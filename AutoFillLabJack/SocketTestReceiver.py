'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket
from _socket import SHUT_RDWR
# import select
'''
Socket that will act as the auto fill process, it has all the information for the current autofill system status

'''

class SocketTestReceiver():
    
    def __init__(self):
        self.PORT = 50088
        self.HOST = 'localhost' #local host
        self.replyDict = {'get 1':"Temp 99\nName: AA",
             'get 2':"Temp 10\nName: bang",
             'get 3':"Temp 30\nName: Shorts",
             'get 4':"Temp 44\nName: My",
             'get 5':"Temp 00\nName: Eat",
            }
    def getSocket(self):
        '''
        Get a hold of the socket that will be used to talk with the AutoFill control process
        '''
        self.SOC = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.SOC.bind((self.HOST,self.PORT))
        
    
    def _releaseSocket(self,conn):
        '''
        Release the socket when the interface closes
        '''
        conn.shutdown(SHUT_RDWR)
        conn.close()
#         self.SOC.close()
    
    def _sendCommand(self,conn,commandString):
        '''
        Send the command entered by the user to the socketThread
        :commandString: - String, input from the users
        '''
        
        writeSocketFile = conn.makefile(mode='w')
        cleanCommand = commandString.replace('\n','|')
        writeSocketFile.write(cleanCommand+'\n')
        writeSocketFile.close()
        msg = "Sending '%s' through socket"%(commandString)
        print msg
    
    def _receiveCommandReply(self,conn):
        '''
        Recieve reply from the sent command, 
        '''
        replyFile = conn.makefile(mode='r')
        reply = replyFile.readline()
        replyFile.close()
        reply = reply.replace('\n','')
        return reply
    
    def mainInput(self):
        '''
        Main input for the user, feeds input to commandInputs() for completing tasks
        '''  
        
        self.getSocket()
        self.SOC.listen(1)
        
        (conn,addr) = self.SOC.accept()
        print "Got socket!"
        conn.settimeout(10.0) #set the timeout after the connection has been made
        try:
            while True:
    
                command = self._receiveCommandReply(conn)
                if command == 'exit':
                    self._releaseSocket()
                    break
                else:
                    try:
                        reply = self.replyDict[command]
                    except KeyError:
                        reply = "Not a valid Command"
                    self._sendCommand(conn,reply)
        except socket.timeout:
            msg = "Socket Closed"
            print msg
        finally:
            self._releaseSocket(conn)
        
        



if __name__ == '__main__':
    tester = SocketTestReceiver()
    tester.mainInput()
    