'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket
'''
Test send portion of the autofill stuff, this would be the process that gets data from the autofill process
'''
PORT = 50007
HOST = 'localhost' #local host
if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send('Hello, world')
    data = s.recv(1024)
    print data
#     print 'Data Sent'