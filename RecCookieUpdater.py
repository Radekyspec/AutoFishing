import json
import sys
import os
import random
import requests

URI = "/api/config/global"
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")


def get_config(host):
    return requests.get(host + URI).json()


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


def update_config(host):
    cur_config = get_config(host)
    cur_config["optionalCookie"]["hasValue"] = True
    cur_config["optionalCookie"]["value"] = fetch_cookie()
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    cur_config = json.dumps(
        cur_config, ensure_ascii=False, separators=(",", ":"))
    assert requests.post(host + URI, data=cur_config, headers=headers).status_code, 200
    print("Update success")


def main():
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from datetime import datetime

    if "py" in sys.argv[0]:
        if len(sys.argv) < 3:
            print("Usage: python3 RecCookieupdater.py host ...")
            return
        host = sys.argv[2]
    else:
        if len(sys.argv) < 2:
            print("Usage: .\RecCookieupdater.exe host ...")
            input()
            return
        host = sys.argv[1]
    scheduler = BlockingScheduler()
    scheduler.add_job(update_config, args=(host,), misfire_grace_time=3600, max_instances=10, trigger=IntervalTrigger(hours=1),
                      next_run_time=datetime.now())
    scheduler.start()
    # update_config()


if __name__ == '__main__':
    main()
