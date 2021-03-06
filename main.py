import re, sys, os, hashlib, requests, sqlite3, time
import apiclient, CSVUnicode

RES_VER_PATH = os.path.dirname(os.path.realpath(__file__))+'/res_ver'

try:
    open(RES_VER_PATH, 'r')
except:
    with open(RES_VER_PATH, 'w') as f:
        f.write('10013600')

with open(RES_VER_PATH, 'r') as f:
    global VERSION
    VERSION = f.read()

ASSETBBASEURL="http://storage.game.starlight-stage.jp/dl/resources/High/AssetBundles/Android"
SOUNDBASEURL="http://storage.game.starlight-stage.jp/dl/resources/High/Sound/Common"
SQLBASEURL="http://storage.game.starlight-stage.jp/dl/resources/Generic"

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))+"/exec"
LZ4ER="{0}/lz4er".format(SCRIPT_PATH)
UNACB="{0}/acb.py".format(SCRIPT_PATH)
HCA="{0}/hca".format(SCRIPT_PATH)
DISUNITY="{0}/disunity.jar".format(SCRIPT_PATH)
AHFF2PNG="{0}/ahff2png".format(SCRIPT_PATH)

TMP_COMPRESSED=os.path.dirname(os.path.realpath(__file__))+"/orimain"
TMP_SQLITE3=os.path.dirname(os.path.realpath(__file__))+"/main.db"
DOWNLOAD_LIST=os.path.dirname(os.path.realpath(__file__))+"/downloadlist"

TMP_DOWNLOAD=os.path.dirname(os.path.realpath(__file__))+"/origin"
TMP_DEST=os.path.dirname(os.path.realpath(__file__))+"/tmpdest"
DEST=os.path.dirname(os.path.realpath(__file__))+"/dest"

def check_version_api_recv(response, msg, sid):
    result_code = msg.get("data_headers", {}).get("result_code", "0")
    res_ver = msg.get("data_headers", {}).get("required_res_ver", "-1")
    if result_code is 204:
        # app version update
        res = requests.get("https://play.google.com/store/apps/details?id=jp.co.bandainamcoent.BNEI0242").content
        match_ver = re.findall(r'itemprop="softwareVersion"> (\d{1}\.\d{1}\.\d{1})  </div>', res.decode('utf8'), re.M)
        if(len(match_ver)):
            os.environ['VC_APP_VER'] = match_ver[0]
            print("update app ver to {}".format(match_ver[0]))
            check_version()
        return
        
    if res_ver != VERSION:
        if res_ver != "-1":
            print("New version {0} found".format(res_ver))
            update_to_res_ver(res_ver)
            with open(RES_VER_PATH, 'w') as f:
                f.write(res_ver)
        else:
            print("no required_res_ver, did the app get a forced update?")
            print(msg)
            exit(1)
    else:
        print("we're on latest")
        exit(0)

def can_check_version():
    return all([x in os.environ for x in ["VC_ACCOUNT", "VC_AES_KEY", "VC_SID_SALT"]]) \
        and not os.getenv("DISABLE_AUTO_UPDATES", None)

def check_version():
    if not can_check_version():
        print("no enough secrets")
        return

    print("trace check_version")
    print("current APP_VER: {0}".format(VERSION))
    print("start check at {0}".format(time.asctime()))

    apiclient.versioncheck(check_version_api_recv)

def get_manifests():
    print("===> Figuring out where the main manifest is...")
    res = requests.get(DBMANIFEST+"/all_dbmanifest").content.split()
    regex = re.compile(".*Android,High,High")
    FILENAME = [m.group(0) for l in res for m in [regex.search(l.decode('ascii'))] if m][0].split(',')[0]
    FILEMD5 = [m.group(0) for l in res for m in [regex.search(l.decode('ascii'))] if m][0].split(',')[1]
    if not check_file(TMP_SQLITE3, FILEMD5):
        print("===> Downloading the main manifest.")
        res = requests.get(DBMANIFEST+"/"+ FILENAME).content
        with open(TMP_COMPRESSED, 'wb') as f:
            f.write(res)
        lz4er_comm = "{0} {1} > {2}".format(LZ4ER, TMP_COMPRESSED, TMP_SQLITE3)
        if os.system(lz4er_comm) == 0:
            print("Successfully decompressed.")
    else:
        print("===> Using cached manifest from earlier.")

    sqlite_comm = "{0} {1} --separator \",\" \"SELECT name, hash FROM manifests\" > {2}".format("sqlite3", TMP_SQLITE3, DOWNLOAD_LIST)
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
    with open(DOWNLOAD_LIST, "r") as f:
        for res in f.readlines():
            res = res.split()[0].split(',')
            FILENAME = res[0]
            MD5 = res[1]
            if not check_file("{0}/{1}".format(TMP_DOWNLOAD, destfile(FILENAME)), MD5):
                print("===> Downloading new version of file {0}.".format(FILENAME))
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
                    print("===> Error {0}.".format(FILENAME))
            else:
                print("===> Skipping {0}.".format(FILENAME))
                
def extract_master():
    os.path.isdir(TMP_DEST) or os.mkdir(TMP_DEST)
    os.path.isdir(DEST) or os.mkdir(DEST)
    for root, dirs, files in os.walk(TMP_DOWNLOAD):
        for name in files:
            if name.split('.')[1] == "mdb":
                sql_extract(root,name,DEST+"/master",TMP_DEST)

def extract():
    os.path.isdir(TMP_DEST) or os.mkdir(TMP_DEST)
    os.path.isdir(DEST) or os.mkdir(DEST)
    for root, dirs, files in os.walk(TMP_DOWNLOAD):
        for name in files:
            ext = name.split('.')[1]
            if ext == "acb":
                acb_extract(root,name,DEST+"/sound"+"/"+os.path.basename(root)+"/"+name.split('.')[0],TMP_DEST)
            elif ext == "mdb":
                sql_extract(root,name,DEST+"/master",TMP_DEST)
            elif ext == "unity3d":
                disunity_extract(root,name,DEST+"/"+name.split('_')[0],TMP_DEST)
            elif ext == "bdb":
                bdb_extract(root,name,DEST+"/"+name.split('_')[0],TMP_DEST)
            else:
                print("[!] cannot ripper {0}".format(os.path.join(root,name)))

def acb_extract(root, name, dest, tmp):
    print("[-] unacb {0}".format(name))
    if not os.path.isdir(dest):
        os.makedirs(dest)
        acb_comm = "python3 {0} {1} {2}".format(UNACB, os.path.join(root,name), tmp)
        os.system(acb_comm)
        for rootdir, dirs, files in os.walk(tmp):
            for filename in files:
                if filename.split('.')[1] == "hca":
                    # use basename because hca cannot accept absolute path
                    hca_comm = "{0} -m 32 \"{1}\"".format(HCA, os.path.join(tmp,filename))
                    os.system(hca_comm)
                    if not os.path.isfile(os.path.join(tmp,filename.replace('hca','wav'))):
                        # clean up even fails
                        os.remove(os.path.join(tmp,filename))
                        continue
                    avconv_comm = "avconv -i {0} -qscale:a 0 {1}".format(os.path.join(tmp,filename.replace('hca','wav')), os.path.join(dest,filename.replace('hca','mp3')))
                    os.system(avconv_comm)
                    os.remove(os.path.join(tmp,filename.replace('hca','wav')))
                    os.remove(os.path.join(tmp,filename))

def sql_extract(root, name, dest, tmp):
    print("[-] unpacking sql {0}".format(name))
    os.path.isdir(dest) or os.mkdir(dest)
    lz4er_comm = "{0} {1} > {2}".format(LZ4ER, os.path.join(root,name), os.path.join(tmp,name))
    os.system(lz4er_comm)
    conn = sqlite3.connect(os.path.join(tmp,name))
    cur = conn.cursor()
    cur.execute("select name from sqlite_master where type='table' order by name")
    for table in cur.fetchall():
        tablename = table[0]
        print("[>] {0} to {0}.csv".format(tablename))
        cur.execute("select * from {0}".format(tablename))
        with open("{0}/{1}.csv".format(dest,tablename), "wb") as f:
            writer = CSVUnicode.UnicodeWriter(f)
            writer.writerow([col[0] for col in cur.description])
            writer.writerows(cur)
    os.remove(os.path.join(tmp,name))
    
def bdb_extract(root, name, dest, tmp):
    print("[-] unpacking bdb {0}".format(name))
    os.path.isdir(dest) or os.mkdir(dest)
    lz4er_comm = "{0} {1} > {2}".format(LZ4ER, os.path.join(root,name), os.path.join(tmp,name))
    os.system(lz4er_comm)
    conn = sqlite3.connect(os.path.join(tmp,name))
    cur = conn.cursor()
    cur.execute("select * from blobs")
    for fileBlob in cur.fetchall():
        filename = fileBlob[0]
        print("[>] {0} to {0}".format(filename))
        fileDir = "{0}/{1}".format(os.path.dirname(dest), os.path.dirname(filename))
        os.path.isdir(fileDir) or os.mkdir(fileDir)
        filePath = "{0}/{1}".format(os.path.dirname(dest),filename)
        if os.path.isfile(filePath):
            continue
        with open(filePath, "wb") as f:
            f.write(fileBlob[1])
    os.remove(os.path.join(tmp,name))

def disunity_extract(root, name, dest, tmp):
    print("[-] disunitying {0}.".format(name))
    os.path.isdir(dest) or os.mkdir(dest)
    if not os.path.isdir(dest+"/"+name.split('.')[0]):
        lz4er_comm = "{0} {1} > {2}".format(LZ4ER, os.path.join(root,name), os.path.join(tmp,name))
        os.system(lz4er_comm)
        disunity_comm = "java -jar {0} extract -d {1} {2}".format(DISUNITY, dest+"/"+name.split('.')[0], os.path.join(tmp,name))
        os.system(disunity_comm)
        for rootdir, dirs, files in os.walk(dest+"/"+name.split('.')[0]):
            for destname in files:
                if destname.split('.')[1]=="ahff":
                    ahff2png_comm = "{0} {1}".format(AHFF2PNG, os.path.join(rootdir, destname))
                    os.system(ahff2png_comm)
                    os.remove(os.path.join(rootdir, destname))
        os.remove(os.path.join(tmp,name))

def update_to_res_ver(res_ver):
    global DBMANIFEST
    DBMANIFEST="http://storage.game.starlight-stage.jp/dl/{0}/manifests".format(res_ver)
    get_manifests()

def update_all():
    download_new_files()
    extract()
    print("{0} done update".format(time.asctime()))
    exit(0)
    
def update_master():
    if not os.path.isdir(TMP_DOWNLOAD):
        os.mkdir(TMP_DOWNLOAD)
    with open(DOWNLOAD_LIST, "r") as f:
        for res in f.readlines():
            FILENAME, MD5 = res.split()[0].split(',')
            # print(FILENAME, FILENAME=="master.mdb")
            if(FILENAME=="master.mdb" and not check_file("{0}/{1}".format(TMP_DOWNLOAD, destfile(FILENAME)), MD5)):
                print("===> Downloading new version of file {0}.".format(FILENAME))
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
                    print("===> Error {0}.".format(FILENAME))
    extract_master()
    print("{0} done master update".format(time.asctime()))

if __name__ == '__main__':
    check_version()
    if sys.argv[1:]:
        if('master' in sys.argv):
            update_master()
    else:
        update_all()
