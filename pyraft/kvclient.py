from socket import AF_INET, SOCK_STREAM, socket

from .kvserver import KVADDR
from .message import recv_message, send_message


def main(addr):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(addr)
    while True:
        msg = input("KV >")
        if not msg:
            break
        send_message(sock, msg.encode("utf-8"))
        response = recv_message(sock)
        print(response.decode("utf-8"))
    sock.close()


main(KVADDR)
