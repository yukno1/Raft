import pickle
import threading

from kvapp import KVApp
from raftlog import RaftLog
from raftlogic import ChatMessage, Message, RaftLogic
from raftnet import RaftNetNode


class RaftServer:
    def __init__(self, nodenum: int):
        self.node_num = nodenum
        self.node = RaftNetNode(nodenum)  # Communications
        self.logic = RaftLogic(nodenum)  # Consensus module
        self.log = RaftLog()  # Log
        self.app = KVApp()  # State machine

    def encode_msg(self, msg: Message) -> bytes:
        # encode
        return pickle.dumps(msg)

    def decode_msg(self, msg: bytes) -> Message:
        return pickle.loads(msg)

    def send(self, msg: Message):
        # high-level send that works with Message instance
        self.node.send(msg.dest, self.encode_msg(msg))

    def run(self):
        while True:
            # pseudo-code
            raw_msg = self.node.receive()
            msg = self.decode_msg(raw_msg)
            # decode?
            self.logic.handle_msg(msg)

        # outgoing messages or response?

    def console(self):
        while True:
            cmd = input(f"Node {self.node_num} > ")
            dest, msg = cmd.split()
            self.send(ChatMessage(int(dest), self.node_num, msg))

    def start(self):
        print(f"Start Raft Node {self.node_num}")
        self.node.start()
        threading.Thread(target=self.run).start()


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        server = RaftServer(int(sys.argv[1]))
        server.start()
        server.console()
