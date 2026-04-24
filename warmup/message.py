# size-prefixed messages
#
# in the raft project, different servers are
# going to send msgs. It's critical that msg stays intact
# as a single object
#
# many ways: high-level lib/framework, e.g., ZeroMQ or web api;
# program using sockets or some low-level code

def send_message(sock, msg: str):
    size=b'%10d' % len(msg)
    sock.sendall(size)
    sock.sendall(msg)

def recv_exactly(sock, nbytes:int):
    chunks=[]
    while nbytes>0:
        chunk=sock.recv(nbytes)
        if chunk==b'':
            raise IOError("Incomplete message")
        chunks.append(chunk)
        nbytes-=len(chunk)
    return b''.join(chunks)

def recv_message(sock):
    size=int(recv_exactly(sock, 10))
    return recv_exactly(sock, size)
