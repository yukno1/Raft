# kvserver.py
import threading
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket

from pyraft.kvapp import KVApp
from pyraft.message import *

KVADDR = ("localhost", 15000)


class KVServer:
    __slots__ = ("app", "sock")

    def __init__(self):
        self.app = KVApp()
        self.sock = socket(AF_INET, SOCK_STREAM)
        # self.consensus_mod = Raft()

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
                cmd = recv_message(sock).decode("utf-8")  # step 1

                # step 2
                # try:
                #     self.consensus_mod.commit(cmd)
                # except NotLeader:
                #     response = "go away"

                response = self.app.execute_command(cmd)  # step 3
                send_message(sock, response.encode("utf-8"))  # step 4
        except OSError:
            print("Client went away")


if __name__ == "__main__":
    serv = KVServer()
    serv.run()
