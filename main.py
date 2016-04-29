#!/usr/bin/env python
import re
import sys
import os
import hashlib
import requests

VERSION=os.getenv('VERSION') or 10014950

DBMANIFEST="http://storage.game.starlight-stage.jp/dl/{0}/manifests".format(VERSION)
ASSETBBASEURL="http://storage.game.starlight-stage.jp/dl/resources/High/AssetBundles/Android"
SOUNDBASEURL="http://storage.game.starlight-stage.jp/dl/resources/High/Sound/Common"
SQLBASEURL="http://storage.game.starlight-stage.jp/dl/resources/Generic"

SCRIPT_PATH=os.getcwd()+"/exec"
LZ4ER="{0}/lz4er".format(SCRIPT_PATH)

TMP_COMPRESSED=os.getcwd()+"/orimain"
TMP_SQLITE3=os.getcwd()+"/main.db"

TMP_DOWNLOAD=os.getcwd()+"/origin"

def get_manifests():
    if not os.path.isfile(TMP_SQLITE3):
        print "===> Figuring out where the main manifest is..."
        res = requests.get(DBMANIFEST+"/all_dbmanifest").content.split()
        regex = re.compile(".*Android,High,High")
        FILENAME = [m.group(0) for l in res for m in [regex.search(l)] if m][0].split(',')[0]
        print "===> Downloading the main manifest."
        res = requests.get(DBMANIFEST+"/"+ FILENAME).content
        with open(TMP_COMPRESSED, 'wb') as f:
            f.write(res)
        lz4er_comm = "{0} {1} > {2}".format(LZ4ER, TMP_COMPRESSED, TMP_SQLITE3)
        if os.system(lz4er_comm) == 0:
            print "Successfully decompressed."
    else:
        print "===> Using cached manifest from earlier."

    sqlite_comm = "{0} {1} --separator \",\" \"SELECT name, hash FROM manifests\" > downloadlist".format("sqlite3", TMP_SQLITE3)
    os.system(sqlite_comm)

def download_url(filename, md5):
    ext = filename.split('.')[1]
    if ext == "unity3d":
        return "{0}/{1}".format(ASSETBBASEURL, md5)
    elif ext == "mdb" or ext == "bdb":
        return "{0}/{1}".format(SQLBASEURL, md5)
    elif ext == "acb":
        return "{0}/{1}".format(SOUNDBASEURL, md5)

def destfile(filename):
    ext = filename.split('.')[1]
    if ext == "unity3d" or ext == "mdb" or ext == "bdb":
        return "{0}.lz4".format(filename)
    else:
        return filename

def check_file(filename, md5):
    if not os.path.isfile(filename):
        return False
    with open(filename, 'rb') as f:
        m = hashlib.md5()
        m.update(f.read())
        calc_md5 = m.hexdigest()
    return calc_md5 == md5

def download_new_files():
    if not os.path.isdir(TMP_DOWNLOAD):
        os.mkdir(TMP_DOWNLOAD)
    with open("downloadlist", "r") as f:
        for res in f.readlines():
            res = res.split()[0].split(',')
            FILENAME = res[0]
            MD5 = res[1]
            if not check_file("{0}/{1}".format(TMP_DOWNLOAD, destfile(FILENAME)), MD5):
                print "===> Downloading new version of file {0}.".format(FILENAME)
                url = download_url(FILENAME, MD5)
                file_content = requests.get(url).content
                if(os.path.dirname(FILENAME)!='' and not os.path.isdir("{0}/{1}".format(TMP_DOWNLOAD, os.path.dirname(FILENAME)))):
                    os.mkdir("{0}/{1}".format(TMP_DOWNLOAD, os.path.dirname(FILENAME)))
                with open("{0}/{1}".format(TMP_DOWNLOAD, destfile(FILENAME)), 'wb') as f:
                    f.write(file_content)
            else:
                print "===> Skipping {0}.".format(FILENAME)

def main(*args):
    get_manifests()
    download_new_files()

if __name__ == '__main__':
    main(*sys.argv)
