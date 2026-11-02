# kvserver.py
import threading
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket

from pyraft.kvapp import KVApp
from pyraft.message import *

KVADDR = ("localhost", 15000)


class KVServer:
    def __init__(self):
        self.app = KVApp()
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.sock.bind(KVADDR)
        self.sock.listen()

    def run(self):
        while True:
            client, addr = self.sock.accept()
            print("Connection from:", addr)
            threading.Thread(target=self.handle_client, args=(client)).start()

    def handle_client(self, sock):
        try:
            while True:
                cmd = recv_message(sock).decode("utf-8")
                response = self.app.execute_command(cmd)
                send_message(sock, response.encode("utf-8"))
        except OSError:
            print("Client went away")


if __name__ == "__main__":
    serv = KVServer()
    serv.run()
