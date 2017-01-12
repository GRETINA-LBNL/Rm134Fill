'''
Created on Sep 16, 2016

@author: ADonoghue
'''
# import curses
# import time
from datetime import datetime as dt
from AutoFillLabJack.AutoFillInterface import AutoFillInterface
from threading import Event
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
                          'temp':'Detector Max Temperature','name':'Name'}
        
        self.timeFormat = '%H:%M'
        self.inputSelectDict = {'set':self.detectorSettingsInput,'get':self.checkDetectorSettingsInput,'temp':self.detectorTempInput,\
                                'error':self.errorInput,'start':self.startInput,'stop':self.stopInput,'exit':self.exitInput,\
                                'write':self.writeSettingsInput,'help':self.helpInput}
        
        self.exitEvent = Event()
    def initInterface(self):
        '''
        Initalize the interface module
        '''
        try:
            self.interface = AutoFillInterface()
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
                times = sptext[2].split(',')      
            else:
                times = [sptext[2]]
            for time in times: #check that the times are valid 24H times
                try:
                    dt.strptime(time,self.timeFormat)
                except ValueError:
                    errorString = '%s not a valid fill time in fill schedule %s'%(time,sptext[2])
                    raise
            value = sptext[2]   
        elif option == 'Fill Enabled': 
            if sptext[2] == 'False': #bool() conversion does not work for strings, do the test long hand 
                value = 'False'
            elif sptext[2] == 'True':
                value = 'True'
            else:
                msg = '%s not a valid setting for Fill Enabled'%sptext[2]
            
        elif option == 'Name': #the values for names may have spaces in them so join them together
            values = sptext[2:] #get all the values
            value = ' '.join(values)
        else:
            try:
                value = self.cleanDict[option](sptext[2]) #use the clean dict to confirm the correct type of input for the option
            except:
                errorString = '%s not a valid value for %s setting %s'%(sptext[2],detector,option)
                print errorString
                return False
        self.interface.changeDetectorSetting(detector,option,value)
        
    def checkDetectorChanges(self):
        '''
        Show the user what changes they have entered
        '''
        detectors,settings,values,returnString = self.interface.collectDetectorSettings()
        print returnString
        return detectors,settings,values
    
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
            displayString += '%s (%s) temperature %sK\n'%(detector,name,temp)
        print displayString
    
    def writeSettingsInput(self,text):
        '''
        Write the settings that the user entered using the detectorSettingsInput method
        '''
        detectors,settings,values = self.checkDetectorChanges()
#         print 'Detectors',detectors
#         print 'Settings', settings
#         print 'Values', values
        answer = raw_input('Write the settings show above?')
        if answer.upper() == 'Y':
            self.writeDetectorChanges(detectors,settings,values)
        else:
            print "Fine I won't\n"
    
    def errorInput(self,text):
        '''
        Check the interface for any errors
        :text: - to dispaly error this is empty, to clear errors this will be 'clear'
        '''
        if text == 'clear':
            self.interface.cleanErrorDict()
        else:
            errorString = self.interface.readDetectorErrors()
            print errorString
        
        
    def commandInputs(self,text):
        '''
        Select the input function baised on the first word in the command
        :text: - input text from user
        '''
        sText = text.split(' ')
        command = sText.pop(0) # remove the first text entered, it is the command and the rest of the methods will not be use
        try:
            inputFunction = self.inputSelectDict[command]
        except KeyError:
            msg = "%s not a valid command\n enter 'help' to print help file" %(command)
            print msg
            return
        commandOptions = ' '.join(sText)
        inputFunction(commandOptions)
        return True
    
    def startInput(self,text):
        '''
        start the running thread
        '''   
        self.interface.startRunThread()
        
    def stopInput(self,text):
        '''
        stop the running thread
        '''
        self.interface.stopRunThread()
    
    def exitInput(self,text):
        '''
        Stop the running thread then close everything
        '''
        self.interface.initRelease()
        del self.interface
        self.exitEvent.set()
        
    def helpInput(self,text):
        '''
        Print the help file to screen
        :text: - not used, needed to make it common
        '''
        print 'HELP!'
        
    
    def mainInput(self):
        '''
        Main input for the user, feeds input to commandInputs() for completing tasks
        '''  
        print 'Auto Fill program has been started, enter "start" to start auto fill operation.'
        while True:
            if self.exitEvent.is_set() == True:
                break
            answer = raw_input('>>')
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
    AutoFillGUI.startWindow()
#     AutoFillGUI.addText()
#     AutoFillGUI.endWindow()