'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket


'''
Test send portion of the autofill stuff, this would be the process that gets data from the autofill process
'''


class SocketTestSender():
    
    def __init__(self):
        self.PORT = 50088
        self.HOST = 'localhost' #local host
#         print 'Bang'
        
    def getSocket(self):
        '''
        Get a hold of the socket that will be used to talk with the AutoFill control process
        '''
#         print "Start!"
        self.SOC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.SOC.settimeout(15.0)
            self.SOC.connect((self.HOST,self.PORT))
            return True
        except Exception:
            print 'Socket Connection Failed'
            return False
    
    def _releaseSocket(self):
        '''
        Release the socket when the interface closes
        '''
        
        self.SOC.close()
    
    def _sendCommand(self,commandString):
        '''
        Send the command entered by the user to the socketThread
        :commandString: - String, input from the users
        '''
        writeSocketFile = self.SOC.makefile(mode='w')
#         print "Writing:",commandString
        writeSocketFile.write(commandString+'\n')
        writeSocketFile.close()
#         msg = "Sending '%s' through socket"%(commandString)
#         print msg
    
    def _receiveCommandReply(self):
        '''
        Recieve reply from the sent command, 
        '''
        replyFile = self.SOC.makefile(mode='r')
        reply = replyFile.readline()
        replyFile.close()
        formattedReply = reply.replace('|','\n')
        return formattedReply
    
    def mainInput(self):
        '''
        Main input for the user, feeds input to commandInputs() for completing tasks
        '''  
        msg = 'Remote interface has started. Please enter the commands below.'
        print msg
#         self._printOKGreen(msg)      
        success = self.getSocket()
        if success == True:
#             try:
            while True:
                print "got Socket!"
                answer = raw_input('>>')
                if answer == 'exit':
#                     self._sendCommand(answer)
                    self._releaseSocket()
                    break
                self._sendCommand(answer)
                reply = self._receiveCommandReply()
                print "Received:",reply
#             except socket.error:
#                 msg = "Socket Send failed, most likely a timeout on the receiver."
#                 print msg
#             finally:
#                 self._releaseSocket()
        elif success == False:
            msg = "Connection attempt failed"
            print msg
        
        
        
if __name__ == '__main__':
    tester = SocketTestSender()
    tester.mainInput()
