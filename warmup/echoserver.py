from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from message import send_message, recv_message
from threading import Thread


def echo_message(sock):
    try:
        while True:
            msg = recv_message(sock)
            send_message(sock, msg)
    except IOError:
        sock.close()


def main(addr):
    sock = socket(AF_INET, SOCK_STREAM)
    # common problem with sockets is error: "Address already in use."
    # can be suppressed by setsockopt()
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)

    sock.bind(addr)
    sock.listen()
    while True:
        client, addr = sock.accept()
        print("Connection from ", addr)
        Thread(
            target=echo_message,
            args=[
                client,
            ],
        ).start()


main(("localhost", 12345))
