import base64

import flask
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA512
from flask import Flask

from BiliUser import CookieKeepAlive


cookie = CookieKeepAlive()
cookie.start()


def encrypt(message: str) -> str:
    pub_key = RSA.importKey("""\
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAmOmt4K5qkEnJQts44O7Y
TgJZ1aQ8DIAQ/eoccdzzyB4UYVLUSDnIi9RR2OmGpm2j/GZR86iRKJFtLBSVe2No
Z7dMAxYkLSw+laieUiq0UtsTFlZ6E/7ucplkDtGyV4aqB0GXTlDC5AFOJxCQCKnV
yY5r+GIFqNLxVWPcIrdvx5qVh9R/Mx3Zik25hv/tpV0oycrueIwvLp+NEZgBTi8l
f+YE5BgsThiLC/STDe1/lcdJhuBhyd3D6tk/cvHBi30VPgdxF6FZIQblWbx4DMmR
pTyW765KNIzL+gYvXuapNa6MXdBK0sD/FqLhShesmWm7LaPgv+kTnriVreIwJghc
T0MtCwgOYQeTH39ZzCCWL+6AwwJIF01+9NphRhKwqgHyvjofnvwvH2T7sulG0LME
Db11zmj38HywG+3ZgOZR6ntwI+CA/MJKvBj5jjRatK9WnqIgnb1GlUPCcnQFTyVn
uPy7yDB97jXtIy1++RObkd4f3J93HuY6TYtyLjAwrkyFrpWviNilJuR4ozHbhr3A
vNf9abmHRycaw9TeOGF+5N5mMCsOVhsRW2LCgwICo/LTcy2KlAbMUr2q+ISHGcuH
fVxOWea5jJ/gwk/iA11xCxDqvxsiklUXr7QYWbnQirw4YVOrth/6XM64PE4gd8bA
RjCL9JcA6yBn8qh+gEpkwLkCAwEAAQ==
-----END PUBLIC KEY-----""")
    cipher = PKCS1_OAEP.new(pub_key, SHA512)
    encrypted = cipher.encrypt(message.encode(encoding="utf-8"))
    return base64.b64encode(encrypted).decode(encoding="utf-8")


def create_app():
    app = Flask(__name__)

    @app.get("/cookies")
    def cookie_api():
        raw_cookie = cookie.random_cookie()
        encrypted = encrypt(raw_cookie)
        return {
            "code": 0,
            "cookies": encrypted
        }

    @app.get("/status")
    def cookie_status_api():
        return {
            "code": 0,
            "alive": cookie.status()
        }

    @app.get("/")
    def hello_page():
        return flask.Response(
            "Hi there!\n\n"
            "\t· GET /cookies\n"
            "\t· GET /status",
            200,
            mimetype="text/plain")

    @app.errorhandler(404)
    def redirect_to_home(error):
        return flask.redirect(flask.url_for("hello_page")), 301

    return app


if __name__ == '__main__':
    create_app().run()
