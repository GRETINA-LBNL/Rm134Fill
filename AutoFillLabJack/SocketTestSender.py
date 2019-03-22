'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket
'''
Test send portion of the autofill stuff, this would be the process that gets data from the autofill process
'''
PORT = 50088
HOST = 'localhost' #local host


def getSocket(self):
    '''
    Get a hold of the socket that will be used to talk with the AutoFill control process
    '''
    self.SOC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        self.SOC.connect((self.HOST,self.PORT))
        self.socketFile = self.SOC.makefile(mode='rw')
        return True
    except Exception as E:
        self.EventLog.warning('Failed to connect to socket, host %s | port %d'%(self.HOST,self.PORT))
        self.EventLog.exception(E)
        print 'Socket Connection Failed'
        return None

def _releaseSocket(self):
    '''
    Release the socket when the interface closes
    '''
    self.socketFile.close()
    self.SOC.close()

def _sendCommand(self,commandString):
        '''
        Send the command entered by the user to the socketThread
        :commandString: - String, input from the users
        '''
        self.socketFile.write(commandString+self.endSend)
        msg = "Sending '%s' through socket"%(commandString)
        print msg
        self.EventLog.debug(msg)

def _receiveCommandReply(self):
    '''
    Recieve reply from the sent command, 
    '''
    reply = ''
    while True:
        reply = self.socketFile.read()
        print "reply:",reply
        if self.endSend in reply:
            break
    return reply

def mainInput(self):
    '''
    Main input for the user, feeds input to commandInputs() for completing tasks
    '''  
    msg = 'Remote interface has started. Please enter the commands below.'
    self._printOKGreen(msg)      
    self.getSocket()
    while True:
        answer = raw_input('>>')
        if answer == 'exit':
            self._releaseSocket()
            break
        self.EventLog.debug('Entered command: %s'%answer)
        self._sendCommand(answer)
        print self._receiveCommandReply()
if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send('Hello, world')
    data = s.recv(1024)
    print data
#     print 'Data Sent'
