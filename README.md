# AutoFishing

自动获取神奇饼干, 支持多账号

## 环境要求
* Python >= 3.10

## 开始使用
建议使用venv隔离环境

### 拉取仓库
* `git clone https://github.com/Radekyspec/AutoFishing.git`

### 安装依赖
* `pip3 install -r requirements.txt`

## 入口点

### 添加账号
运行`GenerateCmd.py`, 根据提示输入对应Cookie值: 
* `SESSDATA`
* `bili_jct`(`csrf`)
* `UID`
* `uid_ckmd5`(`DedeUserID__ckMd5`)
* `sid`
* `refresh_token`(web端该值存储在`localStorage`中的`ac_time_value`字段中，在登录成功后返回并保存)

复制输出的内容，新建另一个`cookies.json`文件，首先输入一对英文大括号`{}`，再在**大括号内**粘贴复制的内容

最终文件结构应该类似于：
```json
{
    "114514": {
        "UID": 114514,
        "SESSDATA": "some_SESSDATA",
        "bili_jct": "some_csrf",
        "DedeUserID": 114514,
        "DedeUserID__ckMd5": "some md5",
        "sid": "some sid",
        "refresh_token": "some token"
    },
    "1919810": {
        "UID": 1919810,
        "SESSDATA": "some sess",
        "bili_jct": "some csrf",
        "DedeUserID": 1919810,
        "DedeUserID__ckMd5": "md5",
        "sid": "some sid",
        "refresh_token": "another token"
    }
}
```
如有多个账号，重复这个步骤即可

### 运行
在终端中输入`python3 app.py`来运行

上一步中粘贴导入的cookie便会开始自动刷新，最新的cookie会存放在目录下`cookies.json`文件内
该文件包含所有敏感信息，请确保文件安全，如意外泄漏文件内容需立即更改所有导入账号的密码

## 关于录播姬cookie自动刷新

首先**需要打开录播姬的HTTP API功能**

打开目录下的`RecCookieUpdater.py`文件, 修改文件开头的`HOST`字段为**在录播姬启动时绑定的HTTP接口地址**，如果是跟着[录播姬文档](https://rec.danmuji.org/reference/arguments/)操作则无需修改，默认值为`http://localhost:2356`

运行：`python3 RecCookieUpdater.py`，之后每隔一小时便会随机读取文件中的一个账户cookie进行更新替换
