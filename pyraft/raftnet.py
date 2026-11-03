# Raft networking layer
# different server nodes need to be able to communicate by
# sending messages.


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
        """

    def receive(self) -> bytes:
        """
        receive message from any other nodes.\n
        Consideration:
        - do we know sender?
        - message can be sent any time.
        - wait when no messge available?
        """
