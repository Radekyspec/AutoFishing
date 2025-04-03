import json
import os
import random
import requests

HOST = "http://localhost:2356"
URI = "/api/config/global"
PATH = "./cookies.json"

URL = HOST + URI
def get_config():
    return requests.get(URL).json()


def fetch_cookie():
    with open(os.path.realpath(PATH), "r", encoding="utf-8") as f:
        content = f.read()

    content: dict = json.loads(content)
    content = content[random.choice(list(content.keys()))]

    return "; ".join([fr"SESSDATA={content['SESSDATA']}",
                      f"bili_jct={content['bili_jct']}",
                      f"DedeUserID={content['UID']}",
                      f"DedeUserID__ckMd5={content['DedeUserID__ckMd5']}",
                      f"sid={content['sid']}", ])


def update_config():
    cur_config = get_config()
    cur_config["optionalCookie"]["hasValue"] = True
    cur_config["optionalCookie"]["value"] = fetch_cookie()
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    cur_config = json.dumps(
        cur_config, ensure_ascii=False, separators=(",", ":"))
    assert requests.post(URL, data=cur_config, headers=headers).status_code, 200
    print("Update success")


if __name__ == '__main__':
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from datetime import datetime
    scheduler = BlockingScheduler()
    scheduler.add_job(update_config, misfire_grace_time=3600, max_instances=10, trigger=IntervalTrigger(hours=1),
                      next_run_time=datetime.now())
    scheduler.start()
    # update_config()