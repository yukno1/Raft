from socket import socket, AF_INET, SOCK_STREAM
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
