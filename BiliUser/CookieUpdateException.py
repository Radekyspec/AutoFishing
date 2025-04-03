class CookieUpdateException(BaseException):
    _msg: str

    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self._msg = msg

    def __str__(self) -> str:
        return self._msg
