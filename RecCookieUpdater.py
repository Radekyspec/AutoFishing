import json
import os
import random
import sys

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URI = "/api/config/global"


def get_config(host):
    return requests.get(host + URI).json()


def fetch_cookie(f_path):
    with open(os.path.realpath(f_path), "r", encoding="utf-8") as f:
        content = f.read()

    content = json.loads(content)
    content = content[random.choice(list(content.keys()))]

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")  # 避免容器共享内存问题
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    cookies_list = [
        {
            "name": "SESSDATA",
            "value": content['SESSDATA'],
            "domain": ".bilibili.com",
            "path": "/",
            "secure": True,  # 若 SameSite=None 则必须 secure
            "sameSite": "None"
        },
        {
            "name": "bili_jct",
            "value": content['bili_jct'],
            "domain": ".bilibili.com",
            "path": "/",
            "secure": True,  # 若 SameSite=None 则必须 secure
            "sameSite": "None"
        },
        {
            "name": "DedeUserID__ckMd5",
            "value": content['DedeUserID__ckMd5'],
            "domain": ".bilibili.com",
            "path": "/",
            "secure": True,  # 若 SameSite=None 则必须 secure
            "sameSite": "None"
        },
        {
            "name": "DedeUserID",
            "value": str(content['UID']),
            "domain": ".bilibili.com",
            "path": "/",
            "secure": True,  # 若 SameSite=None 则必须 secure
            "sameSite": "None"
        },
        {
            "name": "sid",
            "value": content['sid'],
            "domain": ".bilibili.com",
            "path": "/",
            "secure": True,  # 若 SameSite=None 则必须 secure
            "sameSite": "None"
        }
    ]
    driver.execute_cdp_cmd("Network.enable", {})

    for cookie in cookies_list:
        # 确保将 expiry ➜ expires
        if 'expiry' in cookie:
            cookie['expires'] = cookie['expiry']
            del cookie['expiry']
        driver.execute_cdp_cmd("Network.setCookie", cookie)

    driver.execute_cdp_cmd("Network.disable", {})
    driver.get("https://www.bilibili.com/")
    session = requests.Session()
    for c in driver.get_cookies():
        session.cookies.set(c['name'], c['value'], domain=c['domain'])
    cookie_dict = session.cookies.get_dict()
    print("; ".join([f"{key}={cookie_dict[key]}" for key in cookie_dict]))
    # driver.get("https://api.bilibili.com/x/web-interface/nav")
    # print(driver.page_source)
    driver.quit()
    return "; ".join([f"{key}={cookie_dict[key]}" for key in cookie_dict])


def update_config(host, f_path):
    cur_config = get_config(host)
    cur_config["optionalCookie"]["hasValue"] = True
    cur_config["optionalCookie"]["value"] = fetch_cookie(f_path)
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    cur_config = json.dumps(
        cur_config, ensure_ascii=False, separators=(",", ":"))
    assert requests.post(host + URI, data=cur_config,
                         headers=headers).status_code, 200
    print("Update success")


def main():
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from datetime import datetime

    try:
        f_path = os.path.join(os.path.abspath(__compiled__.containing_dir),
                              "cookies.json")
        if len(sys.argv) < 2:
            print("Usage: .\RecCookieupdater.exe host ...")
            input()
            return
    except NameError:
        f_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "cookies.json")
        if len(sys.argv) < 2:
            print("Usage: python3 RecCookieupdater.py host ...")
            return

    host = sys.argv[1]
    scheduler = BlockingScheduler()
    scheduler.add_job(update_config, args=(host, f_path),
                      misfire_grace_time=3600, max_instances=10,
                      trigger=IntervalTrigger(hours=1),
                      next_run_time=datetime.now())
    scheduler.start()
    # update_config()


if __name__ == '__main__':
    main()
