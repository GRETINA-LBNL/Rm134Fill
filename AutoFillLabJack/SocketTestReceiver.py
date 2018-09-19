'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket
'''
Socket that will act as the auto fill process, it has all the information for the current autofill system status

'''
PORT = 50007
HOST = 'localhost' #local host
if __name__ == '__main__':
    SOC = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    SOC.bind((HOST,PORT))
    SOC.listen(1)
    conn,addr = SOC.accept()
    while True:
        data = conn.recv(1024)
        if not data:
            break
        if data == 'Hello, world':
            conn.send('I Said Good Day!')
        
    conn.close()
    