# AutoFishing

自动摸鱼

## 环境要求
* Python >= 3.10

## 入口点

在`SendDanmaku.py`中设置对应Cookie: 
* `SESSDATA`
* `csrf`(`bili_jct`)
* `uid_ckmd5`(`DedeUserID_ckMd5`)
* `sid`
* web端的`refresh_token`(存储于`localStorage.ac_time_value`中)）
