'''
Created on Sep 26, 2016

@author: ADonoghue
'''
import threading
from AutoFillLabJack.LJC import LJC
import ConfigParser
from datetime import datetime as dt
from datetime import timedelta as td
import time
from email.mime.text import MIMEText
import smtplib
import time

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
        self.detectorChangesDict = {}
        self.detectorConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\DetectorConfiguration.cfg'
        self.detectorWiringConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\PortWiring.cfg'
        self.detectorSettings = ['Name','Fill Enabled','Fill Schedule','Fill Timeout','Minimum Fill Time','Detector Max Temperature'] #Settings for each
        self.loadConfigEvent = threading.Event()
        self.fillInhibitEvent = threading.Event()
        self.stopRunningEvent = threading.Event()
        self.timeFormat = '%H:%M'
        self.LNTemp = 83.0 #Temperature in kelvin
        self.inihibitFills = False
        self.errorRepeatLimit = 2 #number of times the error needs to show
        self.emailSignature = '\nCheers,\nRoom 134 Auto Fill Sytem'
        self.valuesDictLock = threading.Lock()
        self.configDictLock = threading.Lock()
        #detector
#         self.detectorValues = ['Detector Temp','Valve Temp','Valve State']
       
    def initController(self): 
        '''
        initilize the lab jack
        '''
        try:
            cnfgFile = ConfigParser.RawConfigParser()
            cnfgFile.read(self.detectorWiringConfigFile)
            self.LJ = LJC(cnfgFile)
            self.LJ.controllerInit()
        except:
            print 'Interface did not Initalize'
            raise 
        self.loadDetectorConfig()
    
    def initRelease(self):
        '''
        Clean enerything up before closing
        turn off all the leds and valves
        '''  
        states = [False] * len(self.detectors)
        self.writeValveState(self.detectors,states)
        self.writeEnableLEDState(self.detectors, states)
        self.writeEnableLEDState(['Line Chill'], [False])
        self.writeValveState(['Line Chill'], [False])
        self.LJ.writeErrorState(False)
        self.LJ.writeInhibitState(False)
        self.LJ.releaseInit()
        del self.LJ
        
    def readDetectorTemps(self):
        '''
        :detectors: list of detector names(string) to read temperature
        '''
        with self.valuesDictLock:
            temperatures = self.LJ.readDetectorTemps(self.detectors)
            for (temp,detector) in zip(temperatures,self.detectors):
                self.detectorValuesDict[detector]['Detector Temperature'] = temp
#             self.valuesDictLock.notify() #notify the any threads that are waiting for the 
            
    def getDetectorTemps(self,detectors):
        '''
        :detectors: list of detector names(string) to read temperature
        '''
        self.valuesDictLock.acquire()
        temps = []
        for detector in detectors:
            temps.append(self.detectorValuesDict[detector]['Detector Temperature'])
        self.valuesDictLock.release()
        self.configDictLock.acquire()
        names = []
        for detector in detectors:
            names.append(self.detectorConfigDict[detector]['Name'])
        self.configDictLock.release()
        return temps,names
    
    def readVentTemps(self):
        '''
        :detectors: list of detector names (strings) to read the valve temperature
        '''
        if self.enabledDetectors: #make sure the list is not empty
            temperatures = self.LJ.readVentTemps(self.enabledDetectors)
            for (temp,detector) in zip(temperatures,self.enabledDetectors):
                self.detectorValuesDict[detector]['Vent Temperature'] = temp
        
    
    def writeValveState(self,detectors,states):
        '''
        set the state of the give detector list to matching state in the state list
        :detectors: list of detector names to set valve state, list of string names
        :valveState: list of states to set the valves to, list of bools
        '''
        self.LJ.writeValveStates(detectors, states)
        
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
        self.lineChillEnabled = False
        self.lineChillTimeout = 0
        for detector in self.detectorConfigDict.keys():
            if 'Detector' in detector: #make sure it is a detector not the line chill
                self.detectors.append(detector)
                self.detectorValuesDict[detector] = {'Detector Temperature':'0:0','Vent Temperature':'0:0','Valve State':False,\
                                                     'Fill Started Time':'0:0'}
                if self.detectorConfigDict[detector]['Fill Enabled'] == 'True':
                    self.enabledDetectors.append(detector)
        self.lineChillEnabled = bool(cnfgFile.get('Line Chill','Enabled'))
        self.lineChillTimeout = float(cnfgFile.get('Line Chill','Chill Timeout'))
        offStates = [False]*len(self.detectors)
        self.writeEnableLEDState(self.detectors, offStates)
        if len(self.enabledDetectors) != 0: #if there are no enabled detectors then do turn any of the leds on
            states = [True]*len(self.enabledDetectors)
            self.writeEnableLEDState(self.enabledDetectors, states)
        self.writeEnableLEDState(['Line Chill'], [self.lineChillEnabled])
        self.loadConfigEvent.clear()
    
    def startRunThread(self):
        '''
        Start the thread that will run
        '''   
        mainThread = threading.Thread(target=self.runThread,name='MainControlThread',args=())
        mainThread.start()
        print 'end of run start'
        
    def runThread(self):
        '''
        Thread run the detector filling
        '''
#         print 'Thread Started'
        while self.stopRunningEvent.isSet() == False:
            # read all the detector temps temperatures
            self.readDetectorTemps()
            # if the check configuration event is set read the configuration list to get a list of enabled detectors and other
            if self.loadConfigEvent.is_set():
                self.loadDetectorConfig()
                
            # check temperatures for any enabled detectors that are above maximun temperature, set error LED and send email is nessassary
            self.checkDetectorTemperatures()
            # check enabled detector's settings and start fills if needed
            self.checkFillInhibit()
            self.checkStartDetectorFills()
            
            if self.inihibitFills == False: #if the inhibit fills is true no new fills will be started so don't do anyother checking
                # check currently filling detectors for min fill time breach
                self.checkMinFillTime()
                # for filling detectrors check for vent temp reaching LN levels
                self.checkVentTemp()
                # check for filling timeout, set error and close valve if nessassary 
                self.checkFillTimeout()
                #check for errors with filling or detector temperature
            errorBody = self.checkDetectorErrors()
            if errorBody != '':
                print errorBody
            curTime = time.time()
            startScan = curTime + 1
            while curTime < startScan: #while the thread sleeps check the fill inhibit
                self.checkFillInhibit()
                curTime = time.time()
#             time.sleep(1)
    #             self.sendEmail(errorBody)
        
        # repeat
        # flash the heatbeat light
            self.LJ.heartbeatFlash()
    #         return True
         
    
    def checkDetectorTemperatures(self):
        '''
        Check the enabled detectors to see if there temperatures exceed the maximum temp limits 
        
        '''  
        for detector in self.enabledDetectors:
            maxTemp = float(self.detectorConfigDict[detector]['Detector Max Temperature'])
            curTemp = float(self.detectorValuesDict[detector]['Detector Temperature'])
            if curTemp > maxTemp:
                name = self.detectorConfigDict[detector]['Name']
                msg = '%s detector temperature has exceeded its max allowed temperature'%(name)
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
            if curTimeStr in schedule:
                if self.detectorValuesDict[detector]['Valve State'] == False: #check to make sure the valve has not already been opened
                    detectorToOpen.append(detector)
                    print 'Opening valve for detector', detector
                    self.detectorValuesDict[detector]['Fill Start'] = curTimeStr
#                     minFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Minimum Fill Time']))
#                     maxFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Fill Timeout']))
                    
                    minFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Minimum Fill Time']))
                    maxFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Fill Timeout']))
                    self.detectorValuesDict[detector]['Minimum Fill Timeout'] = dt.strftime(curTime+minFillDelta,self.timeFormat)
                    #min time the valve can be opened before 
                    self.detectorValuesDict[detector]['Minimum Fill Expired'] = False
                    self.detectorValuesDict[detector]['Maximum Fill Timeout'] = dt.strftime(curTime+maxFillDelta,self.timeFormat)
                    
                    #max fill time
                    
        numValves = len(detectorToOpen)
        if self.inihibitFills == True:
            if numValves != 0:
                msg = 'Fill inhibit prevented the a fill from starting'
                self.errorList.append(msg)                
        else:
            if numValves != 0:
                states = [True] *numValves
                self.writeValveState(detectorToOpen,states)
                for detector in detectorToOpen:
                    self.detectorValuesDict[detector]['Valve State'] = True
        
    def checkMinFillTime(self):
        '''
        Check the minimum fill time for the currently filling detector
        '''
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True: #only check min fill time for detectors that have open valves
                if self.detectorValuesDict[detector]['Minimum Fill Timeout'] == False: # if the min time has experied don't check it again
                    minTimeout = self.detectorValuesDict[detector]['Minimum Fill Timeout']
                    if minTimeout == curTime: # the intervals between check the detector should be less than a minute
                        print 'Min Fill Time has Expired', detector
                        self.detectorValuesDict[detector]['Minimum Fill Expired'] = True
                    
                
    def checkVentTemp(self):
        '''
        Check the vent temperatures on filling detectors and see if it has reached liquid nitrogen temperatures
        '''
        valvesToClose = []
#         detectorValveTemps = self.LJ.readValveTemps(self.enabledDetectors)
        self.readVentTemps()
        for detector in self.enabledDetectors:
            ventTemp = self.detectorValuesDict[detector]['Vent Temperature']
            if self.detectorValuesDict[detector]['Valve State'] == True:
                if self.detectorValuesDict[detector]['Minimum Fill Expired'] == True:
                    if ventTemp <= self.LNTemp:
                        valvesToClose.append(detector)
        numValves = len(valvesToClose)
        if numValves != 0:
            states = [False] * numValves
            print 'Closing valves, vent',valvesToClose
            self.writeValveState(valvesToClose,states)
            for detector in valvesToClose:
                self.detectorValuesDict[detector]['Valve State'] = False
            self.cleanValuesDict(valvesToClose) #clean up the values dict
            
     
    def checkFillTimeout(self):
        '''
        Check to see if any fills have timedout
        '''
        valvesToClose = []
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True:
#                 timeoutTime = curTime + td(minutes=int(self.detetorValuesDict[detector]['Fill Timeout'])
#                 timeoutStr = tim
                if curTime == self.detectorValuesDict[detector]['Maximum Fill Timeout']:
                    valvesToClose.append(detector)
                    msg = '%s fill has timed out'%(self.detectorConfigFile[detector]['Name'])
                    self.errorList.append(msg) 
        numValves = len(valvesToClose)
        if numValves != 0:
            print 'Closing valves, timout',valvesToClose
            states = [False]*numValves
            self.writeValveState(valvesToClose,states)
            for detector in valvesToClose:
                self.detectorValuesDict[detector]['Valve State'] = False
            self.cleanValuesDict(valvesToClose)
            
    def checkDetectorErrors(self):
        '''
        Check the error in the error dict and compose and email body
        '''   
        if self.errorList == []: #if no errors 
            self.errorDict = {}
            self.LJ.writeErrorState(False)
        for error in self.errorList:
            self.LJ.writeErrorState(True)
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
    
    def cleanValuesDict(self,detectors):
        '''
        Reset self.detectorValuesDict after a fill has been completed
        this will reset 'Minimum Fill Timout', 'Minimum Fill Experied', 'Maximum Fill Timout','Fill Started Time'
        :detectors: - list of detectors to clean up
        
        '''
        for detector in detectors:
            self.detectorValuesDict[detector]['Minimum Fill Timeout'] = '0:0'
            self.detectorValuesDict[detector]['Minimum Fill Experied'] = False
            self.detectorValuesDict[detector]['Maximum Fill Timeout'] = '0:0'
            self.detectorValuesDict[detector]['Fill Started Time'] = '0:0'
        
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
        errorBody += tempString
        try:
            server = smtplib.SMTP('localhost') #use the open port to send the message
        except:
#             self.EventLog.exception('Tried to contact mail server and failed')
            return False
        msg = MIMEText(errorBody+self.emailSignature)
        msg['Subject'] = 'Dewar Fill Level'
        msg['From'] = self.senderEmail
        msg['To'] = self.emailRecipents
        if ',' in self.emailRecipents: #if there are multiple reciepents then the email has to be split in to a list
            server.sendmail(self.senderEmail, self.emailRecipents.split(','), msg.as_string()) #note the localhost email must be used
            #to contaact the server. the baseEmail will show up as the from.
        else: #else just send the single recipent as a list
            server.sendmail(self.senderEmail, [self.emailRecipents], msg.as_string())
        server.quit()  
            
            
    def checkFillInhibit(self):
        '''
        Check the fill inhibit input and turn the light on if needed
        '''
        state = not self.LJ.readInhibitState() #the switch is normally closed
        self.LJ.writeInhibitState(state) #write the current state of the inhibit switch to the 
        if state == True:
            self.inihibitFills = state
            numDetectors = len(self.enabledDetectors)
            if numDetectors !=0:
                states = [False]*numDetectors
                self.LJ.writeValveStates(self.enabledDetectors, states) #close all the valves but keep the enabled lights on
            self.fillInhibitEvent.set()
        else:
#             if self.fillInhibitEvent.isSet() == True:
            self.fillInhibitEvent.clear()
#             self.LJ.writeInhibitState(state)
        
        
    def readDetectorConfig(self,detector):
        '''
        Read the detector configuration from the config dict and return a string of the stuff
        :detector: -name of detector to read
        '''
        returnString = ''
        for setting in self.detectorSettings:
            returnString += setting + ' | ' + self.detectorConfigDict[detector][setting] + '\n'
        
        return returnString
    
    def changeDetectorSetting(self,detector,setting,value):
        '''
        Collect the settings that will be made to the detector settings. This will not write to the config file or change any settings
        '''  
        try:
            self.detectorChangesDict[detector]['Settings'].append(setting)
            self.detectorChangesDict[detector]['Values'].append(value)
        except KeyError:
            self.detectorChangesDict[detector] = {}
            self.detectorChangesDict[detector]['Settings'] = [setting]
            self.detectorChangesDict[detector]['Values'] = [value]
            
    def collectDetectorSettings(self):
        '''
        Collect the changes that will be made by the user and report, the user will reply with yes or no then _writecfg is called to write
        the file
#         :detector: - string name of detector to be adjusted should be "Detector <#>"
#         :setting: - Setting to change, ie enabled, min fill timeout
#         :value: - value the setting will be changed to
        '''   
        detectors = []
        settings = []
        values = []
        returnString = ''
        for detector in self.detectorChangesDict.iterkeys():
            detectorDict = self.detectorChangesDict[detector]
            for (setting,value) in zip(detectorDict["Settings"],detectorDict['Values']):
                detectors.append(detector)
                settings.append(setting)
                values.append(value)
                returnString += '%s %s will be set to %s \n'%(detector,setting,value)
        return detectors,settings,values,returnString
        
    def writeDetectorSettings(self,sections,options,values): 
        '''
        load and write the config file using the inputs
        :sections: - list section names that will be written to, will be detector names
        :options: - list option within the section to write value to, ie name, fill timeout, fill schedule
        :values: - list of values to that will be corresponding option will be set to
        '''
        cnfgFile = ConfigParser.RawConfigParser()
        cnfgFile.read(self.detectorConfigFile)
        for (section,option,value) in zip(sections,options,values):
            cnfgFile.set(section, option, value)
        with open(self.detectorConfigFile, 'w') as FILE:
            cnfgFile.write(FILE)
        
        