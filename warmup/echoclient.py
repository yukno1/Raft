from socket import socket, AF_INET, SOCK_STREAM
from message import send_message, recv_message


def main(addr):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(addr)
    while True:
        msg = input("Say >")
        if not msg:
            break
        send_message(sock, msg.encode("utf-8"))
        response = recv_message(sock)
        print("Received >", response.decode("utf-8"))
    sock.close()


main(("localhost", 12345))
