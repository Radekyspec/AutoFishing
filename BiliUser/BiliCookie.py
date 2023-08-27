from __future__ import annotations

import binascii
import time
from threading import Thread
from urllib.parse import quote

import lxml.html as html
import requests
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


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
    """
    is_checking: bool
    ua: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    uid: int
    uid_ckmd5: str
    
    _sessdata: str
    _csrf: str
    _sid: str
    _refresh_token: str

    def __init__(self, uid: int) -> None:
        super().__init__(name=f"BiliCookie_{uid}", daemon=True)
        self.is_checking = True
        self.uid = uid
        self.uid_ckmd5 = self._sessdata = self._csrf = self._sid = self._refresh_token = None

    def __str__(self) -> str:
        return "\n\t".join([f"UID: {self.uid}",
                            f"SESSDATA: {self._sessdata}",
                            f"bili_jct: {self._csrf}",
                            f"DedeUserID: {self.uid}",
                            f"DedeUserID__ckMd5: {self.uid_ckmd5}",
                            f"sid: {self._sid}",
                            f"refresh_token: {self._refresh_token}"])

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
                          f"sid={self._sid}",])

    @property
    def sessdata(self) -> str:
        return self._sessdata

    @property
    def csrf(self) -> str:
        return self._csrf

    def check_expires(self) -> tuple[bool, int]:
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
        headers = {
            "cookie": self.cookie_string,
            "origin": "https://www.bilibili.com",
            "referer": "https://www.bilibili.com/",
            "user-agent": self.ua,
        }
        params = {"csrf": self.csrf}
        response = requests.get(url, headers=headers, params=params).json()
        assert response["code"] == 0, f"Failed to check cookie status, {response}"
        return response["data"]["refresh"], response["data"]["timestamp"]

    def get_correspond_path(self, ts: int) -> str:
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

    def get_refresh_csrf(self, path: str) -> str:
        url = "https://www.bilibili.com/correspond/1/" + path
        headers = {
            "cookie": self.cookie_string,
            "origin": "https://www.bilibili.com",
            "referer": "https://www.bilibili.com/",
            "user-agent": self.ua,
        }
        response = requests.get(url, headers=headers).text
        refresh_csrf = html.fromstring(response).xpath("//div[@id='1-name']/text()")
        assert refresh_csrf, f"Failed to obtain <refresh_csrf>, {response}"
        return refresh_csrf[0]
    
    def refresh_cookie(self, refresh_csrf: str) -> None:
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
        assert (response_json := response.json())["code"] == 0, \
            f"Failed to refresh cookie, {response_json}"
        self._sid = response.cookies.get("sid")
        self.uid_ckmd5 = response.cookies.get("DedeUserID__ckMd5")
        self._sessdata = response.cookies.get("SESSDATA")
        self._csrf = response.cookies.get("bili_jct")
        self.confirm_refresh()
        self._refresh_token = response_json["data"]["refresh_token"]

    def confirm_refresh(self) -> None:
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
        assert (response.json())["code"] == 0, \
            f"Failed to deactivate old cookie, {response.json()}"

    def update(self) -> None:
        """Keep cookie alive
        """
        expires, ts = self.check_expires()
        if not expires:
            return
        path = self.get_correspond_path(ts)
        refresh_csrf = self.get_refresh_csrf(path)
        self.refresh_cookie(refresh_csrf)
        print(self)
    
    def stop_update(self) -> None:
        self.is_checking = False

    
    def run(self) -> None:
        assert self.sessdata is not None and self.csrf is not None and \
            self._refresh_token is not None, "Cookie cannot be None"
        while self.is_checking:
            time.sleep(60)
            self.update()

if __name__ == '__main__':
    cookie = BiliCookie(178856569)
    cookie.set_cookies(sessdata="",
                       csrf="",
                       uid_ckmd5="",
                       sid="",
                       refresh_token="")
    cookie.start()
    cookie.join()