"""
independent of networking and other details

2 operations:
- leaders append new entries at end of own logs
- followers append entries provided by leader to log.
if leader send inconsistent data (gap or other), reject

The log is 1-based: index 0 holds a sentinel entry. Raft never uses it, but it
lets AppendEntries describe the very beginning of a log with
(prev_index=0, prev_term=0). Entries are always contiguous from index 0.
"""

from dataclasses import dataclass


@dataclass
class LogEntry:
    index: int
    term: int  # Term of leader that created the entry
    command: bytes  # App cmd. Never used by Raft


class RaftLog:
    def __init__(self, initial_entries=None):
        self._entries: list[LogEntry] = [LogEntry(0, 0, b"")]  # sentinel
        if initial_entries:
            for entry in initial_entries:
                self._entries.append(LogEntry(entry.index, entry.term, entry.command))
        self._check()

    def __repr__(self):
        return f"RaftLog({self._entries[1:]})"

    def __len__(self):
        return len(self._entries) - 1

    def _check(self):
        """Indexes must stay contiguous; a gap means a broken AppendEntries."""
        assert all(entry.index == index for index, entry in enumerate(self._entries))

    @property
    def last_index(self) -> int:
        return self._entries[-1].index

    @property
    def last_term(self) -> int:
        return self._entries[-1].term

    @property
    def entries(self) -> list[LogEntry]:
        """Copies of all real entries (for tests and debugging)."""
        return self.entries_from(1)

    def entry_at(self, index: int) -> LogEntry | None:
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def term_at(self, index: int) -> int | None:
        entry = self.entry_at(index)
        return entry.term if entry is not None else None

    def entries_from(self, index: int) -> list[LogEntry]:
        """Entries starting at index. Copies, so a message can't mutate this log."""
        return [
            LogEntry(e.index, e.term, e.command) for e in self._entries[max(index, 0) :]
        ]

    def append_new_cmd(self, leader_term: int, command: bytes) -> LogEntry:
        """Used by leader. Always work"""
        entry = LogEntry(self._entries[-1].index + 1, leader_term, command)
        self._entries.append(entry)
        return entry

    def append_entries(self, prev_index: int, prev_term: int, entries) -> bool:
        """Used by follower. Might fail.

        First verify the log has a matching entry at prev_index. Then append the
        leader's entries: a conflicting entry truncates this log from that index
        onwards, while entries that already agree are left alone (so replaying
        an AppendEntries is harmless).
        """
        if self.term_at(prev_index) != prev_term:
            return False

        entries = list(entries)
        for offset, entry in enumerate(entries):
            index = prev_index + 1 + offset
            existing = self.entry_at(index)
            if existing is not None and existing.term == entry.term:
                continue
            del self._entries[index:]
            self._entries.extend(
                LogEntry(i, e.term, e.command)
                for i, e in enumerate(entries[offset:], start=index)
            )
            break
        self._check()
        return True


def test_append_new_cmd():
    log = RaftLog()
    assert log.last_index == 0
    assert log.last_term == 0
    assert log.append_new_cmd(1, b"set a 1") == LogEntry(1, 1, b"set a 1")
    assert log.append_new_cmd(3, b"set a 2") == LogEntry(2, 3, b"set a 2")
    assert len(log) == 2
    assert log.last_index == 2 and log.last_term == 3


def test_append_entries_checks_prev():
    log = RaftLog()
    log.append_new_cmd(1, b"set a 1")  # (1, 1)
    # gap: index 2 is not in the log
    assert not log.append_entries(2, 1, [LogEntry(3, 1, b"set a 3")])
    # wrong term at index 1
    assert not log.append_entries(1, 2, [LogEntry(2, 2, b"set a 2")])
    assert len(log) == 1
    # empty log described by the sentinel
    assert RaftLog().append_entries(0, 0, [LogEntry(1, 1, b"set a 1")])


def test_append_entries_conflict_and_idempotence():
    log = RaftLog()
    log.append_new_cmd(1, b"a")  # (1, 1)
    log.append_new_cmd(1, b"b")  # (2, 1)
    log.append_new_cmd(1, b"c")  # (3, 1)

    incoming = [LogEntry(2, 2, b"B"), LogEntry(3, 2, b"C")]
    assert log.append_entries(1, 1, incoming)
    assert log.entries == [LogEntry(1, 1, b"a")] + incoming
    # replaying the same message must not duplicate/truncate anything
    assert log.append_entries(1, 1, incoming)
    assert len(log) == 3
    # a shorter matching prefix keeps this log's extra entries
    assert log.append_entries(0, 0, [LogEntry(1, 1, b"a")])
    assert len(log) == 3


if __name__ == "__main__":
    test_append_new_cmd()
    test_append_entries_checks_prev()
    test_append_entries_conflict_and_idempotence()
