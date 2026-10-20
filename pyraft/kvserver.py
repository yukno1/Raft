# kvserver.py

import kvapp
from socket import *
import message

KVADDR = ("localhost", 15000)


class KVServer:
    def __init__(self):
        self.app = kvapp.KVApp()
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.bind(KVADDR)
        self.sock.listen()

    def run(self):
        while True:
            client, addr = self.sock.accept()
            print("Connection from:", addr)
            self.handle_client(client)

    def handle_client(self, sock):
        while True:
            cmd = message.recv_message(sock).decode("utf-8")
            response = self.app.run_command(cmd)
            message.send_message(sock, response.encode("utf-8"))


if __name__ == "__main__":
    serv = KVServer()
    serv.run()
