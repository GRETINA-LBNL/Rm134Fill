'''
Created on Sep 26, 2016

@author: ADonoghue
'''
import threading
from AutoFillLabJack.LJC import LJC
import ConfigParser
from datetime import datetime as dt
from datetime import timedelta as td

class AutoFillInterface():
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.errorDict = {} #storage dict for errors that occur every time the LJ is polled
        self.errorList = [] #storage of error string recored for each LJ poll
        self.detectorConfigDict = {} #locations for setting for the detector
        self.detectorValuesDict = {} #storage for the detectors current settings
        self.detectorConfigFile = 'C:\Python\Misc\AutoFillLabJack\DetectorConfiguration.cfg'
        self.detectorSettings = ['Name','Fill Enabled','Fill Schedule','Fill Timout','Minimum Fill Time','Detector Max Temperature'] #Settings for each
        self.loadConfigEvent = threading.Event()
        self.timeFormat = '%H:%M'
        self.LNTemp = 77 #Temperature in kelvin
        self.inihibitFills = False
        self.errorRepeatLimit = 2 #number of times the error needs to show
        #detector
#         self.detectorValues = ['Detector Temp','Valve Temp','Valve State']
       
    def initController(self): 
        '''
        initilize the lab jack
        '''
        try:
            self.LJ = LJC()
            self.LJ.controllerInit()
        except:
            print 'Lab Jack failed to Initilize'
            return False
    
    def initRelease(self):
        '''
        Clean enerything up before closing
        turn off all the leds and valves
        '''  
        states = [False] * self.detectors
        self.LJ.writeDetectorStates(self.detectors,states)
        self.LJ.writeEnableLEDState(self.detectors, states)
        self.LJ.writeErrorState(False)
        self.LJ.writeInhibitState(False)
        self.LJ.releaseInit()
        
    def readDetectorTemps(self,detectors):
        '''
        :detectors: list of detector names(string) to read temperature
        '''
        temperatures = self.LJ.readDetectorTemps(detectors)
        return temperatures
    
    def readValveTemps(self,detectors):
        '''
        :detectors: list of detector names (strings) to read the valve temperature
        '''
        temperatures = self.LJ.readValveTemps(detectors)
        return temperatures
    
    def writeValveState(self,detectors,states):
        '''
        set the state of the give detector list to matching state in the state list
        :detectors: list of detector names to set valve state, list of string names
        :valveState: list of states to set the valves to, list of bools
        '''
        self.LJ.writeValveState(detectors, states)
        
    def writeEnableLEDState(self,detectors,states):
        '''
        :detectors: list of detector names to write, list of strings
        :states: list of states for the detectors, list of bools
        '''
        self.LJ.writeEnableLEDState(detectors, states)
        
    def loadDetectorConfig(self):
        '''
        Load the data from the configuration file for each detector
        '''
        cnfgFile = ConfigParser.RawConfigParser()
        cnfgFile.read(self.detectorConfigFile)
        detectors = cnfgFile.get('Detectors','Names').split(',')
        for detector in detectors:
            config = {}
            for setting in self.detectorSettings:
                config[setting] = cnfgFile.get(detector, setting)
            self.detectorConfigDict[detector] = config
        self.enabledDetectors = []
        self.detectors = []
        for detector in self.detectorConfigDict.keys():
            if 'Detector' in detector: #make sure it is a detector not the line chill
                self.detectors.append(detector)
                self.detectorValuesDict[detector] = {'Detector Temp':0.0,'Valve Temp':0.0,'Valve State':False,'Fill Started Time':0.0}
                if self.detectorConfigDict[detector]['Fill Enabled'] == 'True':
                    self.enabledDetectors.append(detector)
        
    def runThread(self):
        '''
        Thread run the detector filling
        '''
        # read all the detector temps temperatures
        detTemps = self.LJ.readDetectorTemps(self.detectors)
        for (temp,detector) in zip(detTemps,self.detectors):
            self.detectorValuesDict[detector]['Detector Temperature'] = temp
        # if the check configuration event is set read the configuration list to get a list of enabled detectors and other
        if self.loadConfigEvent.is_set():
            self.loadDetectorConfig()
        # check temperatures for any enabled detectors that are above maximun temperature, set error LED and send email is nessassary
        self.checkDetectorTemperatures()
        # check enabled detector's settings and start fills if needed
        self.checkStartDetectorFills()
        
        if self.inihibitFills != True: #if the inhibit fills is true no new fills will be started so don't do anyother checking
            # check currently filling detectors for min fill time breach
            self.checkMinFillTime()
            # for filling detectrors check for vent temp reaching LN levels
            self.checkVentTemp()
            # check for filling timeout, set error and close valve if nessassary 
            self.checkFillTimeout()
            #check for errors with filling or detector temperature
        self.checkDetectorErrors() 
        # repeat
        # flash the heatbeat light
        self.LJ.heartbeatFlash()
        
        
        

        
    
    def checkDetectorTemperatures(self):
        '''
        Check the enabled detectors to see if there temperatures exceed the maximum temp limits 
        
        '''  
        for detector in self.enabledDetectors:
            maxTemp = float(self.detectorConfigDict[detector]['Detector Maximum Temperature'])
            curTemp = float(self.detectorValuesDict[detector]['Detector Temperature'])
            if curTemp > maxTemp:
                name = self.detectorConfigDict[detector]['Name']
                msg = '% detector temperature has exceeded its max allowed temperature'(name)
                
                self.errorList.append(msg)
               
        
    def checkStartDetectorFills(self):
        '''
        Check the schedule for each detector and start a fill if needed
        '''    
        detectorToOpen = []
        curTime = dt.today()
        curTimeStr = curTime.strftime(self.timeFormat) #get the current time as a sting with format Hour:Min
        for detector in self.enabledDetectors:
            schedule = self.detectorConfigDict[detector]['Fill Schedule']
            if curTime in schedule:
                if self.detectorValuesDict[detector]['Valve State'] == False: #check to make sure the valve has not already been opened
                    detectorToOpen.append(detector)
                    self.detectorValuesDict[detector]['Fill Start'] = curTimeStr
                    minFillDelta = td(self.detectorConfigDict[detector]['Minimum Fill Time'],'%M')
                    maxFillDelta = td(self.detectorConfigDict[detector]['Fill Timeout'],'%M')
                    self.detectorValuesDict[detector]['Min Fill Timeout'] = dt.strftime(curTime+minFillDelta,self.timeFormat)
                    #min time the valve can be opened before 
                    self.detectorValuesDict[detector]['Min Fill Expired'] = False
                    self.detectorValuesDict[detector]['Max Fill Timeout'] = dt.strftime(curTime+maxFillDelta,self.timeFormat)
                    #max fill time
                    
        numValves = len(detectorToOpen)
        if self.inihibitFills == True:
            if numValves != 0:
                msg = 'Fill inhibit prevented the a fill from starting'
                self.errorList.append(msg)                
        else:
            if numValves != 0:
                states = [True] *numValves
                self.LJ.writeHeartbeatStates(detectorToOpen,states)
        
    def checkMinFillTime(self):
        '''
        Check the minimum fill time for the currently filling detector
        '''
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True:
                minTimeout = self.detectorValuesDict[detector]['Min Fill Timout']
                if minTimeout == curTime: # the intervals between check the detector should be less than a minute
                    self.detectorValuesDict[detector]['Min Fill Expired'] = True
                    
                
    def checkVentTemp(self):
        '''
        Check the vent temperatures on filling detectors and see if it has reached liquid nitrogen temperatures
        '''
        valvesToClose = []
        detectorValveTemps = self.LJ.readValveTemps(self.enabledDetectors)
        for (detector,valveTemp) in zip(self.enabledDetectors,detectorValveTemps):
                if self.detectorValuesDict[detector]['Valve State'] == True:
                    if self.detectorValuesDict[detector]['Min Fill Expired'] == True:
                        if valveTemp <= self.LNTemp:
                            valvesToClose.append(detector)
        numValves = len(valvesToClose)
        if numValves != 0:
            states = [False] * numValves
            self.LJ.writeValveStates(valvesToClose,states)
            
            
     
    def checkFillTimout(self):
        '''
        Check to see if any fills have timedout
        '''
        valvesToClose = []
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True:
                if curTime == self.detectorValuesDict[detector]['Max Fill Timeout']:
                    valvesToClose.append(detector)
                    msg = '%s fill has timed out'%(self.detectorConfigFile[detector]['Name'])
                    self.errorList.append(msg) 
        numValves = len(valvesToClose)
        if numValves != 0:
            states = [False]*numValves
            self.LJ.writeValveStates(valvesToClose,states)
        
    def checkDetectorErrors(self):
        '''
        Check the error in the error dict and compose and email body
        '''   
        if self.errorDict == []: #if no errors 
            self.errorDict = {}
        for error in self.errorList:
            try:
                self.errorDict[error] += 1
            except KeyError:
                self.errorDict[error] = 1
        
        emailBody = ''
        for (error, numRepeat) in self.errorDict.iteritems():
            if numRepeat >= self.errorRepeatLimit:
                emailBody += ',%s'%error
            else:
                continue
        return emailBody
    
    def sendEmail(self,emailBody):
        '''
        send the email of the errors
        :emailBody: - string of the errors, they are seperated by ','
        '''
        if emailBody == '':
            return
        else:
            if len(emailBody)>1:
                errorBody = '\n'.join(emailBody.split(','))
            else:
                errorBody = emailBody+'\n'
        tempString = ''
        for detector in self.detectors: #make a string of the last read detector temperatures
            temp = self.detectorValuesDict[detector]['Detector Temperature']
            detStr = '%s current temperature %s\n'%(self.detectorConfigDict['Name'],temp)
            tempString+=detStr
        emailBody += tempString
            
            
    def checkFillInhibit(self):
        '''
        Check the fill inhibit input and turn the light on if needed
        '''
        state = self.LJ.readInhibitState()
        self.LJ.writeInhibitState() #write the current state of the inhibit switch to the 
        self.inihibitFills = state
        numDetectors = len(self.enabledDetectors)
        states = [False]*numDetectors
        self.LJ.writeValveStates(self.enabledDetectors, states) #close all the valves but keep the enabled lights on
        