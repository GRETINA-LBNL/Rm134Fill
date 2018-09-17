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
        
        self.timeFormat = '%H:%M'
        self.inputSelectDict = {'set':self.detectorSettingsInput,'get':self.checkDetectorSettingsInput,'temp':self.detectorTempInput,\
                                'error':self.errorInput,'start':self.startInput,'stop':self.stopInput,'exit':self.exitInput,\
                                'write':self.writeSettingsInput,'graph':self.graphInput,'help':self.helpInput}
        self.hostname = socket.gethostname()
        if self.hostname == 'MMStrohmeier-S67':
            self.loggingConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\winLogging.cfg'
        elif self.hostname == 'localhost':
            self.loggingConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/logging.cfg'
        self.getLogs()
        self.exitEvent = Event()
        
        
    def initInterface(self):
        '''
        Initalize the interface module
        '''
        try:
            self.interface = AutoFillInterface(eventLog=self.EventLog,hostname=self.hostname)
            self.interface.initController()
        except:
            msg = 'Interface failed to initalize'
            print msg
            raise
        
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
        else:
            detector = 'Detector %s'%sptext[0]
        try:
            option = self.shortHand[sptext[1]] #use the shorthand dict to get the correct option to set
        except KeyError:
            msg = '%s not a valid option for %s'%(sptext[1],detector)
            print msg
            return False
        if option == 'Fill Schedule':
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
                print errorString
                return False
            value = sptext[2]   
        elif option == 'Fill Enabled' or option == 'Temperature Logging': 
            if sptext[2] == 'False': #bool() conversion does not work for strings, do the test long hand 
                value = 'False'
            elif sptext[2] == 'True':
                value = 'True'
            else:
                msg = '"%s" not a valid setting for %s'%(sptext[2],option)
                print msg
                return False
        elif option == 'Name': #the values for names may have spaces in them so join them together
            values = sptext[2:] #get all the values
            value = ' '.join(values)
        else:
            try:
                value = self.cleanDict[option](sptext[2]) #use the clean dict to confirm the correct type of input for the option
            except:
                errorString = '"%s" not a valid value for %s setting %s'%(sptext[2],detector,option)
                print errorString
                return False
        self.interface.changeDetectorSetting(detector,option,value)
        self.EventLog.info('Setting change entered: Detector %s, option %s, value %s'%(detector,option,value))
        
    def checkDetectorChanges(self):
        '''
        Show the user what changes they have entered
        '''
        detectors,settings,values,returnString = self.interface.collectDetectorSettings()
        print returnString
        settingsDict,enabledDetectors = self.interface.constructSettingsDict(detectors, settings, values)
        errorString = self.interface.checkFillScheduleConflicts(settingsDict,enabledDetectors)
        if errorString:
            print errorString
            print 'The settings have not be written due to the above error'
            print 'Please amend the fill schedule to fix the conflicts'
            error = True
        else:
            error = False
        return detectors,settings,values,error
    
    def writeDetectorChanges(self,detectors,settings,values):
        '''
        After the user has confirmed the settings are correct write them to the config file
        '''
        
        self.interface.writeDetectorSettings(detectors,settings,values)
        
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
            print self.interface.readDetectorConfig(name)
        
    
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
#         for (detector,value) in zip(detectors,values):
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
            print msg
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
        :text: - not used, needed to make it these input functions common
        '''
        print 'HELP!'
        
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
        print 'Auto Fill program has been started, enter "start" to start auto fill operation.'
        while True:
            if self.exitEvent.is_set() == True:
                break
            answer = raw_input('>>')
            self.EventLog.debug('Entered command: %s'%answer)
            self.commandInputs(answer)
            if self.exitEvent.is_set() == True:
                break
#             if value == 'exit':
#                 break
#     def startWindow(self):
#         stdscr = curses.initscr()
#         window = stdscr.subwin(23,79,0,0)
#         curses.wrapper(window.addstr('Hello Grill!'))
#         time.sleep(4)
#         curses.endwin()
# #         self.window = curses.newwin(5,20,20,7)
# #         self.window.keypad(1)
# #         self.window.newwin(5,40,20,7)
#     
#     def addText(self):
#         '''
#         Add some text to the window
#         '''
#         self.window.addstr('Hello Grill!')
#         time.sleep(3)
#         
#     def endWindow(self):
#         curses.endwin()
        
        
if __name__ == '__main__':
    AutoFillGUI = AutoFillGUI()
#     AutoFillGUI.startWindow()
#     AutoFillGUI.addText()
#     AutoFillGUI.endWindow()
