from socket import socket, AF_INET, SOCK_STREAM

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('localhost', 12345))
msg=sock.recv(1000)
print("Current time is:", msg.decode('utf-8'))