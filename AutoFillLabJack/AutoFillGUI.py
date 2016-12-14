'''
Created on Sep 16, 2016

@author: ADonoghue
'''
# import curses
# import time
from datetime import datetime as dt
from AutoFillLabJack.AutoFillInterface import AutoFillInterface
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
                          'temp':'Detector Max Temperature'}
        
        self.timeFormat = '%H:%M'
        
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
        
    def detectorSettingsInput(self,text):
        '''
        Take the input and confirm it is the correct type
        :text: - input from the user that is changing, should be '1 Enabled True' => Detector 1 Fill Enabled True
        
        '''
        sptext = text.split(' ')
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
                    return False
            value = sptext[2]   
        elif option == 'Fill Enabled': 
            if sptext[2] == 'False': #bool() conversion does not work for strings, do the test long hand 
                value = 'False'
            elif sptext[2] == 'True':
                value = 'True'
            else:
                msg = '%s not a valid setting for Fill Enabled'%sptext[2]
            
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
        
    def checkDetectorSettings(self,number):
        '''
        Check the detector settings for the 
        '''   
        detector = 'Detector %s'%number
        print self.interface.readDetectorConfig(detector)
    
    def printHelp(self):
        '''
        Print the help file to screen
        '''
    
    def detectorTempInput(self,number):
        '''
        Display the current temperature for the detector number
        '''   
        if number == 'all' or number == 'All':
            detectors = []
            for num in range(1,7): #1-6
                detectors.append('Detector %d'%num)
        else:
            detectors = ['Detector %s'%number]
        temps,names = self.interface.getDetectorTemps(detectors)
        displayString = ''
        for (detector,name,temp) in zip(detectors,names,temps):
            displayString += '%s (%s) temperature %sK\n'%(detector,name,temp)
        print displayString
            
        
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