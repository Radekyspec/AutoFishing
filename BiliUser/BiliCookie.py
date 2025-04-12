from __future__ import annotations

import binascii
import json
import time
from random import randint
from threading import Thread

import lxml.html as html
import requests
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256

from .CookieUpdateException import CookieUpdateException


class BiliCookie(Thread):
    """A class representation of bilibili cookies.

    https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/cookie_refresh.md

    === Public Attributes ===
    is_checking: boolean that represents status of thread.
    ua: default Chrome user agent.
    uid: the uid of user
    uid_ckmd5: ckmd5 representation of uid

    === Private Attributes ===
    _sessdata: SESSDATA option.
    _csrf: csrf or bili_jct option.
    _sid: sid option.
    _refresh_token: token used to refresh cookie.
    _error_times: number of errors occured until next success run.
    """
    is_checking: bool
    ua: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    uid: int
    uid_ckmd5: str

    _sessdata: str
    _csrf: str
    _sid: str
    _refresh_token: str
    _error_times: int

    def __init__(self, uid: int) -> None:
        super().__init__(name=f"BiliCookie_{uid}", daemon=True)
        self.is_checking = True
        self.uid = uid
        self.uid_ckmd5 = self._sessdata = self._csrf = self._sid = self._refresh_token = str()
        self._error_times = 0

    def __str__(self) -> str:
        content = {
            "UID": self.uid,
            "SESSDATA": self._sessdata,
            "bili_jct": self._csrf,
            "DedeUserID": self.uid,
            "DedeUserID__ckMd5": self.uid_ckmd5,
            "sid": self._sid,
            "refresh_token": self._refresh_token
        }
        return json.dumps(content, ensure_ascii=False, separators=(",", ":"))

    def set_cookies(self,
                    sessdata: str,
                    csrf: str,
                    uid_ckmd5: str,
                    sid: str,
                    refresh_token: str) -> None:
        self.uid_ckmd5 = uid_ckmd5
        self._sessdata, self._csrf, self._sid, self._refresh_token = sessdata, csrf, sid, refresh_token

    @property
    def cookie_string(self) -> str:
        return "; ".join([f"SESSDATA={self._sessdata}",
                          f"bili_jct={self._csrf}",
                          f"DedeUserID={self.uid}",
                          f"DedeUserID__ckMd5={self.uid_ckmd5}",
                          f"sid={self._sid}", ])

    @property
    def sessdata(self) -> str:
        return self._sessdata

    @property
    def csrf(self) -> str:
        return self._csrf

    def _check_expires(self) -> tuple[bool, int]:
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
        headers = {
            "cookie": self.cookie_string,
            "origin": "https://www.bilibili.com",
            "referer": "https://www.bilibili.com/",
            "user-agent": self.ua,
        }
        params = {"csrf": self.csrf}
        response = requests.get(url, headers=headers, params=params).json()
        if response["code"] != 0:
            raise CookieUpdateException(
                f"Failed to check cookie status, {response}")
        return response["data"]["refresh"], response["data"]["timestamp"]

    def _get_correspond_path(self, ts: int) -> str:
        pub_key = RSA.importKey("""\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----""".strip())
        cipher = PKCS1_OAEP.new(pub_key, SHA256)
        encrypted = cipher.encrypt(f"refresh_{ts}".encode(encoding="utf-8"))
        return binascii.b2a_hex(encrypted).decode(encoding="utf-8")

    def _get_refresh_csrf(self, path: str) -> str:
        url = "https://www.bilibili.com/correspond/1/" + path
        headers = {
            "cookie": self.cookie_string,
            "origin": "https://www.bilibili.com",
            "referer": "https://www.bilibili.com/",
            "user-agent": self.ua,
        }
        response = requests.get(url, headers=headers).text
        refresh_csrf = html.fromstring(response).xpath(
            "//div[@id='1-name']/text()")
        if not refresh_csrf:
            raise CookieUpdateException(
                f"Failed to obtain <refresh_csrf>, {response}")
        return refresh_csrf[0]

    def _refresh_cookie(self, refresh_csrf: str) -> None:
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/refresh"
        headers = {
            "cookie": self.cookie_string,
            "origin": "https://www.bilibili.com",
            "referer": "https://www.bilibili.com/",
            "user-agent": self.ua,
        }
        data = {
            "csrf": self.csrf,
            "refresh_csrf": refresh_csrf,
            "source": "main_web",
            "refresh_token": self._refresh_token,
        }
        response = requests.post(url, headers=headers, data=data)
        if (response_json := response.json())["code"] != 0:
            raise CookieUpdateException(
                f"Failed to refresh cookie, {response_json}")
        self._sid = response.cookies.get("sid")
        self.uid_ckmd5 = response.cookies.get("DedeUserID__ckMd5")
        self._sessdata = response.cookies.get("SESSDATA")
        self._csrf = response.cookies.get("bili_jct")
        self._confirm_refresh()
        self._refresh_token = response_json["data"]["refresh_token"]

    def _confirm_refresh(self) -> None:
        url = "https://passport.bilibili.com/x/passport-login/web/confirm/refresh"
        headers = {
            "cookie": self.cookie_string,
            "origin": "https://www.bilibili.com",
            "referer": "https://www.bilibili.com/",
            "user-agent": self.ua,
        }
        data = {
            "csrf": self.csrf,
            "refresh_token": self._refresh_token,
        }
        response = requests.post(url, headers=headers, data=data)
        if (response.json())["code"] != 0:
            raise CookieUpdateException(
                f"Failed to deactivate old cookie, {response.json()}")

    def _refresh(self, ts: int) -> None:
        path = self._get_correspond_path(ts)
        refresh_csrf = self._get_refresh_csrf(path)
        self._refresh_cookie(refresh_csrf)

    def _update(self) -> None:
        """Keep cookie alive
        """
        expires, ts = self._check_expires()
        if not expires:
            return
        self._refresh(ts)
        print(f"[{self.name}] refresh success.")

    def stop_update(self) -> None:
        self.is_checking = False

    def run(self) -> None:
        if not self.sessdata or not self.csrf or not self._refresh_token:
            self.stop_update()
            raise CookieUpdateException("Cookie cannot be empty")
        try:
            _, ts = self._check_expires()
            self._refresh(ts)
            print(f"[{self.name}] init refresh success.")
        except CookieUpdateException as e:
            self.stop_update()
            raise e
        
        s_t = randint(40, 70)
        while self.is_checking:
            if self._error_times > 10:
                self.stop_update()
                break
            try:
                self._update()
            except:
                import traceback

                traceback.print_exc()
                print(f"[{self.name}] refresh failed.")
                self._error_times += 1
            else:
                self._error_times = 0
            finally:
                time.sleep(s_t)
