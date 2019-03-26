'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket
import logging.config

class RemoteInterface(object):
    '''
    This is the remote interface for the Rm134AutoFill system
    It will send requests to the server socket for infomation about the current state of the Rm134AutoFill system 
    '''


    def __init__(self):
        '''
        
        
        '''
        self.PORT = 50088
        self.HOST = 'localhost'
        self.hostname = socket.gethostname()
        self.endSend = '*'
        if self.hostname == 'MMStrohmeier-S67':
            self.loggingConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\winRemoteLogging.cfg'
            self.helpFile = 'C:\Python\Rm134Fill\AutoFillLabJack\RemoteHelpDoc.txt'
            
        elif self.hostname == 'localhost':
            self.loggingConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/remotelogging.cfg'
            self.helpFile = '/home/gretina/Rm134Fill/AutoFillLabJack/RemoteHelpDoc.txt'
        sucess = self.getLogs()
        self.mainInput()

    
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
            try:
                while True:
                    print "got Socket!"
                    answer = raw_input('>>')
                    if answer == 'exit':
                        self._sendCommand(answer)
                        self._releaseSocket()
                        break
                    self._sendCommand(answer)
                    reply = self._receiveCommandReply()
                    print reply
            except socket.error:
                msg = "Socket Send failed, most likely a timeout on the receiver."
                print msg
            finally:
                self._releaseSocket()
        elif success == False:
            msg = "Connection attempt failed"
            print msg
        

    def getLogs(self):
        '''
        get the temperature logs have have been started
        grap the event log as well
        '''
        logging.config.fileConfig(fname=self.loggingConfigFile)
        self.EventLog = logging.getLogger('RemoteEventLog')
    
#    def commandInputs(self,text):
#        '''
#        Select the input function baised on the first word in the command
#        :text: - input text from user
#        '''
#        sText = text.split(' ')
#        command = sText.pop(0) # remove the first text entered, it is the command and the rest of the methods will not be used
#        try:
#            inputFunction = self.inputSelectDict[command]
#        except KeyError:
#            msg = '"%s" not a valid command\n enter <help> to print help file' %(command)
#            print msg
#            return
#        commandOptions = ' '.join(sText)
#        funcName = inputFunction.__name__
#        self.EventLog.info('Command %s called to gather information.'%funcName)
#        inputFunction(commandOptions)
#        return True
            
    def _printError(self,errorMsg):
        '''
        Print a fail to the scree, ie red
        :errorMsg: - string that will be printed to the screen in red
        '''
        print '\t'+bcolors.FAIL+errorMsg+bcolors.ENDC

    def _printOKGreen(self,okMsg):
        '''
        Print the ok msg to the screen in green
        :okMsg: - string that will be printed to screen in green
        '''
        print '\t'+bcolors.OKGREEN+okMsg+bcolors.ENDC
    
    def _printOKBlue(self,okMsg):
        '''
        Print the ok msg to the screen in blue
        :okMsg: - string that will be printed to screen in green
        '''
        print '\t'+bcolors.OKBLUE+okMsg+bcolors.ENDC

    
            

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

if __name__ == '__main__':
    remote = RemoteInterface()
