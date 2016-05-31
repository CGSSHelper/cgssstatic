# cgssstatic
Auto Update Static Data of CGSS

Only TESTED under `Debian 8 Jessie`, no gurantee under other Linux Platform.

## Dependencies
```Shell
apt update
#libav-tools for wav to mp3 convert, python3 for acb.py, java for disunity.
apt-get install libav-tools python3 python3-pip default-jre sqlite3
pip3 install -r requirements.txt
```

## Usage
1. Set environment variables
you need to set `VC_AES_KEY`, `VC_SID_SALT`, and `VC_ACCOUNT`, see `apiclient.py`
for more information.

2. Run and take a cup of coffee
```Shell
./main.py
```
Check `dest` folder for data.
