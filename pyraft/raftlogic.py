"""Raft consensus logic.

A pure state machine: no sockets, no threads, no clocks. The server feeds it
events (incoming messages, local client requests, timer ticks) and gets back
the list of messages to send. Committed commands are exposed through
take_applied() so the server can run them on the state machine (KVApp) and
answer the waiting client.
"""

import random
import threading
from dataclasses import dataclass, field

import raftconfig
from raftlog import LogEntry, RaftLog


@dataclass
class Message:
    dest: int


# debug
@dataclass
class ChatMessage(Message):
    sender: int
    text: str

    def __repr__(self):
        return f"{self.sender} said {self.text}"


# Response sent to ack chat message
@dataclass
class ChatResponse(Message):
    sender: int
    orig_text: str

    def __repr__(self):
        return f"{self.sender} got {self.orig_text}"


@dataclass
class AppendEntries(Message):
    """Replicate log entries (also used as the leader's heartbeat)."""

    sender: int
    term: int
    prev_index: int
    prev_term: int
    entries: list[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse(Message):
    sender: int
    term: int
    success: bool
    match_index: int


@dataclass
class RequestVote(Message):
    sender: int
    term: int
    last_index: int
    last_term: int


@dataclass
class RequestVoteResponse(Message):
    sender: int
    term: int
    vote_granted: bool


@dataclass
class ClientRequest:
    """Local event (never sent over the network): a KV client command."""

    command: bytes
    event: threading.Event = field(default_factory=threading.Event)
    result: bytes = b""

    def reply(self, result: bytes):
        if not self.event.is_set():
            self.result = result
            self.event.set()


class RaftLogic:
    def __init__(
        self,
        nodenum,
        log=None,
        peers=None,
        election_timeout_min=None,
        election_timeout_max=None,
        heartbeat_ticks=None,
    ):
        self.nodenum = nodenum
        self.log = log if log is not None else RaftLog()
        self.peers = (
            list(peers)
            if peers is not None
            else [n for n in raftconfig.SERVERS if n != nodenum]
        )
        self.election_timeout_min = (
            election_timeout_min or raftconfig.ELECTION_TIMEOUT_MIN
        )
        self.election_timeout_max = (
            election_timeout_max or raftconfig.ELECTION_TIMEOUT_MAX
        )
        self.heartbeat_ticks = heartbeat_ticks or raftconfig.HEARTBEAT_TICKS

        # persistent state
        self.curr_term = 0
        self.voted_for = None

        # volatile state
        self.role = "follower"  # follower | candidate | leader
        self.leader_id = None
        self.commit_index = 0
        self.last_applied = 0
        self.votes = set()
        self.next_index = {}  # leader only: next log index to send to each peer
        self.match_index = {}  # leader only: highest known replicated index

        # timers, measured in ticks (see raftconfig)
        self.election_elapsed = 0
        self.election_timeout = 0
        self.heartbeat_elapsed = 0
        self._reset_election_timer()

        # side effects collected while handling a single event
        self._outgoing = []
        self._applied = []  # (index, command) ready for the state machine
        self.client_requests = {}  # log index -> ClientRequest waiting for commit

    def __repr__(self):
        return (
            f"RaftLogic(node={self.nodenum}, role={self.role}, "
            f"term={self.curr_term}, leader={self.leader_id}, "
            f"commit={self.commit_index}, log={self.log})"
        )

    # ---- event plumbing -------------------------------------------------
    def send(self, msg):
        self._outgoing.append(msg)

    def take_applied(self):
        """Entries committed since the last call, for the server to execute."""
        applied, self._applied = self._applied, []
        return applied

    def resolve_client(self, index: int, result: bytes):
        """Server reports the state machine's answer for a committed command."""
        req = self.client_requests.pop(index, None)
        if req is not None:
            req.reply(result)

    def handle_msg(self, msg) -> list[Message]:
        """Dispatch messages / local events."""
        self._outgoing = []
        if isinstance(msg, ChatMessage):
            self.handle_chat_msg(msg)
        elif isinstance(msg, ChatResponse):
            self.handle_chat_resp(msg)
        elif isinstance(msg, AppendEntries):
            self.handle_append_entries(msg)
        elif isinstance(msg, AppendEntriesResponse):
            self.handle_append_entries_response(msg)
        elif isinstance(msg, RequestVote):
            self.handle_request_vote(msg)
        elif isinstance(msg, RequestVoteResponse):
            self.handle_request_vote_response(msg)
        elif isinstance(msg, ClientRequest):
            self.handle_client_request(msg)
        else:
            raise TypeError(f"Can't handle {msg}")
        return self._outgoing

    def handle_tick(self) -> list[Message]:
        """One timer tick: elections for followers/candidates, heartbeats for leaders."""
        self._outgoing = []
        self.election_elapsed += 1
        if self.role == "leader":
            self.heartbeat_elapsed += 1
            if self.heartbeat_elapsed >= self.heartbeat_ticks:
                self.heartbeat_elapsed = 0
                self._broadcast_append_entries()
        elif self.election_elapsed >= self.election_timeout:
            self._start_election()
        return self._outgoing

    # ---- debug chat (from the original skeleton) ------------------------
    def handle_chat_msg(self, msg: ChatMessage):
        print(msg)
        self.send(ChatResponse(msg.sender, self.nodenum, msg.text))

    def handle_chat_resp(self, msg: ChatResponse):
        """print out ack"""
        print(msg)

    # ---- term / role helpers --------------------------------------------
    @property
    def cluster_size(self):
        return len(self.peers) + 1

    def _has_majority(self, count):
        return count > self.cluster_size // 2

    def _reset_election_timer(self):
        self.election_elapsed = 0
        self.election_timeout = random.randint(
            self.election_timeout_min, self.election_timeout_max
        )

    def _fail_pending(self, reason: str):
        for req in self.client_requests.values():
            req.reply(reason.encode())
        self.client_requests.clear()

    def _become_follower(self, term: int, leader_id=None):
        was_leader = self.role == "leader"
        if term > self.curr_term:
            self.curr_term = term
            self.voted_for = None  # a new term means a new vote
        self.role = "follower"
        self.leader_id = leader_id
        self.votes = set()
        self.next_index = {}
        self.match_index = {}
        self._reset_election_timer()
        if was_leader:
            self._fail_pending("error: no longer leader")

    def _start_election(self):
        self.curr_term += 1
        self.role = "candidate"
        self.voted_for = self.nodenum
        self.votes = {self.nodenum}
        self.leader_id = None
        self._reset_election_timer()
        for peer in self.peers:
            self.send(
                RequestVote(
                    peer,
                    self.nodenum,
                    self.curr_term,
                    self.log.last_index,
                    self.log.last_term,
                )
            )
        if self._has_majority(len(self.votes)):  # single-node cluster
            self._become_leader()

    def _become_leader(self):
        self.role = "leader"
        self.leader_id = self.nodenum
        self.votes = set()
        self.heartbeat_elapsed = 0
        for peer in self.peers:
            self.next_index[peer] = self.log.last_index + 1
            self.match_index[peer] = 0
        # Raft only counts current-term entries when committing, so a new
        # leader appends a no-op first (it also commits older entries).
        self.log.append_new_cmd(self.curr_term, b"")
        self._broadcast_append_entries()
        self._try_advance_commit()

    # ---- log replication -------------------------------------------------
    def _send_append_entries(self, dest: int):
        next_index = self.next_index.get(dest, self.log.last_index + 1)
        prev_index = next_index - 1
        prev_term = self.log.term_at(prev_index)
        if prev_term is None:  # only possible after a badly backed-up next_index
            prev_index = self.log.last_index
            prev_term = self.log.last_term
            next_index = prev_index + 1
        self.send(
            AppendEntries(
                dest,
                self.nodenum,
                self.curr_term,
                prev_index,
                prev_term,
                self.log.entries_from(next_index),
                self.commit_index,
            )
        )

    def _broadcast_append_entries(self):
        for peer in self.peers:
            self._send_append_entries(peer)

    def _try_advance_commit(self):
        """Leader: commit N if a majority has N and log[N] is from this term."""
        if self.role != "leader":
            return
        for index in range(self.log.last_index, self.commit_index, -1):
            if self.log.term_at(index) != self.curr_term:
                break
            replicas = 1 + sum(
                1 for peer in self.peers if self.match_index.get(peer, 0) >= index
            )
            if self._has_majority(replicas):
                self._advance_commit(index)
                break

    def _advance_commit(self, new_commit: int):
        new_commit = min(new_commit, self.log.last_index)
        if new_commit <= self.commit_index:
            return
        self.commit_index = new_commit
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log.entry_at(self.last_applied)
            self._applied.append((entry.index, entry.command))

    # ---- RPC handlers ----------------------------------------------------
    def handle_append_entries(self, msg: AppendEntries):
        if msg.term < self.curr_term:
            self.send(
                AppendEntriesResponse(
                    msg.sender, self.nodenum, self.curr_term, False, 0
                )
            )
            return

        if msg.term > self.curr_term or self.role != "follower":
            self._become_follower(msg.term, msg.sender)
        else:
            self.leader_id = msg.sender
            self._reset_election_timer()

        if self.log.append_entries(msg.prev_index, msg.prev_term, msg.entries):
            match_index = msg.prev_index + len(msg.entries)
            self._advance_commit(min(msg.leader_commit, match_index))
            self.send(
                AppendEntriesResponse(
                    msg.sender, self.nodenum, self.curr_term, True, match_index
                )
            )
        else:
            # Leader will decrement next_index and retry with an earlier prefix.
            self.send(
                AppendEntriesResponse(
                    msg.sender, self.nodenum, self.curr_term, False, 0
                )
            )

    def handle_append_entries_response(self, msg: AppendEntriesResponse):
        if msg.term > self.curr_term:
            self._become_follower(msg.term)
            return
        if self.role != "leader" or msg.term != self.curr_term:
            return
        if msg.success:
            if msg.match_index > self.match_index.get(msg.sender, 0):
                self.match_index[msg.sender] = msg.match_index
                self.next_index[msg.sender] = msg.match_index + 1
            self._try_advance_commit()
        else:
            self.next_index[msg.sender] = max(
                1, self.next_index.get(msg.sender, self.log.last_index + 1) - 1
            )
            self._send_append_entries(msg.sender)

    def handle_request_vote(self, msg: RequestVote):
        if msg.term < self.curr_term:
            self.send(
                RequestVoteResponse(msg.sender, self.nodenum, self.curr_term, False)
            )
            return
        if msg.term > self.curr_term:
            self._become_follower(msg.term)

        # "up-to-date" log: compare last term, then last index
        up_to_date = (msg.last_term, msg.last_index) >= (
            self.log.last_term,
            self.log.last_index,
        )
        granted = up_to_date and self.voted_for in (None, msg.sender)
        if granted:
            self.voted_for = msg.sender
            self._reset_election_timer()
        self.send(
            RequestVoteResponse(
                msg.sender, self.nodenum, self.curr_term, granted
            )
        )

    def handle_request_vote_response(self, msg: RequestVoteResponse):
        if msg.term > self.curr_term:
            self._become_follower(msg.term)
            return
        if (
            self.role != "candidate"
            or msg.term != self.curr_term
            or not msg.vote_granted
        ):
            return
        self.votes.add(msg.sender)
        if self._has_majority(len(self.votes)):
            self._become_leader()

    def handle_client_request(self, msg: ClientRequest):
        if self.role != "leader":
            hint = f" (leader is {self.leader_id})" if self.leader_id else ""
            msg.reply(f"error: not leader{hint}".encode())
            return
        entry = self.log.append_new_cmd(self.curr_term, msg.command)
        self.client_requests[entry.index] = msg
        self._broadcast_append_entries()
        self._try_advance_commit()


def test_chat():
    logic = RaftLogic(1)
    resp = logic.handle_msg(ChatMessage(1, 2, "hi"))
    assert resp == [ChatResponse(2, 1, "hi")]


class _Simulation:
    """In-memory network used by the tests: no sockets, no real time."""

    def __init__(self, size=5):
        self.nodes = {}
        for n in range(1, size + 1):
            peers = [p for p in range(1, size + 1) if p != n]
            # staggered timeouts keep elections deterministic
            self.nodes[n] = RaftLogic(
                n,
                RaftLog(),
                peers,
                election_timeout_min=10 + n,
                election_timeout_max=10 + n,
                heartbeat_ticks=2,
            )
        self.dead = set()
        self.applied = {}

    def _deliver(self, msgs):
        while msgs:
            msg = msgs.pop(0)
            if msg.sender in self.dead or msg.dest in self.dead:
                continue
            msgs.extend(self.nodes[msg.dest].handle_msg(msg))
        self._collect_applied()

    def _collect_applied(self):
        # stands in for RaftServer running committed commands on KVApp
        for n, logic in self.nodes.items():
            for index, command in logic.take_applied():
                self.applied.setdefault(n, []).append(command)
                logic.resolve_client(index, b"ok")

    def tick(self, times=1):
        for _ in range(times):
            msgs = []
            for n, logic in self.nodes.items():
                if n not in self.dead:
                    msgs.extend(logic.handle_tick())
            self._deliver(msgs)

    def submit(self, n, command):
        req = ClientRequest(command)
        self._deliver(self.nodes[n].handle_msg(req))
        return req

    def leader(self):
        return next(
            (
                n
                for n, logic in self.nodes.items()
                if logic.role == "leader" and n not in self.dead
            ),
            None,
        )


def test_election():
    sim = _Simulation()
    for _ in range(50):
        sim.tick()
        if sim.leader() is not None:
            break
    leader = sim.leader()
    assert leader == 1  # smallest election timeout wins
    term = sim.nodes[leader].curr_term
    assert term >= 1
    assert all(logic.curr_term == term for logic in sim.nodes.values())
    assert all(
        logic.role == "follower" for n, logic in sim.nodes.items() if n != leader
    )


def test_replication():
    sim = _Simulation()
    sim.tick(20)
    leader = sim.leader()
    assert leader is not None

    req = sim.submit(leader, b"set foo bar")
    sim.tick(5)  # followers learn leader_commit on the next heartbeat
    assert req.event.is_set() and req.result == b"ok"

    entries = sim.nodes[leader].log.entries
    assert LogEntry(2, sim.nodes[leader].curr_term, b"set foo bar") in entries
    for n, logic in sim.nodes.items():
        assert logic.log.entries == entries
        assert logic.commit_index == sim.nodes[leader].commit_index
        assert sim.applied[n].count(b"set foo bar") == 1


def test_not_leader_rejected():
    sim = _Simulation()
    sim.tick(20)
    follower = next(n for n, logic in sim.nodes.items() if logic.role == "follower")
    req = sim.submit(follower, b"get foo")
    assert req.event.is_set() and req.result.startswith(b"error: not leader")


def test_failover_repairs_divergent_log():
    sim = _Simulation()
    sim.tick(20)
    old_leader = sim.leader()
    assert sim.submit(old_leader, b"set a 1").result == b"ok"
    sim.tick(5)

    # partition the old leader, then give it an entry nobody else will see
    sim.dead = {old_leader}
    sim.submit(old_leader, b"set a 2")
    for _ in range(50):
        sim.tick()
        if sim.leader() not in (None, old_leader):
            break
    new_leader = sim.leader()
    assert new_leader is not None and new_leader != old_leader
    assert sim.nodes[new_leader].curr_term > sim.nodes[old_leader].curr_term

    req = sim.submit(new_leader, b"set b 3")
    sim.tick(5)
    assert req.result == b"ok"

    # old leader rejoins: higher term wins and its stale entry is replaced
    sim.dead = set()
    sim.tick(10)
    entries = sim.nodes[new_leader].log.entries
    assert sim.nodes[old_leader].log.entries == entries
    assert b"set a 2" not in [e.command for e in entries]
    assert all(
        logic.log.entries == entries for n, logic in sim.nodes.items() if n != old_leader
    )


if __name__ == "__main__":
    test_chat()
    test_election()
    test_replication()
    test_not_leader_rejected()
    test_failover_repairs_divergent_log()
    print("all raft logic tests passed")
