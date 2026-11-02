# kvapp.py


class KVApp:
    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def run_command(self, cmd: str) -> str:
        match cmd.split():
            case ["get", key]:
                return self._get(key)
            case ["set", key, value]:
                return self._set(key, value)
            case ["delete", key]:
                return self._delete(key)
            case _:
                return "error: bad command"

    def execute_command(self, msg: bytes) -> bytes:
        """
        Method used by network code to handle messages in/out.\n
        Any decoding/encoding happens here
        """
        cmd = msg.decode("utf-8")
        match cmd.split():
            case ["get", key]:
                response = self._get(key)
            case ["set", key, value]:
                response = self._set(key, value)
            case ["delete", key]:
                response = self._delete(key)
            case _:
                response = "error: bad command"
        return response.encode("utf-8")

    def _get(self, key: str) -> str:
        return self._data.get(key) if self._data.get(key) else ""

    def _set(self, key: str, value: str) -> str:
        self._data[key] = value
        return "ok"

    def _delete(self, key: str) -> str:
        if key in self._data:
            del self._data[key]
        return "ok"


def test_kvapp():
    app = KVApp()
    assert app.run_command("get foo") == ""
    assert app.run_command("set foo bar") == "ok"
    assert app.run_command("get foo") == "bar"
    assert app.run_command("delete foo") == "ok"
    assert app.run_command("get foo") == ""


def test_kvapp_messages():
    app = KVApp()
    assert app.execute_command(b"set name Guido") == b"ok"
    assert app.execute_command(b"get name") == b"Guido"
    assert app.execute_command(b"get x") == b""
    assert app.execute_command(b"delete name") == b"ok"
    assert app.execute_command(b"get name") == b""


if __name__ == "__main__":
    test_kvapp()
    test_kvapp_messages()
