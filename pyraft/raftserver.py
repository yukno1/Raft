"""Glue between the pure consensus logic, the network and the KV state machine."""

import pickle
import queue
import sys
import threading
import time

import raftconfig
from kvapp import KVApp
from kvserver import KVServer
from raftlog import RaftLog
from raftlogic import ChatMessage, ClientRequest, Message, RaftLogic
from raftnet import RaftNetNode


class RaftServer:
    def __init__(self, nodenum: int):
        self.node_num = nodenum
        self.node = RaftNetNode(nodenum)  # Communications
        self.log = RaftLog()  # Log
        self.logic = RaftLogic(nodenum, self.log)  # Consensus module
        self.app = KVApp()  # State machine
        self.kvserver = KVServer(raftconfig.CLIENTS[nodenum], self.submit_command)

    def encode_msg(self, msg: Message) -> bytes:
        return pickle.dumps(msg)

    def decode_msg(self, msg):
        # Local events (ClientRequest) are put straight on the incoming queue.
        return pickle.loads(msg) if isinstance(msg, (bytes, bytearray)) else msg

    def send(self, msg: Message):
        # high-level send that works with Message instance
        self.node.send(msg.dest, self.encode_msg(msg))

    def submit_command(self, cmd: bytes) -> bytes:
        """Called by a KV client thread. Blocks until committed or timed out."""
        req = ClientRequest(cmd)
        self.node.deliver(req)
        if not req.event.wait(raftconfig.CLIENT_TIMEOUT):
            return b"error: request timed out"
        return req.result

    def run(self):
        """Single-threaded event loop: messages, client requests and timer ticks."""
        next_tick = time.monotonic() + raftconfig.TICK_INTERVAL
        while True:
            outgoing = []
            try:
                raw_msg = self.node.receive(
                    timeout=max(0, next_tick - time.monotonic())
                )
            except queue.Empty:
                pass
            else:
                outgoing += self.logic.handle_msg(self.decode_msg(raw_msg))

            now = time.monotonic()
            if now >= next_tick:
                outgoing += self.logic.handle_tick()
                next_tick = now + raftconfig.TICK_INTERVAL

            for out in outgoing:
                self.send(out)

            # Committed entries go to the state machine. The answer is handed
            # back to the client request that produced the entry (leader only).
            for index, command in self.logic.take_applied():
                result = b"ok" if not command else self.app.execute_command(command)
                self.logic.resolve_client(index, result)

    def console(self):
        print("Commands: <node> <text> (debug chat) | status")
        while True:
            cmd = input(f"Node {self.node_num} > ")
            if not cmd:
                continue
            if cmd.strip() == "status":
                print(self.logic)
                continue
            try:
                dest, msg = cmd.split()
                self.send(ChatMessage(int(dest), self.node_num, msg))
            except ValueError:
                print("usage: <node> <text> | status")

    def start(self):
        print(f"Start Raft Node {self.node_num}")
        self.node.start()
        self.kvserver.start()
        threading.Thread(target=self.run, daemon=True).start()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        server = RaftServer(int(sys.argv[1]))
        server.start()
        server.console()
    else:
        sys.exit("usage: python raftserver.py <node number>")
