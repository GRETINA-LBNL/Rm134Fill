'''
Created on Sep 16, 2016

@author: ADonoghue
'''
# import curses
# import time
from datetime import datetime as dt
from AutoFillLabJack.AutoFillInterface import AutoFillInterface
from threading import Event
import logging.config
import socket


class AutoFillGUI():
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.cleanDict = {"Name":str,'Fill Timeout':int,'Minimum Fill Time':int,'Detector Max Temperature':int}
        self.shortHand = {'enabled':'Fill Enabled','schedule':'Fill Schedule','timeout':'Fill Timeout','minimum':'Minimum Fill Time',\
                          'temp':'Detector Max Temperature','name':'Name','logging':'Temperature Logging'}
        self.chillShortHand = {'enabled':'Fill Enabled','timeout':'Chill Timeout'}
        
        self.timeFormat = '%H:%M'
        self.inputSelectDict = {'set':self.detectorSettingsInput,'get':self.checkDetectorSettingsInput,'temp':self.detectorTempInput,\
                               'error':self.errorInput,'start':self.startInput,'stop':self.stopInput,'exit':self.exitInput,\
                                'write':self.writeSettingsInput,'graph':self.graphInput,'help':self.helpInput}
        self.hostname = socket.gethostname()
        if self.hostname == 'MMStrohmeier-S67':
            self.loggingConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\winLogging.cfg'
            self.HelpFile = 'C:\Python\Rm134Fill\AutoFillLabJack\HelpDoc.txt'
            self.MiniHelpFile = 'C:\Python\Rm134Fill\AutoFillLabJack\MiniHelpDoc.txt'
        elif self.hostname == 'localhost':
            self.loggingConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/logging.cfg'
            self.HelpFile = '/home/gretina/Rm134Fill/AutoFillLabJack/HelpDoc.txt'
            self.MiniHelpFile = '/home/gretina/Rm134Fill/AutoFillLabJack/MiniHelpDoc.txt'
        self.getLogs()
        self.exitEvent = Event()
        
        
    def initInterface(self):
        '''
        Initalize the interface module
        '''
        try:
            self.interface = AutoFillInterface(eventLog=self.EventLog,hostname=self.hostname)
            msg = self.interface.initController()
        except:
            msg = 'Interface failed to initalize'
            self._printError(msg)
            raise
        if msg != None:
            self._printError(msg)

    def checkThreadRunning(self):
        '''
        Check if the thread that does everything is running and notify the user if the thread is not
        running. Used in some of the input functions
        '''
        status = self.interface.threadRunningCheck()
        if status == False:
            msg="Operation thread is not running, values read from detector will not be updated"
            self._printError(msg)       

    def initRelease(self):
        '''
        Release the lab jack and turn everything off
        '''
        self.interface.initRelease()
        del self.interface
    
    
    def getLogs(self):
        '''
        get the temperature logs have have been started
        grap the event log as well
        '''
        logging.config.fileConfig(fname=self.loggingConfigFile)
        self.EventLog = logging.getLogger('EventLog')
        
        
    def detectorSettingsInput(self,text):
        '''
        Take the input and confirm it is the correct type
        :text: - input from the user that is changing, should be '1 Enabled True' => Detector 1 Fill Enabled True
        
        '''
        sptext = text.split(' ')
        if sptext[0] == 'chill':
            detector = 'Line Chill'
            try: 
                option = self.chillShortHand[sptext[1]] #use the shorthand dict to get the correct option to set
            except KeyError:
                msg = '%s not a valid option for %s'%(sptext[1],detector)
                self._printFail(msg)
                return False


        else:
            detector = 'Detector %s'%sptext[0]
            try:
                option = self.shortHand[sptext[1]] #use the shorthand dict to get the correct option to set
            except KeyError:
                msg = '%s not a valid option for %s'%(sptext[1],detector)
                self._printFail(msg)
                return False
            if option == 'Fill Schedule':
                value = self._fillScheduleInput(sptext)
                if value == False:
                    return value
            elif option == 'Fill Enabled' or option == 'Temperature Logging': 
                inputValue = sptext[2].capitalize()            
                if inputValue == 'False': #bool() conversion does not work for strings, do the test long hand 
                    value = 'False'
                elif inputValue == 'True':
                    value = 'True'
                else:
                    msg = '"%s" not a valid setting for %s'%(sptext[2],option)
                    self._printFail(msg)
                    return False
            elif option == 'Name': #the values for names may have spaces in them so join them together
                values = sptext[2:] #get all the values
                value = ' '.join(values)
            else:
                try:
                    value = self.cleanDict[option](sptext[2]) #use the clean dict to confirm the correct type of input for the option
                except:
                    errorString = '"%s" not a valid value for %s setting %s'%(sptext[2],detector,option)
                    self._printFail(errorString)
                    return False
            self.interface.changeDetectorSetting(detector,option,value)
            self.EventLog.info('Setting change entered: Detector %s, option %s, value %s'%(detector,option,value))
            
    def _fillScheduleInput(self,sptext):
        '''
        Handle values for the fill schedule input
        '''    
        if ',' in sptext[2]:
            fillTimes = sptext[2].split(',')      
        else:
            fillTimes = [sptext[2]]
        i = 0
        errorString = ''
        numTimes = len(fillTimes)
        for fillTime in fillTimes: #check that the times are valid 24H times
            try:
                dt.strptime(fillTime,self.timeFormat)
            except ValueError:
                if numTimes > 1:
                    errorString += '%s is not a valid fill time in fill schedule %s\n'%(fillTime,sptext[2])
                else:
                    errorString += '%s is not a valid fill time\n'%(fillTime)
        if errorString != '':
            self._printFail(errorString)
            return False
        value = sptext[2]   
        return value

    def checkDetectorChanges(self):
        '''
        Show the user what changes they have entered
        '''
        detectors,settings,values,returnString = self.interface.collectDetectorSettings()
        print '\n'+returnString
        settingsDict,enabledDetectors = self.interface.constructSettingsDict(detectors, settings, values)
        errorString = self.interface.checkFillScheduleConflicts(settingsDict,enabledDetectors)
        if errorString:
            msg1 = '\n   The settings have not be written due to the above error'
            msg2 = '\n   Please amend the fill schedule to fix the conflicts'
            self._printError(errorString+msg1+msg2)
            error = True
        else:
            error = False
        return detectors,settings,values,error
    
    def writeDetectorChanges(self,detectors,settings,values):
        '''
        After the user has confirmed the settings are correct write them to the config file
        '''
        self.checkThreadRunning()
        self.interface.writeDetectorSettings(detectors,settings,values)
        
    def checkDetectorSettingsInput(self,text):
        '''
        Check the detector settings for the 
        :text: - options for getting detector settings command, '1'
        full command is 'get 1','all' is also a valid detector number
        '''   
        if text == 'all':
            detectors = ['1','2','3','4','5','6','chill']
        elif text in ['1','2','3','4','5','6','chill']:
            detectors = [text]
        else:
            errorString = '"%s" not a valid detector number'%text
            self._printFail(errorString)
            return False
        for number in detectors:
            if number == 'chill':
                name = 'Line Chill'
            else:
                name = 'Detector %s'%number
            print '\n'+self.interface.readDetectorConfig(name)
        
    
    def detectorTempInput(self,text):
        '''
        Display the current temperature for the detector number
        :text: - options for command requesting detector temp, something like 'detector 1' or 'all' 
        total command will be 'temp 1'
        '''
        detectorNumbers = map(lambda x: str(x),range(1,7))
        detectors = []   
        self.checkThreadRunning()
        if text in detectorNumbers:
            detectors.append('Detector %s'%text)
        if text == 'All' or text == 'all':
            for num in detectorNumbers:
                detectors.append('Detector %s'%num)
        else:
            errorString = '"%s" not a valid detector name'%text
            self._printFAIL(errorString)
        temps,names = self.interface.getDetectorTemps(detectors)
        displayString = ''
        for (detector,name,temp) in zip(detectors,names,temps):
            displayString += '%s (%s) temperature %sC\n'%(detector,name,temp)
        print displayString
    
    def writeSettingsInput(self,text):
        '''
        Write the settings that the user entered using the detectorSettingsInput method
        '''
        detectors,settings,values,errors = self.checkDetectorChanges()
        if errors is True:
            return
#         print 'Detectors',detectors
#         print 'Settings', settings
#         print 'Values', values
        answer = raw_input('Write the settings show above(Y/n)?')
        if answer.upper() == 'Y':
            self.writeDetectorChanges(detectors,settings,values)
            print 'Settings have been written'
        else:
            print "Fine I won't\n"
    
    def errorInput(self,text):
        '''
        Check the interface for any errors
        :text: - to dispaly error this is empty, to clear errors this will be 'clear'
        '''
        if text == 'clear':
            self.interface.cleanErrorDict()
            self.EventLog.info('Cleaning error log')
        else:
            errorString = self.interface.readDetectorErrors()
            print errorString

    def _printError(self,errorMsg):
        '''
        Print the error msg in yellow to make sure the operator sees it
        '''
        print bcolors.WARNING+"Warning: "+errorMsg+bcolors.ENDC
    
    def _printFail(self,failMsg):
        '''
        Print a fail to the scree, ie red
        '''
        print bcolors.FAIL+failMsg+bcolors.ENDC

#     def loggingInput(self,text):
#         '''
#         Enable/Disable temperature logging for the specified detecotr
#         :text: - detector number and value (True/False)
#         '''
#         spText = text.split(' ')
#         
#         if spText[1] not in ['True','False']:
#             msg = '%s not a valid option for logging'
#             print msg
#             return False
#         
#         if spText[0] == 'all' or spText[0] == 'All':
#             detectors = []
#             values = [spText[1]]*6
#             for num in range(1,7): #1-6
#                 detectors.append('Detector %d'%num)
#         else:
#             values = [spText[1]]
#             detectors = ['Detector %s'%text]
#        for (detector,value) in zip(detectors,values):
#             self.interface.setTempLogging(detector,value)
                  
                         
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
            self._printFail(msg)
            return
        commandOptions = ' '.join(sText)
        inputFunction(commandOptions)
        return True
    
    def startInput(self,text):
        '''
        start the running thread
        :text: - not used, needed to make it common
        '''   
        error = self.interface.startRunThread()
        self.EventLog.info('Starting Auto Fill Operation')
        if error != '': #problems in the fill schedule are checked for before a run is started.
            self.EventLog.info('Starting Stopped, error: %s'%error)
            print error
        
    def stopInput(self,text):
        '''
        stop the running thread
        :text: - not used, needed to make it common
        '''
        self.EventLog.info('Stopping Auto Fill Operation')
        self.interface.stopRunThread()
    
    def exitInput(self,text):
        '''
        Stop the running thread then close everything
        :text: - not used, needed to make it common
        '''
        self.interface.initRelease()
        del self.interface
        self.EventLog.info('Exiting Auto Fill Program')
        self.exitEvent.set()
        
    def helpInput(self,text):
        '''
        Print the help file to screen
        :text: - 
        '''
        
        if text == 'all':
            fileName = self.HelpFile
        elif text == '':
            fileName = self.MiniHelpFile
        with open(fileName, 'r') as helpFile:
            print helpFile.read()
        
#         print 'HELP!'
        
    def graphInput(self,text):
        '''
        Produce a graph the detector temperature for the given detector number
        '''
#         detNum = text.split(' ')[1]
        if text in ['1','2','3','4','5','6']:
            detName = 'Detector %s'%text
            self.interface.graphDetectorTemp(detName)
        else:
            msg = '"%s" not a valid detector number'%text
            print msg
    
    def mainInput(self):
        '''
        Main input for the user, feeds input to commandInputs() for completing tasks
        '''  
        print bcolors.OKBLUE+'Auto Fill program has been started, enter "start" to start auto fill operation.'\
                +bcolors.ENDC
        self.initInterface()
        while True:
            if self.exitEvent.is_set() == True:
                break
            answer = raw_input('>>')
            self.EventLog.debug('Entered command: %s'%answer)
            self.commandInputs(answer)
            if self.exitEvent.is_set() == True:
                break
        
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
    AutoFillGUI = AutoFillGUI()
    AutoFillGUI.mainInput()
#     AutoFillGUI.startWindow()
#     AutoFillGUI.addText()
#     AutoFillGUI.endWindow()
