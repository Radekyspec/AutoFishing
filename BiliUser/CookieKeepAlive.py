from __future__ import annotations

import json
import time

from random import choice
from threading import Thread

from .BiliCookie import BiliCookie


class CookieKeepAlive(Thread):
    _cookies: dict[int, BiliCookie]
    _uids: set[int]

    def __init__(self) -> None:
        super().__init__(name="CookieKeepAlive", daemon=True)
        self._cookies = {}
        self._uids = set()
        self._closed = False

    def load_cookie(self) -> set[int]:
        """Load cookies from saved file.
        """
        new_uid = set()
        try:
            with open("cookies.json", "r", encoding="utf-8") as f:
                content = f.read()
            content = json.loads(content)
        except FileNotFoundError:
            content = {}
        for uid in content:
            uint = content[uid]["UID"]
            if uint in self._uids:
                continue
            self._cookies[uint] = BiliCookie(uint)
            self._cookies[uint].set_cookies(
                sessdata=content[uid]["SESSDATA"],
                csrf=content[uid]["bili_jct"],
                uid_ckmd5=content[uid]["DedeUserID__ckMd5"],
                sid=content[uid]["sid"],
                refresh_token=content[uid]["refresh_token"]
            )
            self._uids.add(uint)
            new_uid.add(uint)
        if (new_len := len(new_uid)) > 0:
            print(f"[CookieKeepAlive] loads {new_len} new users.")
            print(f"[CookieKeepAlive] alive: {len(self._uids)}")
        return new_uid

    def save_cookie(self) -> None:
        """Save current cookies into files.
        """
        content = {}
        for uid in self._cookies:
            content[str(uid)] = json.loads(str(self._cookies[uid]))
        content = json.dumps(content, ensure_ascii=False,
                             separators=(",", ":"))
        with open("cookies.json", "w", encoding="utf-8") as f:
            f.write(content)

    def clean_dead(self) -> None:
        dead_uid = set()
        for uid in self._cookies:
            if not self._cookies[uid].is_checking:
                print(f"[CookieKeepAlive] user {uid} cookie is dead.")
                dead_uid.add(uid)
                self._uids.remove(uid)
        for u in dead_uid:
            del self._cookies[u]

    def random_cookie(self) -> str:
        index = choice(list(self._cookies.keys()))
        return self._cookies[index].cookie_string

    def status(self) -> int:
        return len(self._uids)

    def run(self) -> None:
        self.load_cookie()
        for uid in self._cookies:
            self._cookies[uid].start()
        while len(self._uids) != 0 and not self._closed:
            self.save_cookie()
            time.sleep(60)
            new_uid = self.load_cookie()
            for uid in new_uid:
                self._cookies[uid].start()
            self.clean_dead()

    def close(self) -> None:
        self._closed = True
        for uid in self._cookies:
            self._cookies[uid].stop_update()


if __name__ == '__main__':
    cookie = CookieKeepAlive()
    cookie.start()
    try:
        cookie.join()
    except KeyboardInterrupt:
        cookie.close()
