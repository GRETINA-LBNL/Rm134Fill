'''
Created on Aug 22, 2017

@author: ADonoghue
'''
import socket
import logging
class RemoteInterface(object):
    '''
    This is the remote interface for the Rm134AutoFill system
    It will send requests to the server socket for infomation about the current state of the Rm134AutoFill system 
    '''


    def __init__(self):
        '''
        
        
        '''
        self.inputSelectDict = {'get':self.checkDetectorSettingsInput,'temp':self.detectorTempInput,
                                'error':self.errorInput,'help':self.helpInput}
        
        self.PORT = 50088
        self.HOST = 'localhost'
        if self.hostname == 'MMStrohmeier-S67':
            self.loggingConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\winRemoteLogging.cfg'
            self.helpFile = 'C:\Python\Rm134Fill\AutoFillLabJack\RemoteHelpDoc.txt'
            
        elif self.hostname == 'localhost':
            self.loggingConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/remotelogging.cfg'
            self.helpFile = '/home/gretina/Rm134Fill/AutoFillLabJack/RemoteHelpDoc.txt'
        sucess = self.getLogs()
        if sucess:
            self.mainInput()
        else:
            return
    
    def getSocket(self):
        '''
        Get a hold of the socket that will be used to talk with the AutoFill control process
        '''
        self.SOC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.SOC.connect((self.HOST,self.PORT))
            return True
        except Exception as E:
            self.EventLog.warning('Failed to connect to socket, host %s | port %d'%(self.HOST,self.PORT))
            self.EventLog.exception(E)
            print 'Socket Connection Failed'
            return None
        

    def getLogs(self):
        '''
        get the temperature logs have have been started
        grap the event log as well
        '''
        logging.config.fileConfig(fname=self.loggingConfigFile)
        self.EventLog = logging.getLogger('RemoteEventLog')
    
    def commandInputs(self,text):
        '''
        Select the input function baised on the first word in the command
        :text: - input text from user
        '''
        sText = text.split(' ')
        command = sText.pop(0) # remove the first text entered, it is the command and the rest of the methods will not be used
        try:
            inputFunction = self.inputSelectDict[command]
        except KeyError:
            msg = '"%s" not a valid command\n enter <help> to print help file' %(command)
            print msg
            return
        commandOptions = ' '.join(sText)
        funcName = inputFunction.__name__
        self.EventLog.info('Command %s called to gather information.'%funcName)
        inputFunction(commandOptions)
        return True
    
    def detectorTempInput(self,text):
        '''
        Display the current temperature for the detector number
        :text: - options for command requesting detector temp, something like 'detector 1' or 'all' 
        total command will be 'temp 1'
        '''   
        if text == 'all' or text == 'All':
            detectors = []
            for num in range(1,7): #1-6
                detectors.append('Detector %d'%num)
        else:
            detectors = ['Detector %s'%text]
        cmd = ','.join(detectors)
        self.EventLog.debug('Sending %s to AutoFill process'%cmd)
        self.SOC.send(cmd)
        data = self.SOC.recv(1024) #the data returned will be a string containing the whole
        self.EventLog.debug('Receving %s from AutoFill process'%data)
        sdata = data.split(':')
        temps = sdata[0].split(',')
        names = sdata[1].split(',')
        displayString = ''
        for (detector,name,temp) in zip(detectors,names,temps):
            displayString += '%s (%s) temperature %sC\n'%(detector,name,temp)
        print displayString
        
    def checkDetectorSettingsInput(self,text):
        '''
        Check the detector settings for the 
        :text: - options for getting detector settings command, '1'
        full command is 'get 1'
        '''   
        if text not in ['1','2','3','4','5','5']:
            errorString = '"%s" not a valid detector number'%text
            print errorString
            return False
        else:
            name = 'Detector %s'%text
            cmd = 'get %s'%name
            self.EventLog.debug('Sending %s to AutoFill Process'%cmd)
            self.SOC.send(cmd)
            data = self.SOC.recv(1024)
            self.EventLog.debug('Received %s from the AutoFill Process'%data)
            print data
            
    def mainInput(self):
        '''
        Main input for the user, feeds input to commandInputs() for completing tasks
        '''  
        print 'Auto Fill program has been started, enter "start" to start auto fill operation.'
        while True:
            if self.exitEvent.is_set() == True:
                break
            answer = raw_input('>>')
            self.EventLog.debug('Entered command: %s'%answer)
            self.commandInputs(answer)
            if self.exitEvent.is_set() == True:
                break

if __name__ == '__main__':
    remote = RemoteInterface()
