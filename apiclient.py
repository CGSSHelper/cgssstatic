#!/usr/bin/python
# -!- coding: utf-8 -!-
#
# Copyright 2016 Hector Martin <marcan@marcan.st>
# Modified By DNARoma <tangpei506@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64, msgpack, hashlib, random, time, os, uuid, requests, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from rijndael import rijndael
from asyncio import coroutine, Future

# laziness
def VIEWER_ID_KEY():
    return os.getenv("VC_AES_KEY", "").encode("ascii")

def SID_KEY():
    return os.getenv("VC_SID_SALT", "").encode("ascii")

def decrypt_cbc(s, iv, key):
    p = b"".join(rijndael.decrypt(key, bytes(s[i:i+len(iv)])) for i in range(0, len(s), len(iv)))
    return bytes((iv+s)[i] ^ p[i] for i in range(len(p)))

def encrypt_cbc(s, iv, key):
    if len(s) % 32:
        s += b"\x00" * (32 - (len(s) % 32))
    out = [iv]
    for i in range(0, len(s), 32):
        blk = bytes(s[i+j] ^ out[-1][j] for j in range(32))
        out.append(rijndael.encrypt(key, blk))
    return b"".join(out[1:])

class ApiClient(object):
    BASE = "https://game.starlight-stage.jp"
    def __init__(self, user, viewer_id, udid, res_ver=os.getenv("CGSS_RES_VER", "10013600").encode('ascii'), sid=None):
        self.user = user
        self.viewer_id = viewer_id
        self.udid = udid
        self.sid = sid
        self.res_ver = res_ver

    def lolfuscate(self, s):
        return "%04x" % len(s) + "".join(
            "%02d" % random.randrange(100) +
            chr(ord(c) + 10) + "%d" % random.randrange(10)
            for c in s) + "%032d" % random.randrange(10**32)

    def unlolfuscate(self, s):
        return "".join(chr(ord(c) - 10) for c in s[6::4][:int(s[:4], 16)])

    def call(self, path, args, done):
        vid_iv = ("%032d" % random.randrange(10**32)).encode("ascii")
        args["timezone"] = "09:00:00"
        args["viewer_id"] = vid_iv + base64.b64encode(
            encrypt_cbc(bytes(self.viewer_id, "ascii"),
                        vid_iv,
                        VIEWER_ID_KEY()))
        plain = base64.b64encode(msgpack.packb(args))
        # I don't even
        key = base64.b64encode(bytes(random.randrange(255) for i in range(32)))[:32]
        msg_iv = self.udid.replace("-","").encode("ascii")
        body = base64.b64encode(encrypt_cbc(plain, msg_iv, key) + key)
        sid = self.sid if self.sid else str(self.viewer_id) + self.udid
        headers = {
            "PARAM": hashlib.sha1(bytes(self.udid + str(self.viewer_id) + path, "ascii") + plain).hexdigest(),
            "KEYCHAIN": "",
            "USER_ID": self.lolfuscate(str(self.user)),
            "CARRIER": "google",
            "UDID": self.lolfuscate(self.udid),
            "APP_VER": os.environ.get("VC_APP_VER", "1.9.4"), # in case of sent
            "RES_VER": self.res_ver,
            "IP_ADDRESS": "127.0.0.1",
            "DEVICE_NAME": "Nexus 42",
            "X-Unity-Version": "5.1.2f1",
            "SID": hashlib.md5(bytes(sid, "ascii") + SID_KEY()).hexdigest(),
            "GRAPHICS_DEVICE_NAME": "3dfx Voodoo2 (TM)",
            "DEVICE_ID": hashlib.md5(b"Totally a real Android").hexdigest(),
            "PLATFORM_OS_VERSION": "Android OS 13.3.7 / API-42 (XYZZ1Y/74726f6c6c)",
            "DEVICE": "2",
            "Content-Type": "application/x-www-form-urlencoded", # lies
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13.3.7; Nexus 42 Build/XYZZ1Y)",
        }

        response = requests.post(self.BASE + path, headers=headers, data=body)
        if(done):
            self.wrap_callback(done, response, msg_iv)
        else:
            reply = base64.b64decode(response.text.encode('ascii'))
            plain = decrypt_cbc(reply[:-32], msg_iv, reply[-32:]).split(b"\0")[0]
            msg = msgpack.unpackb(base64.b64decode(plain), encoding='utf-8')
            future = Future()
            future.set_result((response, msg))
            return future

    def wrap_callback(self, done, response, iv):
        if response.status_code != requests.codes.ok:
            done(response, None)
            return

        reply = base64.b64decode(response.text.encode('ascii'))
        plain = decrypt_cbc(reply[:-32], iv, reply[-32:]).split(b"\0")[0]
        msg = msgpack.unpackb(base64.b64decode(plain), encoding='utf-8')
        # print(msg)
        try:
            self.sid = msg["data_headers"]["sid"]
        except:
            pass
        done(response, msg, self.sid)

def versioncheck(callback):
    user_id, viewer_id, udid = os.getenv("VC_ACCOUNT", "::").split(":")
    client = ApiClient(user_id, viewer_id, udid)
    args = {
        "campaign_data": "",
        "campaign_user": 1337,
        "campaign_sign": hashlib.md5(b"All your APIs are belong to us").hexdigest(),
        "app_type": 0,
    }
    client.call("/load/check", args, callback)

def getLoadIndex(callback, sid):
    user_id, viewer_id, udid = os.getenv("VC_ACCOUNT", "::").split(":")
    client = ApiClient(user_id, viewer_id, udid, sid=sid)
    args = {
        "live_state": 0,
        "friend_view_time": 1467500261,
        "live_setting": 0,
        "load_state": 0,
        "name_card_view_time": 0,
        "live_detail_id": 0,
        "tutorial_flag": 1000
    }
    client.call("/load/index", args, callback)
