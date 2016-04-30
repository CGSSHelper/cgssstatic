#!/usr/bin/env python
import re
import sys
import os
import hashlib
import requests
import sqlite3
from UnicodeWriter import UnicodeWriter

VERSION=os.getenv('VERSION') or 10014950

DBMANIFEST="http://storage.game.starlight-stage.jp/dl/{0}/manifests".format(VERSION)
ASSETBBASEURL="http://storage.game.starlight-stage.jp/dl/resources/High/AssetBundles/Android"
SOUNDBASEURL="http://storage.game.starlight-stage.jp/dl/resources/High/Sound/Common"
SQLBASEURL="http://storage.game.starlight-stage.jp/dl/resources/Generic"

SCRIPT_PATH=os.getcwd()+"/exec"
LZ4ER="{0}/lz4er".format(SCRIPT_PATH)
UNACB="{0}/acb.py".format(SCRIPT_PATH)
HCA="{0}/hca.exe".format(SCRIPT_PATH)
DISUNITY="{0}/disunity.jar".format(SCRIPT_PATH)
AHFF2PNG="{0}/ahff2png".format(SCRIPT_PATH)

TMP_COMPRESSED=os.getcwd()+"/orimain"
TMP_SQLITE3=os.getcwd()+"/main.db"

TMP_DOWNLOAD=os.getcwd()+"/origin"
TMP_DEST=os.getcwd()+"/tmpdest"
DEST=os.getcwd()+"/dest"

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
        return "{0}/{1}/{2}".format(SOUNDBASEURL, os.path.dirname(filename), md5)

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
                r = requests.get(url)
                file_content = r.content
                status_code = r.status_code
                down_dir = os.path.join(TMP_DOWNLOAD, os.path.dirname(FILENAME))
                if os.path.dirname(FILENAME) != '' and not os.path.isdir(down_dir):
                    os.mkdir(down_dir)
                if status_code == 200:
                    with open(os.path.join(TMP_DOWNLOAD, destfile(FILENAME)), 'wb') as f:
                        f.write(file_content)
                else:
                    print "===> Error {0}.".format(FILENAME)
            else:
                print "===> Skipping {0}.".format(FILENAME)

def extract():
    if not os.path.isdir(TMP_DEST): os.mkdir(TMP_DEST)
    if not os.path.isdir(DEST): os.mkdir(DEST)
    for root, dirs, files in os.walk(TMP_DOWNLOAD):
        for name in files:
            ext = name.split('.')[1]
            if ext == "acb":
                acb_extract(root,name,DEST+"/sound",TMP_DEST)
            elif ext == "mdb":
                sql_extract(root,name,DEST+"/master",TMP_DEST)
            elif ext == "unity3d":
                disunity_extract(root,name,DEST+"/"+name.split('_')[0],TMP_DEST)
            else:
                print "[!] cannot ripper {0}".format(os.path.join(root,name))

def acb_extract(root, name, dest, tmp):
    print "[-] unacb {0}".format(name)
    if not os.path.isdir(dest): os.mkdir(dest)
    if not os.path.isfile(os.path.join(dest,name.replace('acb','mp3'))):
        acb_comm = "python3 {0} {1} {2}".format(UNACB, os.path.join(root,name), tmp)
        os.system(acb_comm)
        # use basename because hca.exe cannot accept absolute path
        hca_comm = "wine {0} -m 32 -a F27E3B22 -b 00003657 {1}".format(HCA, os.path.join(os.path.basename(tmp),name.replace('acb','hca')))
        print hca_comm
        os.system(hca_comm)
        avconv_comm = "avconv -i {0} -qscale:a 0 {1}".format(os.path.join(tmp,name.replace('acb','wav')), os.path.join(dest,name.replace('acb','mp3')))
        os.system(avconv_comm)
        os.remove(os.path.join(tmp,name.replace('acb','wav')))
        os.remove(os.path.join(tmp,name.replace('acb','hca')))

def sql_extract(root, name, dest, tmp):
    print "[-] unpacking sql {0}".format(name)
    if not os.path.isdir(dest): os.mkdir(dest)
    lz4er_comm = "{0} {1} > {2}".format(LZ4ER, os.path.join(root,name), os.path.join(tmp,name))
    os.system(lz4er_comm)
    conn = sqlite3.connect(os.path.join(tmp,name))
    cur = conn.cursor()
    cur.execute("select name from sqlite_master where type='table' order by name")
    for table in cur.fetchall():
        tablename = table[0]
        print "[>] {0} to {0}.csv".format(tablename)
        cur.execute("select * from {0}".format(tablename))
        writer = UnicodeWriter(open("{0}/{1}.csv".format(dest,tablename), "wb"))
        writer.writerows(cur)
    os.remove(os.path.join(tmp,name))

def disunity_extract(root, name, dest, tmp):
    print "[-] disunitying {0}.".format(name)
    if not os.path.isdir(dest): os.mkdir(dest)
    if not os.path.isdir(dest+"/"+name.split('.')[0]):
        lz4er_comm = "{0} {1} > {2}".format(LZ4ER, os.path.join(root,name), os.path.join(tmp,name))
        os.system(lz4er_comm)
        disunity_comm = "java -jar {0} extract -d {1} {2}".format(DISUNITY, dest+"/"+name.split('.')[0], os.path.join(tmp,name))
        #print disunity_comm
        os.system(disunity_comm)
        for rootdir, dirs, files in os.walk(dest+"/"+name.split('.')[0]):
            for destname in files:
                if destname.split('.')[1]=="ahff":
                    ahff2png_comm = "{0} {1}".format(AHFF2PNG, os.path.join(rootdir, destname))
                    os.system(ahff2png_comm)
                    os.remove(os.path.join(rootdir, destname))
        os.remove(os.path.join(tmp,name))

def main(*args):
    get_manifests()
    download_new_files()
    extract()

if __name__ == '__main__':
    main(*sys.argv)
