'''
Created on Sep 16, 2016

@author: ADonoghue
'''
# import curses
# import time
from datetime import datetime as dt
from AutoFillLabJack.AutoFillInterface import AutoFillInterface
from time import sleep
from threading import Event
import logging.config
import socket
from labjack.ljm import LJMError


class AutoFillGUI():
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.cleanDict = {"Name":str,
                          'Maximum Fill Time':int,
                          'Minimum Fill Time':int,
                          'Detector Max Temperature':int}

        self.shortHand = {'enabled':'Fill Enabled',
                          'schedule':'Fill Schedule',
                          'maximum':'Maximum Fill Time',
                          'minimum':'Minimum Fill Time',
                          'temp':'Detector Max Temperature',
                          'name':'Name',
                          'logging':'Temperature Logging'}

        self.chillShortHand = {'enabled':'Fill Enabled','maximum':'Maximum Fill Time'}
        
        self.timeFormat = '%H:%M'
        self.inputSelectDict ={'set':self.setDetectorSettingsInput,
                               'get':self.getDetectorSettingsInput,
                               'temp':self.detectorTempInput,
                               'error':self.errorInput,
                               'start':self.startInput,
                               'stop':self.stopInput,
                               'exit':self.exitInput,
                               'write':self.writeSettingsInput,
                               'load':self.loadInput,
                               'graph':self.graphInput,
                               'help':self.helpInput}
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
        i=0
        while i<3:
            try:
                msgStatus = "Try #%d to initalize Controller"%i
                self._printOKGreen(msgStatus)
                self.interface = AutoFillInterface(eventLog=self.EventLog,hostname=self.hostname)
                msg = self.interface.initController()
                self.detectorNumbers = self.interface.detectorNumbers
                self.detectorNamesDict = self.interface.detectorNamesDict
                i=4
                msgStatus = "Controller Initalization Successfull"
                self._printOKGreen(msgStatus)
                if msg != '':
                    self._printWarning(msg)
            except LJMError:
                msg = 'Interface Failed to Initalize'
                self.interface.initRelease()
                del self.interface
                self._printWarning(msg)
                i+=1
                if i == 3:
                    raise
            if i <= 2:    
                sleep(3)
        
    def checkThreadRunning(self):
        '''
        Check if the thread that does everything is running and notify the user if the thread is not
        running. Used in some of the input functions
        '''
        status = self.interface.threadRunningCheck()
        if status == False:
            msg="Operation thread is not running, values read from detector will not be updated"
            self._printWarning(msg)       

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
        
        
    def setDetectorSettingsInput(self,text):
        '''
        Take the input and confirm it is the correct type
        :text: - input from the user that is changing, should be '1 Enabled True' => Detector 1 Fill Enabled True
        
        '''
        sptext = text.split(' ')
        detector = self._detectorNameConversion(sptext[0])
        if detector == False: #if the conversion fails don't do anyting
            return False
        if detector == 'Line Chill':
            try: 
                option = self.chillShortHand[sptext[1]] #use the shorthand dict to get the correct option to set
            except KeyError:
                msg = '%s not a valid option for %s'%(sptext,detector)
                self._printError(msg)
                return False

        else:          
            try:
                option = self.shortHand[sptext[1]] #use the shorthand dict to get the correct option to set
            except KeyError:
                msg = '"%s" not a valid option for %s'%(sptext[1],detector)
                self._printError(msg)
                return False
        if option == 'Fill Schedule':
            value = self._fillScheduleInput(sptext)
            if value == False:
                return value
        elif option == 'Fill Enabled' or option == 'Temperature Logging': 
            value = self._boolInput(sptext)
            if value == False:
                return value
        elif option == 'Name': #the values for names may have spaces in them so join them together
            values = sptext[2:] #get all the values
            value = ' '.join(values) #Make sure to get all the value the user wrote           
        else:
            try:
                value = self.cleanDict[option](sptext[2]) #use the clean dict to confirm the correct type of input for option the
            except:
                errorString = '"%s" not a valid value for %s setting %s'%(sptext[2],detector,option)
                self._printError(errorString)
                return False
        self.interface.changeDetectorSetting(detector,option,value)
        self.EventLog.info('Setting change entered: Detector %s, option %s, value %s'%(detector,option,value))
            
    def _fillScheduleInput(self,sptext):
        '''
        Handle values for the fill schedule input
        :sptext: - text from 'set detector schedule' command 
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
                    errorString += '"%s" is not a valid fill time in fill schedule %s\n'%(fillTime,sptext[2])
                else:
                    errorString += '"%s" is not a valid fill time\n'%(fillTime)
        if errorString != '':
            self._printError(errorString)
            return False
        value = sptext[2]   
        return value
    
    def _boolInput(self,sptext):
        '''
        Handle the detector options that have True/False value options
        including Fill Enabled and Temperature Logging
        :sptext: - text input from commands that have True/False values
        '''
        inputValue = sptext[2].capitalize()            
        if inputValue == 'False': #bool() conversion does not work for strings, do the test long hand 
            value = 'False'
        elif inputValue == 'True':
            value = 'True'
        else:
            msg = '"%s" not a valid setting for %s'%(sptext[2],sptext[1])
            self._printError(msg)
            value = False
        return value

    def _detectorNameConversion(self,nameText):
        '''
        Convert the text to the detector name 
        inputs-
            :nameText: - text of input name can be number or detector name
        outputs - 
            :returnNames
        examples: 
            1 -> Detector 1
            <name> -> Detector 1    
        '''
        if nameText == 'chill':
            returnName = 'Line Chill'
        else:
            if nameText in self.detectorNumbers:
                detectorNumber = nameText
                
            else:
                try:
                    detectorNumber = self.detectorNamesDict[nameText]
                    
                except KeyError:
                    detectors = ''
                    msg = '"%s" not a valid detector number or name'%(nameText)
                    self._printError(msg)
                    return False
            returnName = 'Detector %s'%detectorNumber    
        return returnName
    
#    def _checkValidName(self, possibleName):
#        '''
#        check the name does not have any spaces in items
#        :possibleName: - string, name to check if it is valid
#        '''
#        if ' ' in possibleName:
#            msg = "'%s' not a valid name, contains a space."%(possibleName)
#            self._printError(msg)
#            return False
#        elif possibleName == 'chill':
#            msg = "'%s' not a valid name, it is short hand for Line Chill."%(possibleName)
#            self._printError(msg)
#            return False
#        try:
#            self.detectorNamesDict[possibleName]
#            msg = "'%s' not a valid name, name is currently being used."%(possibleName)
#            self._printError(msg)
#            return False
#        except KeyError:
#            return True

    def checkDetectorChanges(self):
        '''
        Show the user what changes they have entered
        '''
        detectors,settings,values,returnString = self.interface.collectDetectorSettings()
        print '\n'+returnString
        errorList = []
        settingsDict,enabledDetectors = self.interface.constructSettingsDict(detectors, settings, values)
        errorString = self.interface.checkValidConfiguration(settingsDict,enabledDetectors)
        if errorString:
            msg = '\n\tPlease amend the fill schedule to fix the conflicts.'
            self._printWarning(errorString+msg)
        return detectors,settings,values
    
    def writeDetectorChanges(self,detectors,settings,values):
        '''
        After the user has confirmed the settings are correct write them to the config file
        :detectors: - list of detector names that will be written
        :settings: - list of detector settings that will be changed
        :values: - list of values to set the detector settings to
        '''
        self.checkThreadRunning()
        self.interface.writeDetectorSettings(detectors,settings,values)
        self.detectorNamesDict = self.interface.detectorNamesDict
        
    def getDetectorSettingsInput(self,text):
        '''
        Check the detector settings for the 
        :text: - options for getting detector settings command, '1'
        full command is 'get 1','all' is also a valid detector number
        '''  
        if text == 'all':
            detectors = self.detectorNumbers
        else:
            detectors = [text] 

        for number in detectors:
            detectorName = self._detectorNameConversion(number)
            if detectorName == False: #if the name conversion fails exit the function
                return False
            print '\n'+self.interface.readDetectorConfig(detectorName)
        
    
    def detectorTempInput(self,text):
        '''
        Display the current temperature for the detector number
        :text: - options for command requesting detector temp, something like 'detector 1' or 'all' 
        total command will be 'temp 1'
        ''' 
        self.checkThreadRunning()
        detectorNumber = self._detectorNameConversion(text)
        if detectorNumber == False:
            return False
        
        temps,names = self.interface.getDetectorTemps(detectorNumber)
        displayString = ''
        for (detector,name,temp) in zip(detectorNumbers,names,temps):
            displayString += '\t%s (%s) temperature:'%(detector,name)+\
                            bcolors.OKGREEN+' %s%sC'%(temp,u"\u00b0")+bcolors.ENDC
        print displayString
    
    def writeSettingsInput(self,text):
        '''
        Write the settings that the user entered using the setDetectorSettingsInput method
        :text: - not used, needed to make the function match the others
        '''
        detectors,settings,values = self.checkDetectorChanges()
#         print 'Detectors',detectors
#         print 'Settings', settings
#         print 'Values', values
        answer = raw_input('Write the settings show above(Y/n)?')
        if answer.upper() == 'Y':
            self.writeDetectorChanges(detectors,settings,values)
            print 'Settings have been written.'
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
            self._printError(errorString)

    def _printWarning(self,warningMsg):
        '''
        Print the error msg in yellow to make sure the operator sees it
        :warningMsg: - string that will be printed to the screen in the 
                        correct color
        '''
        print '\t'+bcolors.WARNING+"Warning: "+warningMsg+bcolors.ENDC
    
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
            self._printError(msg)
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
            errorMsg = 'Run thread did not start. \n\t%s'%(error)       
            self.EventLog.info(errorMsg)
            self._printWarning(errorMsg)
        else:
            msg = 'AutoFill Operation has Started.'
            self._printOKGreen(msg)
        
    def stopInput(self,text):
        '''s
        stop the running thread
        :text: - not used, needed to make it common with other input function
        '''
        self.EventLog.info('Stopping Auto Fill Operation')
        self.interface.stopRunThread()
        self._printOKGreen("AutoFill Operation has Stopped.")
    
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
        :text: - string, option from user. Either blank or 'all'
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
        :text: - string, number of detector to produce graph for
        '''
        detectorNumbers = self._detectorNameConversion(text)
        if detectorNumbers == False:
            return False
        else:
            self.interface.graphDetectorTemp(detectorNumbers)

    def loadInput(self,text):
        '''
        load the changes made to the configuration file
        :text: -not used
        '''
        msgStr = self.interface.loadDetectorConfig()
        print 'Msg',msgStr
        if msgStr != '':
            self._printWarning(msgStr)
            
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

