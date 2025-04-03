import json

import pyperclip


def generate_from_stdin():
    SESSDATA = input("SESSDATA: ")
    csrf = input("bili_jct: ")
    uid = input("UID: ")
    uint = int(uid)
    ckmd5 = input("DedeUserID__ckMd5: ")
    sid = input("sid: ")
    refresh_token = input("refresn_token: ")
    content = {uid: {
        "UID": uint,
        "SESSDATA": SESSDATA,
        "bili_jct": csrf,
        "DedeUserID": uint,
        "DedeUserID__ckMd5": ckmd5,
        "sid": sid,
        "refresh_token": refresh_token
    }}
    result = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    print(result)
    pyperclip.copy(result[1:-1])
    print("Result copied to clipboard.")


if __name__ == '__main__':
    generate_from_stdin()
