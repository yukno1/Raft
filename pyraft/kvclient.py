import sys
from socket import AF_INET, SOCK_STREAM, socket

import raftconfig
from message import recv_message, send_message


def main(addr):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(addr)
    try:
        while True:
            msg = input("KV > ")
            if not msg:
                break
            send_message(sock, msg.encode("utf-8"))
            response = recv_message(sock)
            print(response.decode("utf-8"))
    finally:
        sock.close()


if __name__ == "__main__":
    # Connect to any node; a follower tells you which node is the leader.
    nodenum = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    main(raftconfig.CLIENTS[nodenum])
