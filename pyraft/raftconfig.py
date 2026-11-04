# raft config

# in a production environment, need to configure the Raft cluster, maybe by a file.
#
# mapping of logical server numbers to actual network addr
# Throughout the Raft implementation, servers will only be
# identified by logical addr
SERVERS = {
    1: ("localhost", 15000),
    2: ("localhost", 16000),
    3: ("localhost", 17000),
    4: ("localhost", 18000),
    5: ("localhost", 19000),
}

# Every Raft node also listens for KV clients on a separate port.
CLIENTS = {
    1: ("localhost", 25001),
    2: ("localhost", 25002),
    3: ("localhost", 25003),
    4: ("localhost", 25004),
    5: ("localhost", 25005),
}

# All timing is expressed in ticks: the server turns real time into a stream
# of tick events so that RaftLogic stays free of clocks, threads and sockets.
TICK_INTERVAL = 0.05          # seconds between two ticks
HEARTBEAT_TICKS = 4           # leader heartbeat every 4 ticks (0.2s)
ELECTION_TIMEOUT_MIN = 20     # randomized election timeout: 1.0s .. 2.0s
ELECTION_TIMEOUT_MAX = 40
CLIENT_TIMEOUT = 5            # seconds a client waits for a commit
