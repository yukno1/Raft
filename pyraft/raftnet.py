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
        # send() is also called from the console thread, so the cached
        # sockets (and their framing) must be protected.
        self._send_lock = threading.Lock()

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
        with self._send_lock:
            # in real, raft send messages thousand times per second
            # this is like a cache prior channel
            if dest not in self.outgoing:
                sock = socket(AF_INET, SOCK_STREAM)
                try:
                    sock.connect(raftconfig.SERVERS[dest])
                    self.outgoing[dest] = sock
                except OSError:
                    sock.close()
                    return
            try:
                message.send_message(self.outgoing[dest], msg)
            except OSError:
                # problem with sending, maybe network is dead or remote machine is dead.
                # Discard connection
                sock = self.outgoing.pop(dest, None)
                if sock is not None:
                    sock.close()

    def receive(self, timeout=None):
        """
        receive message from any other nodes.\n
        Consideration:
        - do we know sender?
        - message can be sent any time.
        - wait when no messge available?
        """
        # Local events (ClientRequest, ...) are delivered on the same queue,
        # so nothing here assumes the queue only holds raw bytes.
        return self.incoming.get(timeout=timeout)

    def deliver(self, event):
        """Inject a local, non-network event into the server's event loop."""
        self.incoming.put(event)

    def start(self):
        threading.Thread(target=self._run_server, daemon=True).start()
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
            client, _ = sock.accept()
            # have to receive messages from any node at any time
            threading.Thread(
                target=self._receive_msgs, args=(client,), daemon=True
            ).start()

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
