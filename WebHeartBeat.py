from __future__ import annotations

import hashlib
import hmac
import json
import random
import requests
import time
import traceback
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional
from uuid import uuid1

from BiliUser import BiliUser


class WebHeartBeat:
    """A thread used to send heartbeat pack.

    === Public Attributes ===
    users: 
        a dictionary of BiliUser instances for users need to keep alive, 
        which key is uid and value is BiliUser instance.
    closed:
        a dictionary which key is room_id and value is the status of heartbeat worker.
    num: 
        number of sent heartbeat

    === Private Attributes ===
    _executor: 
        internal ThreadPoolExecutor instance used to send heartbeat requests.
    """
    users: dict[int, BiliUser]
    closed: dict[int, bool]
    num: dict[int, int]
    _executor: ThreadPoolExecutor

    def __init__(self, *args: tuple[int]) -> None:
        self.users = {uid: BiliUser(uid) for uid in args}
        self.closed = {}
        self.num = {}
        self._executor = ThreadPoolExecutor()

    def add_user(self, *uid: tuple[int]) -> None:
        for user_id in uid:
            self.users[user_id] = BiliUser(user_id)

    def del_user(self, *uid: tuple[int]) -> None:
        for user_id in uid:
            self.users[user_id].stop()

    def on_del_room(self, callback: Optional[Callable], *args) -> Any:
        for room_id in args:
            self.closed[room_id] = True
        if callback is not None:
            return callback(*args)

    def set_cookies_by_uid(self, uid: int, *args, **kwargs) -> None:
        if uid not in self.users:
            raise ValueError(f"UID {uid} does not exist in heartbeat manager.")
        self.users[uid].set_cookies(*args, **kwargs)

    def add_heartbeat(self, uid: int, *room_ids) -> None:
        """Add <self._web_heartbeat>, <self._X_heartbeat> and <self._heartbeat> into thread pool.
        Room id variable <room_id> must be real room id, not short id.
        """
        user = self.users[uid]
        for room_id in room_ids:
            if room_id in self.closed and not self.closed[room_id]:
                continue
            self.closed[room_id] = False
            self.num[uid] = 0
            self._executor.submit(self._web_heartbeat, user, room_id)
            print(f"[{uid}][{room_id}]", "webHeartBeat start")
            self._executor.submit(self._X_heartbeat, user, room_id)
            print(f"[{uid}][{room_id}]", "X heartbeat start")
            self._executor.submit(self._heartbeat, user, room_id)
            print(f"[{uid}][{room_id}]", "heartBeat start")

    # https://github.com/SocialSisterYi/bilibili-API-collect/issues/343
    def _web_heartbeat(self, user: BiliUser, room_id: int) -> None:
        """Send webHeartBeat.
        This method should keep executing.
        """
        interval = 60
        url = "https://live-trace.bilibili.com/xlive/rdata-interface/v1/heartbeat/webHeartBeat"
        headers = {
            "cookie": user.cookie.cookie_string,
            "origin": "https://live.bilibili.com",
            "referer": f"https://live.bilibili.com/{room_id}",
            "user-agent": user.cookie.ua,
        }
        while not self.closed[room_id] and self.num[user.uid] <= 15:
            time.sleep(interval)
            # {interval}|{room_id}|1|0
            hb_data = b64encode(f"{interval}|{room_id}|1|0".encode(
                encoding="utf-8")).decode(encoding="utf-8")
            params = {
                "hb": hb_data,
                "pf": "web",
            }
            headers.update({
                "cookie": user.cookie.cookie_string
            })
            try:
                response = requests.get(
                    url, params=params, headers=headers).json()
                # print(response)
                assert response["code"] == 0, f"Error sending webHeartBeat, {response}"
                interval = response["data"]["next_interval"]
            except:
                self.on_del_room(user.uid, room_id)
                print(traceback.format_exc())
        print(f"[{user.uid}][{room_id}]", "webHeartBeat end")

    def _heartbeat(self, user: BiliUser, room_id: int) -> None:
        """Send heartBeat.
        This method should execute immeditely and once after every 40s.
        """
        url = "https://api.live.bilibili.com/relation/v1/Feed/heartBeat"
        headers = {
            "cookie": user.cookie.cookie_string,
            "origin": "https://live.bilibili.com",
            "referer": f"https://live.bilibili.com/{room_id}",
            "user-agent": user.cookie.ua,
        }
        while not self.closed[room_id] and self.num[user.uid] <= 15:
            headers.update({
                "cookie": user.cookie.cookie_string
            })
            try:
                response = requests.get(url, headers=headers).json()
                # print(response)
                assert response["code"] == 0 and response["msg"] == "success", \
                    f"Error sending heartBeat, {response}"
            except:
                self.on_del_room(user.uid, room_id)
                print(traceback.format_exc())
            time.sleep(40)
        print(f"[{user.uid}][{room_id}]", "heartBeat end")

    def _X_heartbeat(self, user: BiliUser, room_id: int) -> None:
        """Send X heartbeat.
        This method should keep executing like <self._web_heartbeat>.
        """
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X"
        info_url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
        buvid = self._device_hash()
        b_uuid = str(uuid1())
        device = f"[\"{buvid}\",\"{b_uuid}\"]"
        headers = {
            "cookie": user.cookie.cookie_string,
            "origin": "https://live.bilibili.com",
            "referer": f"https://live.bilibili.com/{room_id}",
            "user-agent": user.cookie.ua,
        }
        base_info = requests.get(info_url, headers=headers).json()["data"]
        ruid, area_id, parent_area = base_info["uid"], base_info["area_id"], base_info["parent_area_id"]
        ids = f"[{parent_area},{area_id},{self.num[user.uid]},{room_id}]"
        ets = int(time.time())
        interval, secret_key, secret_rule = self._E_heartbeat(user=user,
                                                              room_id=room_id,
                                                              ids=ids,
                                                              device=device,
                                                              ruid=ruid)
        time.sleep(interval)
        self.num[user.uid] += 1
        while not self.closed[room_id] and self.num[user.uid] <= 15:
            headers.update({
                "cookie": user.cookie.cookie_string,
            })
            base_info = requests.get(info_url, headers=headers).json()["data"]
            area_id, parent_area = base_info["area_id"], base_info["parent_area_id"]
            ids = f"[{parent_area},{area_id},{self.num[user.uid]},{room_id}]"
            ts = int(time.time() * 1000)
            parsed_data = json.dumps({
                "platform": "web",
                "parent_id": parent_area,
                "area_id": area_id,
                "seq_id": self.num[user.uid],
                "room_id": room_id,
                "buvid": buvid,
                "uuid": b_uuid,
                "ets": ets,
                "time": interval,
                "ts": ts
            }, ensure_ascii=False, separators=(",", ":"))
            data = {
                "s": self._gen_s(parsed_data=parsed_data,
                                 secret_rules=secret_rule,
                                 key=secret_key),
                "id": ids,
                "device": device,
                "ruid": ruid,
                "ets": ets,
                "benchmark": secret_key,
                "time": interval,
                "ts": ts,
                "ua": user.cookie.ua,
                "csrf_token": user.cookie.csrf,
                "csrf": user.cookie.csrf,
                "visit_id": "",
            }
            try:
                response = requests.post(
                    url, headers=headers, data=data).json()
                assert response["code"] == 0, f"Error sending X heartbeat, {response}"
            except:
                self.on_del_room(user.uid, room_id)
                print(traceback.format_exc())
            else:
                interval, secret_key, secret_rule = response["data"]["heartbeat_interval"], \
                    response["data"]["secret_key"], response["data"]["secret_rule"]
                ets = int(time.time())
                self.num[user.uid] += 1
                time.sleep(interval)
        print(f"[{user.uid}][{room_id}]", "X heartbeat end")

    @staticmethod
    def _gen_s(parsed_data: str, secret_rules: list[int], key: str) -> str:
        for rule in secret_rules:
            match rule:
                case 0:
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.md5).hexdigest()
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.md5).hexdigest()
                case 1:
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.sha1).hexdigest()
                case 2:
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.sha256).hexdigest()
                case 3:
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.sha224).hexdigest()
                case 4:
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.sha512).hexdigest()
                case 5:
                    parsed_data = hmac.new(key=key.encode(encoding="utf-8"),
                                           msg=parsed_data.encode(
                                               encoding="utf-8"),
                                           digestmod=hashlib.sha384).hexdigest()
                case _:
                    pass
        return parsed_data

    def _E_heartbeat(self, user: BiliUser, room_id: int, ids: str, device: str,
                     ruid: int) -> tuple[int, str, list[int]]:
        """Send E heartbeat.
        This method should execute only once, which is the first heartbeat request.
        """
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E"
        headers = {
            "cookie": user.cookie.cookie_string,
            "origin": "https://live.bilibili.com",
            "referer": f"https://live.bilibili.com/{room_id}",
            "user-agent": user.cookie.ua,
        }
        ts = str(int(time.time() * 1000))
        data = {
            "id": ids,
            "device": device,
            "ruid": ruid,
            "ts": ts,
            "is_patch": 0,
            "heart_beat": "[]",
            "ua": user.cookie.ua,
            "csrf_token": user.cookie.csrf,
            "csrf": user.cookie.csrf,
            "visit_id": "",
        }
        try:
            response = requests.post(url, headers=headers, data=data).json()
            assert response["code"] == 0, f"Error sending E heartbeat, {response}"
            return response["data"]["heartbeat_interval"], response["data"]["secret_key"], \
                response["data"]["secret_rule"]
        except:
            print(traceback.format_exc())
            self.on_del_room(user.uid, room_id)

    def send_danmaku(self, uid: int, room_id: int, content: str) -> None:
        url = "https://api.live.bilibili.com/msg/send"
        cookie = self.users[uid].cookie
        headers = {
            "cookie": cookie.cookie_string,
            "origin": "https://live.bilibili.com",
            "referer": f"https://live.bilibili.com/{room_id}",
            "user-agent": cookie.ua,
        }
        data = {
            "bubble": 0,
            "msg": content,
            "color": 16772431,
            "mode": 1,
            "room_type": 0,
            "jumpfrom": 0,
            "fontsize": 25,
            "rnd": int(time.time()),
            "roomid": room_id,
            "csrf": cookie.csrf,
            "csrf_token": cookie.csrf,
        }
        response = requests.post(url, headers=headers, data=data).json()
        assert response["code"] == 0, f"Error sending danmaku, {response}"
        print(f"[{uid}]", f"Send {content} to room {room_id}.")

    @staticmethod
    def _device_hash() -> str:
        hash_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()+-".split()
        rand_str = f"{int(time.time() * 1000)}" + \
            "".join(random.choices(hash_str, k=5))
        return hashlib.md5(rand_str.encode(encoding="utf-8")).hexdigest()


if __name__ == '__main__':
    w = WebHeartBeat()
    w.set_cookies_by_uid(178856569,
                         sessdata="",
                         csrf="",
                         uid_ckmd5="",
                         sid="",
                         refresh_token="")
    w.add_heartbeat(178856569, 30321760)
