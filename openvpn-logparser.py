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
openvpn-logparser.py
2024-10-01
v0.0.2

OpenVPN-logparser
WIP script to parse and analyze server logs, extract data and manipulate it.

Args:
    file (str, default: None):          openvpn server log file to parse (one file at a time)
    user (str, default: None):          openvpn user (CNAME) to search for
    [...]

Requirements:
    * regex
"""


import os
import click
import regex as re
from datetime import datetime



@click.command()
@click.option(
    "--file",
    type=str,
    default=""
)
@click.option(
    "--user",
    type=str,
    default=""
)

def main(file, user):

    if not os.path.exists(file):
        print(f"Source file not found: {file}")
        raise FileNotFoundError(file)

    if not user:
        print(f"Specify an user to search for with option: --user\n")
        raise ValueError

    print(f"Parse log file: {file}, for user: {user}\n")

    start_time = None
    stop_time = None
    restart_time = None
    active_time = {}

    with open(file) as fp:
        while line := fp.readline():
            this_line = line.rstrip()

            # search connection start time
            if re.search(f"{user}/" + "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{4,6} SENT CONTROL", this_line):
                start_time = datetime.fromisoformat( this_line.split('+02:00')[0] )
                print(f"start connection, time: {start_time}")

            # search connection reset time, then calculate time delta and sum to a dict with day as key
            if re.search(f"{user}/" + "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{4,6} SIGUSR1\[soft,connection-reset\]", this_line):
                stop_time = datetime.fromisoformat( this_line.split('+02:00')[0] )
                print(f"connection-reset, time: {stop_time}")

                if start_time:
                    day_key = start_time.strftime("%Y-%m-%d")
                    delta_t = stop_time - start_time
                    if day_key in active_time:
                        active_time[day_key] += delta_t
                    else:
                        active_time[day_key] = delta_t
                    print(f"*** day: {day_key}, connection-reset add delta_t: {delta_t}, active_time: {active_time[day_key]}\n")

            # search connection restart time, then calculate time delta and sum to a dict with day as key
            if re.search(f"{user}/" + "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{4,6} SIGUSR1\[soft,ping-restart\]", this_line):
                restart_time = datetime.fromisoformat( this_line.split('+02:00')[0] )
                print(f"ping-restart, time: {restart_time}")

                if start_time:
                    day_key = start_time.strftime("%Y-%m-%d")
                    delta_t = restart_time - start_time
                    if day_key in active_time:
                        active_time[day_key] += delta_t
                    else:
                        active_time[day_key] = delta_t
                    print(f"*** day: {day_key}, ping-restart add delta_t: {delta_t}, active_time: {active_time[day_key]}\n")


    print(f"Stats for user: {user}")
    for day_key, day_time in active_time.items():
        print(f"* day: {day_key}, total connection time: {day_time}")
    


if __name__ == '__main__':
    main()
