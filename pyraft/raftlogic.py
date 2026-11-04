class RaftLogic:
    def __init__(self, nodenum):
        self.nodenum = nodenum

    def handle_raw_msg(self, msg: bytes): ...
