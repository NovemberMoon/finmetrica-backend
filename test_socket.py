import socket

s = socket.create_connection(("127.0.0.1", 5432))
print("connected")

data = s.recv(1024)
print(data)

s.close()