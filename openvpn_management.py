#!/usr/bin/env python3

# Copyright 2024 Daniele Vercelli - ynad <info@danielevercelli.it>
# https://github.com/ynad/openvpn-stats
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
openvpn_management.py
2024-10-08
v0.0.3

Inspired from openvpn-monitor by furlongm:
https://github.com/furlongm/openvpn-monitor/


OpenvpnManagement
Class to manage connection and commands to the OpenVPN management console (via TCP/IP or unix socket)

Args:
    host (str, default: localhost):     IP address where management console listen
    port (int, default: 5555):          TCP port to connect to
    password (str, default: None):      Password used to access the console
    socket (socket, default: None):     Unix socket to the console
    name (str, default: None):          Name give to the OpenVPN instance
    mute (bool, default: False):        Suppress info messages to stdout/stderr
    debug (bool, default: False):       Enable debug messages to stdout/stderr

Requirements:
    * regex
"""


import logging
import sys
import regex as re
import socket



# logger
logger = logging.getLogger(__name__)



class OpenvpnManagement(object):

    def __init__(self, 
                host: str = 'localhost',
                port: int = 5555,
                password: str = None,
                socket: socket = None,
                name: str = None,
                mute: bool = False,
                debug: bool = False
        ):
        self.__host = host
        self.__port = port
        self.__password = password
        self.__sck = socket
        self.__name = name
        self.__mute = mute
        self.__debug = debug
        logger.info(f"init OvpnManagement")


    def socket_connect(self) -> None:
        timeout = 3
        try:
            if self.__sck:
                logger.info(f"OvpnManagement, socket mode: {self.__sck}")
                self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.__socket.connect(self.__sck)
            else:
                logger.info(f"OvpnManagement, name: {self.__name}, create connection: {self.__host} : {self.__port}")
                self.__socket = socket.create_connection((self.__host, self.__port), timeout)

            if self.__socket:
                if self.__password:
                    self.__wait_for_data(password=self.__password)
                self.__connected = True

        except socket.timeout as exc:
            self.__connected = False
            self.__error = '{0!s}'.format(exc)
            self.print_warning("socket timeout: {0!s}".format(exc))
            logger.warning("socket timeout: {0!s}".format(exc))
            
            if self.__socket:
                self.socket_disconnect()
            raise socket.timeout from exc

        except socket.error as exc:
            self.__connected = False
            self.__error = '{0!s}'.format(exc.strerror)
            self.print_warning("socket error: {0!s}".format(exc))
            logger.warning("socket error: {0!s}".format(exc))
            raise socket.error from exc

        except Exception as exc:
            self.__connected = False
            self.__error = '{0!s}'.format(exc)
            self.print_warning("unexpected error: {0!s}".format(exc))
            logger.warning("unexpected error: {0!s}".format(exc))
            raise Exception(exc) from exc


    def socket_disconnect(self) -> None:
        if not self.__mute:
            self.print_info("Socket disconnect")
            logger.info("Socket disconnect")
        self.__socket_send('quit\n')
        self.__socket.shutdown(socket.SHUT_RDWR)
        self.__socket.close()


    def send_command(self, command: str) -> str:
        if not self.__mute:
            self.print_info("Sending command: {0!s}".format(command))
            logger.info("Sending command: {0!s}".format(command))
        self.__socket_send(command)
        if command.startswith('kill') or command.startswith('client-kill'):
            return
        return self.__wait_for_data(command=command)


    def __socket_send(self, command: str) -> None:
        if sys.version_info[0] == 2:
            self.__socket.send(command)
        else:
            self.__socket.send(bytes(command, 'utf-8'))

    
    def __socket_recv(self, length: int) -> str:
        if sys.version_info[0] == 2:
            return self.__socket.recv(length)
        else:
            return self.__socket.recv(length).decode('utf-8')


    def __wait_for_data(self, password: str = None, command: str = None) -> str:
        data = ''
        while 1:
            socket_data = self.__socket_recv(1024)
            socket_data = re.sub('>INFO(.)*\r\n', '', socket_data)
            data += socket_data
            if data.endswith('ENTER PASSWORD:'):
                if password:
                    self.__socket_send('{0!s}\n'.format(password))
                else:
                    self.print_warning("password requested but no password supplied by configuration")
                    logger.warning("password requested but no password supplied by configuration")
            if data.endswith('SUCCESS: password is correct\r\n'):
                break
            if command == 'load-stats\n' and data != '':
                break
            elif data.endswith("\nEND\r\n"):
                break
        if self.__debug:
            self.print_debug("=== begin raw data\n{0!s}\n=== end raw data".format(data))

        return data


    def print_info(self, objs):
        print("INFO:", objs, file=sys.stderr)


    def print_warning(self, objs):
        print("WARNING:", objs, file=sys.stderr)


    def print_debug(self, objs):
        print("DEBUG:\n", objs, file=sys.stderr)

