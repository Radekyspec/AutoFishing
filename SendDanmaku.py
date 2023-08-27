from __future__ import annotations

import requests
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from queue import Queue

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from WebHeartBeat import WebHeartBeat


class DanmakuSender:
    """A class that send danmaku. Support multiusers.
    
    === Public Attributes ===
    uids: a set of user id.
    rooms: a dictionary which key is uid and value is a set of rooms.
    
    === Private Attributes ===
    _executor: a thread pool executor used to send danmaku.
    _heartbeat: instance of WebHeartBeat.
    _danmu_queue: a queue used to store room id.
    _scheduler: a BackgroundScheduler instance used to resend danmaku after living.
    """
    uids: set[int]
    rooms: dict[int, set[int]]
    _executor: ThreadPoolExecutor
    _heartbeat: WebHeartBeat
    _danmu_queue: dict[int, Queue]
    _scheduler: BackgroundScheduler

    def __init__(self, *args: tuple[int]) -> None:
        self.uids = set(args)
        self.rooms = {uid: set() for uid in args}
        self._heartbeat = WebHeartBeat()
        self._heartbeat.on_del_room = partial(self._heartbeat.on_del_room, self.close)
        self._danmu_queue = {uid: Queue() for uid in args}
        self._executor = ThreadPoolExecutor()
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        for uid in args:
            self._executor.submit(self.fishing, uid)
    
    def add_user(self, *uid: tuple[int]) -> None:
        [self.uids.add(u) for u in uid]
        self._heartbeat.add_user(*uid)
        for i in uid:
            self.rooms[i] = set()
            self._danmu_queue[i] = Queue()
    
    def set_cookies(self, uid: int, *args, **kwargs) -> None:
        if uid not in self.uids:
            raise ValueError("You should add user first.")
        self._heartbeat.set_cookies_by_uid(uid, *args, **kwargs)
    
    def open(self, uid: int) -> None:
        if uid not in self.uids:
            return
        self._executor.submit(self.fishing, uid)
        while True:
            room_ids = self.get_fishing_list()
            differences = list(filter(lambda x: x not in self.rooms[uid], room_ids))
            self._heartbeat.add_heartbeat(uid, *differences)
            for room_id in differences:
                self.rooms[uid].add(room_id)
                self.put_danmaku(uid, room_id)
            time.sleep(10)
    
    def put_danmaku(self, uid: int, room_id: int) -> None:
        self._scheduler.add_job(
            func=self._danmu_queue[uid].put,
            trigger=IntervalTrigger(hours=2),
            args=(room_id,),
            id=f"KeepFishingAlive_{room_id}",
            coalesce=True,
            next_run_time=datetime.now(),
            replace_existing=True,
        )
        
    def close(self, uid: int, *room_ids) -> None:
        if uid not in self.uids:
            return
        for room_id in room_ids:
            if room_id not in self.rooms[uid]:
                continue
            self.rooms[uid].remove(room_id)
    
    @staticmethod
    def get_fishing_list() -> list[int]:
        url = "https://api.live.bilibili.com/xlive/virtual-interface/v1/app/detail?app_id=1659814658645"
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers).json()
        fishing_list = response["data"]["is_using_anchors"]
        fishing_list = list(map(lambda x: x["room_id"], fishing_list))
        return fishing_list

    def fishing(self, uid) -> None:
        while True:
            room_id = self._danmu_queue[uid].get()
            self._heartbeat.send_danmaku(uid, room_id, "摸鱼")
            time.sleep(3)


if __name__ == '__main__':
    sender = DanmakuSender()
    uid = 178856569
    sender.add_user(uid)
    sender.set_cookies(uid,
                       sessdata="",
                       csrf="",
                       uid_ckmd5="",
                       sid="",
                       refresh_token="")
    sender.open(uid)