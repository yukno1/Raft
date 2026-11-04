# kvserver.py
"""Client-facing endpoint of a Raft node.

A command is handed to RaftServer.submit_command(), which blocks until it has
been replicated, committed and applied by the state machine. The answer is
sent back to the client over the same socket. This used to call KVApp directly
(the step-2 comment below); Raft now sits in that spot.
"""

import threading
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket

from message import recv_message, send_message


class KVServer:
    def __init__(self, addr, submit):
        self.addr = addr
        self.submit = submit
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.sock.bind(addr)
        self.sock.listen()

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        print(f"KV client endpoint: {self.addr}")

    def run(self):
        while True:
            client, _ = self.sock.accept()
            threading.Thread(
                target=self.handle_client, args=(client,), daemon=True
            ).start()

    def handle_client(self, sock):
        try:
            while True:
                cmd = recv_message(sock)  # step 1: get the command
                """
                step 2: consensus
                - replication / majority / commit / apply
                - election, timeouts, retries all happen inside RaftLogic
                """
                response = self.submit(cmd)
                send_message(sock, response)  # step 3: reply
        except OSError:
            pass
        finally:
            sock.close()
