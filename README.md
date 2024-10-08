# openvpn-stats
Collection of scripts to analyze openvpn logs and connection status

## Requirements
- Python > 3.7 is required. Tested with python 3.10.12 and 3.11.2 with virtual env.
- A working MongoDB instance is needed for some advanced scripts, tested up to version 6.0.18 Community Edition.
- Python required packages are listed in the file `requirements.txt`.
  To install them simply run the following:
```
pip install -r requirements.txt
```

or if using venv:
```
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Instructions 
### MongoDB
Create the JSON file `settings_database.json` as follows:
```
{
    "ip" : "localhost",
    "port" : 27017,
    "db" : "openvpn_stats",
    "user" : "openvpn_stats_user",
    "pwd" : "openvpn_stats_password"
}
```
It is reccomended to use MongoDB with user authentication enabled. 

### OpenVPN
Ensure to have enabled status log file on your OpenVPN server config file with the following line:
```
status openvpn-status.log
```

To use the management console, add to the config file the following line:
```
management 127.0.0.1 5555 pw-file
```
Or a different IP/port if more server instances are active.

Then create the JSON file `settings_console.json` as follows, with the appropriate values:
```
{
    "host" : "localhost",
    "port" : 5555,
    "password" : "console-password",
    "name" : "VPN-test"
}
```

## Usage
Usage of each script is described in script's comments.

## License
Released under GPL-3.0 license.

## Disclaimer
Project under early development and tailored for specific usage. Might be expanded or left as is in the future.

Feel free to share any feedback, will be appreciated.
