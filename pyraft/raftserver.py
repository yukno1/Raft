from kvapp import KVApp
from raftlog import RaftLog
from raftlogic import RaftLogic
from raftnet import RaftNetNode


class RaftServer:
    def __init__(self, nodenum: int):
        self.node_num = nodenum
        self.node = RaftNetNode(nodenum)  # Communications
        self.logic = RaftLogic(nodenum)  # Consensus module
        self.log = RaftLog()  # Log
        self.app = KVApp()  # State machine

    def run(self):
        while True:
            # pseudo-code
            msg = self.node.receive()
            response = self.logic.handle_raw_msg(msg)
            self.node.send(dest, response)
