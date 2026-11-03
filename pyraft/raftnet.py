# Raft networking layer
# different server nodes need to be able to communicate by
# sending messages.
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket

import config
import message


class RaftNetNode:
    def __init__(self, nodenum: int):
        self.nodenum = nodenum

    def send(self, dest: int, msg: bytes):
        """
        send a message to another node\n
        Consideration:
        - remote machine might be dead
        - send message to myself?
        - wait message to be delivered?
        - any response/ack expected?
        - is message raw bytes?
        """
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect(config.SERVERS[dest])
        message.send_message(sock, msg)

    def receive(self) -> bytes:
        """
        receive message from any other nodes.\n
        Consideration:
        - do we know sender?
        - message can be sent any time.
        - wait when no messge available?
        """

    def _run_server(self):
        """
        each node operates as a server that must be able to
        receive incoming connections.
        """
        sock = socket(AF_INET, SOCK_STREAM)
        # Silence "addr" in use error
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        sock.bind(config.SERVERS[self.nodenum])
        sock.listen()

        while True:
            client, addr = sock.accept()
            self._receive_msg(client)

    def _receive_msg(self, sock):
        """receive as many as possible"""
        try:
            while True:
                msg = message.recv_message(sock)
        except OSError:
            # client went away
            sock.close()
