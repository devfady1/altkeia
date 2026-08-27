import socket
b1 = socket.socket(socket.AF_INET , socket.SOCK_STREAM)
h = "127.0.0.1"
p = 5001
b1.bind((h,p))
b1.listen(3)

while True: 
    connection, A = b1.accept() 
    p2 = connection.recv(2222) 