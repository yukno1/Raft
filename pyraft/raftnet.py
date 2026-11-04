# Raft networking layer
# different server nodes need to be able to communicate by
# sending messages.
import queue
import threading
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket

import message
import raftconfig

# message encoding
# what data format?
# who is responsible for? network layer?


class RaftNetNode:
    def __init__(self, nodenum: int):
        self.nodenum = nodenum
        self.incoming = queue.Queue()
        self.outgoing = {}  # connection cache

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

        # may be used by multi-thread

        # in real, raft send messages thousand times per second
        # this is like a cache prior channel
        if dest not in self.outgoing:
            sock = socket(AF_INET, SOCK_STREAM)
            try:
                sock.connect(raftconfig.SERVERS[dest])
                self.outgoing[dest] = sock
            except OSError:
                return
        try:
            message.send_message(self.outgoing[dest], msg)
        except OSError:
            # problem with sending, maybe network is dead or remote machine is dead.
            # Discard connection
            self.outgoing.pop(dest).close()

    def receive(self) -> bytes:
        """
        receive message from any other nodes.\n
        Consideration:
        - do we know sender?
        - message can be sent any time.
        - wait when no messge available?
        """
        return self.incoming.get()

    def start(self):
        threading.Thread(target=self._run_server).start()
        print(f"Raft node: {self.nodenum} running")

    def _run_server(self):
        """
        each node operates as a server that must be able to
        receive incoming connections.
        """
        sock = socket(AF_INET, SOCK_STREAM)
        # Silence "addr" in use error
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        sock.bind(raftconfig.SERVERS[self.nodenum])
        sock.listen()

        while True:
            client, addr = sock.accept()
            # have to receive messages from any node at any time
            threading.Thread(target=self._receive_msgs, args=[client]).start()

    def _receive_msgs(self, sock):
        """
        receive as many as possible.
        simply put messages on queue
        """
        try:
            while True:
                msg = message.recv_message(sock)
                self.incoming.put(msg)
        except OSError:
            # client connection went away
            sock.close()


if __name__ == "__main__":
    node_num = int(input("Enter Node Number: "))
    node = RaftNetNode(node_num)
    node.start()
