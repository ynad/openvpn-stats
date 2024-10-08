#!/usr/bin/env python3

# Copyright 2024 Daniele Vercelli - ynad <info@danielevercelli.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>

"""
mongo_manager.py
2024-10-07
v0.0.2
"""

import logging
import os
import shutil
import tarfile
from datetime import datetime
from pymongo import MongoClient
from bson.json_util import dumps



# logger
logger = logging.getLogger(__name__)



"""
MongoManager: It is a class which is useful to manage mongodb operations.

Args:
    ip (str):                                           IP address of mongodb server
    port (int):                                         TCP port of mongodb server
    database (str):                                     database name on mongodb server
    username (str, default: None):                      username for authentication to mongodb server
    password (str, default: None):                      password for authentication to mongodb server
    authSource (str, default: 'admin'):                 mongodb database source for user authentication
    authMechanism (str, default: 'SCRAM-SHA-256'):      mongodb authentication mechanism
"""


class MongoManager():

    def __init__(self, 
                ip: str, 
                port: int, 
                database: str, 
                username: str = None, 
                password: str = None,
                authSource: str = 'admin',
                authMechanism: str = 'SCRAM-SHA-256'
            ):

        logger.info("init Mongo class")
        self.__mongo_ip = ip
        self.__mongo_port = port
        self.__database_name = database
        self.__mongo_user = username
        self.__mongo_pw = password
        self.__authSource = authSource
        self.__authMechanism = authMechanism
        logger.info(f"mongo settings: ip {ip}, port {port}, db {database}, user {username}")

        if not username or not password:
            logger.warning("Empty mongo user or password, authentication may fail")

        self.__init_mongo()


    def __init_mongo(self) -> None:

        logger.info("init Mongo client")
        self.__client = MongoClient(
            self.__mongo_ip, 
            self.__mongo_port,
            username=self.__mongo_user,
            password=self.__mongo_pw,
            authSource=self.__authSource,
            authMechanism=self.__authMechanism
        )
        self._database = self.__client[self.__database_name]


    ##
    ## PID r/w handling
    ##

    def pid_read(self, pid_name: str) -> int:
        pid = self._database.pid.find_one({ 'id' : pid_name })
        if pid:
            logger.info(f"Read PID name: {pid_name}, pid: {pid['pid']}")
            return pid['pid']
        else:
            logger.warning(f"PID name: {pid_name} not found ")
            return 0


    def pid_write(self, pid_name: str, pid: int) -> bool:
        logger.info(f"Write PID: {pid}, name: {pid_name}")
        res = self._database.pid.update_one(
                {
                    'id' : pid_name
                },
                {
                    '$set' : {
                        'pid' : int(pid)
                    }
                },
                upsert=True
        )
        if not res.acknowledged:
            logger.error(f'Mongo update in pid not acknowledged. pid: {pid}, pid_name: {pid_name}.')
            return False

        return True


    def pid_del(self, pid_name: str) -> int:
        pid = self._database.pid.find_one({ 'id' : pid_name })
        if pid:
            logger.info(f"Del PID name: {pid_name}, pid: {pid['pid']}")
            self._database.pid.delete_one({ 'id' : pid_name })
            return pid
        else:
            logger.warning(f"PID name: {pid_name} not found, cannot delete")
            return 0


    ##
    ## CONNECTIONS LOGS
    ##

    def connection_log(self, conn_data: dict) -> tuple[bool, str]:
        # search VPN user
        user_data = self._database.user_list.find_one( {"id" : conn_data['id']} )
        if user_data:

            # search connection date in history log
            date_key = conn_data['date'].split('.')
            if date_key[0] in user_data['history'] and date_key[1] in user_data['history'][date_key[0]] and date_key[2] in user_data['history'][date_key[0]][date_key[1]]:
                logger.info(f"user data found for this date, update user id: {conn_data['id']}")

                # start time is same = same connection uninterrupted
                if conn_data['start'] == user_data['history'][date_key[0]][date_key[1]][date_key[2]]['start']:
                    start_date = user_data['history'][date_key[0]][date_key[1]][date_key[2]]['start']
                    seconds = (conn_data['last'] - user_data['history'][date_key[0]][date_key[1]][date_key[2]]['last']).total_seconds()
                    byte_rec = conn_data['bytes']['received']
                    byte_sent = conn_data['bytes']['sent']

                # different start time = reconnection, use new start time
                else:
                    start_date = conn_data['start']
                    seconds = (conn_data['last'] - conn_data['start']).total_seconds()
                    byte_rec = conn_data['bytes']['received'] + user_data['history'][date_key[0]][date_key[1]][date_key[2]]['bytes']['received']
                    byte_sent = conn_data['bytes']['sent'] + user_data['history'][date_key[0]][date_key[1]][date_key[2]]['bytes']['sent']

                # calc duration in human format
                new_seconds = user_data['history'][date_key[0]][date_key[1]][date_key[2]]['seconds'] + seconds
                hours = int(( new_seconds / ( 60 * 60 )) % 24)
                seconds_ = int(new_seconds % 60)
                minutes = int(( new_seconds / 60 ) % 60)
                duration = f"{hours:02}:{minutes:02}:{seconds_:02}"

                res = self._database.user_list.update_one(
                    {
                        'id': conn_data['id']
                    },
                    {
                        '$set': {
                            #'bytes.received' : user_data['bytes']['received'] + conn_data['bytes']['received'],
                            #'bytes.sent' : user_data['bytes']['sent'] + conn_data['bytes']['sent'],
                            'history.{}'.format(conn_data['date']) : {
                                'ip' : conn_data['ip'], 
                                'port' : conn_data['port'],
                                'start' : start_date,
                                'last' : conn_data['last'],
                                'seconds' :  new_seconds,
                                'duration' : duration,
                                'bytes' : { 
                                    'received' : byte_rec,
                                    'sent' : byte_sent
                                }
                            }
                        }
                    },
                    #upsert=True
                )
                if not res.acknowledged:
                    logger.error(f'Mongo update during user update in user_list not acknowledged. Chat id: {chat_id_new}, chat name: {chat_name}, user count: {user_count}.')
                    return False, "There was some error please retry"

            else:
                logger.info(f"user data found, update user id: {conn_data['id']}")
                hours = int(( conn_data['seconds'] / ( 60 * 60 )) % 24)
                seconds_ = int(conn_data['seconds'] % 60)
                minutes = int(( conn_data['seconds'] / 60 ) % 60)
                duration = f"{hours:02}:{minutes:02}:{seconds_:02}"

                res = self._database.user_list.update_one(
                {
                    'id': conn_data['id']
                },
                {
                    '$set': {
                        #'bytes.received' : user_data['bytes']['received'] + conn_data['bytes']['received'],
                        #'bytes.sent' : user_data['bytes']['sent'] + conn_data['bytes']['sent'],
                        'history.{}'.format(conn_data['date']) : {
                            'ip' : conn_data['ip'], 
                            'port' : conn_data['port'],
                            'start' : conn_data['start'],
                            'last' : conn_data['last'],
                            'seconds' : conn_data['seconds'],
                            'duration' : duration,
                            'bytes' : { 
                                'received' : conn_data['bytes']['received'],
                                'sent' : conn_data['bytes']['sent']
                            }
                        }
                    },
                },
                #upsert=True
            )
            if not res.acknowledged:
                logger.error(f'Mongo update during user update in user_list not acknowledged. Chat id: {chat_id_new}, chat name: {chat_name}, user count: {user_count}.')
                return False, "There was some error please retry"

        else:
            logger.info(f"user data not found, add new user id: {conn_data['id']}")
            hours = int(( conn_data['seconds'] / ( 60 * 60 )) % 24)
            seconds_ = int(conn_data['seconds'] % 60)
            minutes = int(( conn_data['seconds'] / 60 ) % 60)
            duration = f"{hours:02}:{minutes:02}:{seconds_:02}"

            res = self._database.user_list.update_one(
                {
                    'id': conn_data['id']
                },
                {
                    '$set': {
                        #'bytes.received' : conn_data['bytes']['received'],
                        #'bytes.sent' : conn_data['bytes']['sent'],
                        'history.{}'. format(conn_data['date']) : {
                            'ip' : conn_data['ip'], 
                            'port' : conn_data['port'],
                            'start' : conn_data['start'],
                            'last' : conn_data['last'],
                            'seconds' : conn_data['seconds'],
                            'duration' : duration,
                            'bytes' : { 
                                'received' : conn_data['bytes']['received'],
                                'sent' : conn_data['bytes']['sent'] 
                            }
                        }
                    },
                },
                upsert=True
            )
            if not res.acknowledged:
                logger.error(f'Mongo update during user update in user_list not acknowledged. Chat id: {chat_id_new}, chat name: {chat_name}, user count: {user_count}.')
                return False, "There was some error please retry"

        return True, None



    ##
    ## DATABASE MAINTENANCE
    ##

    
    ##
    ## BACKUP
    ##

    def __create_folder_backup(self) -> str:
        dt = datetime.now()
        directory = f'backups/backup_{self.__database_name}__{dt.year}-{dt.month:02}-{dt.day:02}__{dt.hour:02}-{dt.minute:02}'
        logger.debug(f"Making backup dir: {directory}")
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory


    def __make_tarfile(self, output_filename: str, source_dir: list) -> None:
        logger.debug(f"Creating tar gz file: {output_filename}")
        tar = tarfile.open(output_filename, "w:gz")
        for filename in source_dir:
            tar.add(filename)
        tar.close()


    def run_backup(self) -> str:
        logger.debug("Running db backup")
        collections = self._database.list_collection_names()
        files_to_compress = []
        directory = self.__create_folder_backup()

        for collection in collections:
            db_collection = self._database[collection]
            cursor = db_collection.find({})
            text_to_save = dumps([doc for doc in cursor], indent=4)
            filename = f'{directory}/{collection}.json'
            files_to_compress.append(filename)
            with open(filename, 'w') as file:
                file.write(text_to_save)
        tar_file = f'{directory}.tar.gz'
        self.__make_tarfile(tar_file, files_to_compress)

        # rm tmp folder
        if os.path.exists(directory):
            logger.debug("Remove db backup tmp dir")
            shutil.rmtree(directory)

        return tar_file
