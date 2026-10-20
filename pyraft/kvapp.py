# kvapp.py
from typing import Dict


class KVApp:
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


if __name__ == "__main__":
    test_kvapp()
