from __future__ import annotations

import requests

from .BiliCookie import BiliCookie


class BiliUser:
    """A class representation of bilibili user.
    
    === Public Attributes ===
    uid: user id.
    cookie: a BiliCookie instance for this user.
    """
    uid: int
    cookie: BiliCookie

    def __init__(self, uid: int) -> None:
        self.uid = uid
        self.cookie = BiliCookie(uid)
    
    def set_cookies(self, *args, **kwargs) -> None:
        self.cookie.set_cookies(*args, **kwargs)
        self.cookie.start()
    
    def stop(self) -> None:
        self.cookie.stop_update()
