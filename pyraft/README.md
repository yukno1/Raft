Raft is focused on the problem of creating a replicated app.
For this project, app is a key-value DB. kvapp.py implements this app.

## Layout

- `raftlogic.py` - pure consensus state machine (no sockets/clocks/threads). It
  handles messages, client requests and timer ticks, and returns messages to send.
- `raftlog.py` - replicated log with consistency checks and conflict repair.
- `raftnet.py` - TCP transport between nodes (size-prefixed messages).
- `raftserver.py` - event loop: turns network events, client requests and ticks
  into logic events; runs committed commands on `KVApp`.
- `kvserver.py` / `kvclient.py` - client endpoint of each node and a small CLI.
- `raftconfig.py` - node addresses, client ports and timing constants.

## Run

From the repository root, start one node per terminal (1..5):

```bash
python pyraft/raftserver.py 1
python pyraft/raftserver.py 2
python pyraft/raftserver.py 3
python pyraft/raftserver.py 4
python pyraft/raftserver.py 5
```

Then connect a client to any node:

```bash
python pyraft/kvclient.py 1
KV > set name guido
ok
KV > get name
guido
```

Writes go to the leader only; a follower replies with the leader hint. Only a
majority of nodes needs to be up for the cluster to make progress. The
`status` command in a node's console prints its role, term, commit index and log.

## Test

The logic tests simulate a 5-node cluster in memory (election, replication,
failover and log repair), while `kvapp.py` / `raftlog.py` have unit tests:

```bash
pytest pyraft/raftlog.py pyraft/raftlogic.py pyraft/kvapp.py
```
