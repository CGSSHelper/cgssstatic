# cgssstatic
Auto Update Static Data of CGSS
Only TESTED under `Debian 8 Jessie`, no gurantee under other Linux Platform.

## Dependencies
```Shell
#libav-tools for wav to mp3 convert. python3 for acb.py
sudo apt-get install libav-tools python3 python-pip
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
