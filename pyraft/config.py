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
