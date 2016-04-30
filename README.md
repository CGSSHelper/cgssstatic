# cgssstatic
Auto Update Static Data of CGSS

Only TESTED under `Debian 8 Jessie`, no gurantee under other Linux Platform.

## Dependencies
```Shell
#prepare for wine
dpkg --add-architecture i386 && apt update
echo "deb http://httpredir.debian.org/debian jessie-backports main" >> /etc/apt/sources.list
apt update
#libav-tools for wav to mp3 convert. python3 for acb.py. wine for hca.exe
apt-get install libav-tools python3 python-pip wine
pip install -r requirements.txt
```

## Usage
```Shell
#Recommend using virtualenv.
virtualenv .
source bin/activate
#nohup for running background
nohup ./main.py &
```
Check `dest` folder for data.
