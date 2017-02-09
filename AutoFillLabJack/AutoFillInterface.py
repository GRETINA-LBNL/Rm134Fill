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
import copy
import logging
import sys
import matplotlib.pyplot as plt

# from __builtin__ import file
# import socket
class AutoFillInterface():
    '''
    classdocs
    '''


    def __init__(self,eventLog,hostname):
        '''
        Constructor
        '''
        self.errorDict = {} #storage dict for errors that occur every time the LJ is polled
        self.errorList = [] #storage of error string recored for each LJ poll
        self.detectorConfigDict = {} #locations for setting for the detector
        self.detectorValuesDict = {} #storage for the detectors current settings
        self.detectorChangesDict = {}
        self.tempLoggingDict = {}
        self.EventLog = eventLog
#         hostname = socket.gethostname()
        if hostname == 'MMStrohmeier-S67':
            self.detectorConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\DetectorConfiguration.cfg'
            self.detectorWiringConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\PortWiring.cfg'
            self.logDir = "C:\Python\Rm134Fill\AutoFillLabJack\Logs"
#             self.loggingConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\winLogging.cfg'
        elif hostname == 'localhost':
            self.detectorConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/DetectorConfiguration.cfg'
            self.detectorWiringConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/PortWiring.cfg'
            self.logDir = '/home/gretina/Rm134Fill/Logs'
#             self.loggingConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/logging.cfg'
        #Settings for each
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
            self.EventLog.error(sys.exc_info()[0]) #log the error from the labjack
#             print 'Interface did not Initalize'
            raise 
        self.loadDetectorConfig() 
        self.getTemperatureLogs()
    
    def initRelease(self):
        '''
        Clean enerything up before closing
        turn off all the leds and valves
        '''  
        self.stopRunThread()
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
 
    def logDetectorTemps(self):
        '''
        Log the temperature in the approiate log, only detectors that logging has been enabled.
        This will log every time the rurThread cycles
        '''
#         print self.loggingDetectors
        with self.valuesDictLock:
            for detector in self.loggingDetectors:
                    temp = self.detectorValuesDict[detector]['Detector Temperature']
                    self.tempLoggingDict[detector].info('%.3f K'%temp)
                    
    def getTemperatureLogs(self):
        '''
        get the temperature logs have have been started
        grap the event log as well
        '''
#         logging.config.fileConfig(fname=self.loggingConfigFile)
#         self.EventLog = logging.getLogger('EventLog')
        for detector in self.detectors:
            name = detector.replace(' ','') + 'Log'
            self.tempLoggingDict[detector] = logging.getLogger(name)
        
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
        self.EventLog.info('Load Detector Configuration from %s'%self.detectorConfigFile)
        cnfgFile = ConfigParser.RawConfigParser()
        cnfgFile.read(self.detectorConfigFile)
        detectors = cnfgFile.get('Detectors','Names').split(',')
        self.detectorSettings = cnfgFile.get('Detectors','Settings').split(',')
        for detector in detectors:
            config = {}
            for setting in self.detectorSettings:
                config[setting] = cnfgFile.get(detector, setting)
            self.detectorConfigDict[detector] = config
        self.enabledDetectors = []
        self.loggingDetectors = []
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
                if self.detectorConfigDict[detector]['Temperature Logging'] == 'True':
                    self.loggingDetectors.append(detector)
        lineChillEnabled = cnfgFile.get('Line Chill','Fill Enabled')
        if lineChillEnabled == 'True' or lineChillEnabled == 'False':
            self.lineChillEnabled = lineChillEnabled
        self.lineChillTimeout = float(cnfgFile.get('Line Chill','Fill Timeout'))
       
    def applyDetectorConfig(self):
        '''
        Apply the configuration loaded by self.loadDetectorConfig
        '''
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
        errorStr = self.checkFillScheduleConflicts(self.detectorConfigDict, self.enabledDetectors)
        if errorStr != '':
            return errorStr
        else:
            mainThread = threading.Thread(target=self.runThread,name='MainControlThread',args=())
            mainThread.start()
            return ''
#         print 'end of run start'
    
    def stopRunThread(self):
        '''
        Stop the MainControlThread 
        This will do the same thing as initRelease
        '''   
        self.stopRunningEvent.set()
        threads = threading.enumerate()
        for thread in threads: #join the thread
            if thread.name == 'MainControlThread':
                thread.join()
                
        states = [False] * len(self.detectors)
        self.writeValveState(self.detectors,states)
        self.writeEnableLEDState(self.detectors, states)
        self.writeEnableLEDState(['Line Chill'], [False])
        self.writeValveState(['Line Chill'], [False])
        self.LJ.writeErrorState(False)
        self.LJ.writeInhibitState(False)
        self.stopRunningEvent.clear()
        
    def runThread(self):
        '''
        Thread run the detector filling
        '''
#         print 'Thread Started'
#         threadRepeat = 1\
        
        error = self.LJ.checkRelayPower()
        if error:
            self.errorList.append(error)
            self.stopRunningEvent.set() #don't let the run start, the relays will not work.
            self.checkDetectorErrors() #Make sure the error light turns on
        else:
            self.stopRunningEvent.clear()
            self.applyDetectorConfig()
        while self.stopRunningEvent.isSet() == False:
            # read all the detector temps temperatures
            self.readDetectorTemps()
            self.logDetectorTemps() #log the temps that are enabled.
            # if the check configuration event is set read the configuration list to get a list of enabled detectors and other
                
            # check temperatures for any enabled detectors that are above maximun temperature, set error LED and send email is nessassary
            self.errorList = [] #clean the error list for at the beginning of each run
            self.checkDetectorTemperatures()
            # check enabled detector's settings and start fills if needed
            self.checkFillInhibit()
            self.checkStartDetectorFills()
#             print 'Detector 1 valve state',self.detectorValuesDict['Detector 1']['Valve State']
            if self.inihibitFills == False: #if the inhibit fills is true no new fills will be started so don't do anyother checking
                # check currently filling detectors for min fill time breach
                self.checkMinFillTime()
                # for filling detectrors check for vent temp reaching LN levels
                self.checkVentTemp()
                # check for filling timeout, set error and close valve if nessassary 
                self.checkFillTimeout()
                #check for errors with filling or detector temperature
            errorBody = self.checkDetectorErrors() #get the email body and possibly send an email
#             if errorBody != '':
#                 print errorBody
            curTime = time.time()
            startScan = curTime + 1
#             print 'Thread repeats',threadRepeat
#             threadRepeat +=1
            while curTime < startScan: #while the thread sleeps check the fill inhibit, stoprunning, loadconfig
                if self.stopRunningEvent.isSet() == True:
                    break
                if self.loadConfigEvent.is_set(): # check if the config file has been changed and reload it if nessary
                    self.loadDetectorConfig()
                    self.applyDetectorConfig()
                    self.loadConfigEvent.clear()
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
                msg = '%s (%s) temperature has exceeded its max allowed temperature'%(name,detector)
                self.errorList.append(msg)
                self.EventLog.info(msg)
               
        
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
                    detectorToOpen.append(detector) #make the list of valves to open
#                     print 'Opening valve for detector', detector
#                     self.detectorValuesDict[detector]['Fill Start'] = curTimeStr
# #                     minFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Minimum Fill Time']))
# #                     maxFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Fill Timeout']))
#                     
#                     minFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Minimum Fill Time']))
#                     maxFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Fill Timeout']))
#                     self.detectorValuesDict[detector]['Minimum Fill Timeout'] = dt.strftime(curTime+minFillDelta,self.timeFormat)
#                     #min time the valve can be opened before 
#                     self.detectorValuesDict[detector]['Minimum Fill Expired'] = False
#                     self.detectorValuesDict[detector]['Maximum Fill Timeout'] = dt.strftime(curTime+maxFillDelta,self.timeFormat)
                    
                    #max fill time
                    
        numValves = len(detectorToOpen)
        if self.inihibitFills == True:
            if numValves != 0:
                msg = 'Fill inhibit prevented %s from starting a fill'%repr(detectorToOpen)
                self.errorList.append(msg)                
                self.EventLog.info(msg)
        else: #if the fills are not inhibited start the filling process
            if numValves != 0:
                states = [True] *numValves
                self.writeValveState(detectorToOpen,states)
                for detector in detectorToOpen:
                    self.detectorValuesDict[detector]['Valve State'] = True
                    print 'Opening valve for detector', detector
                    self.detectorValuesDict[detector]['Fill Start'] = curTimeStr
                    minFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Minimum Fill Time']))
                    maxFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Fill Timeout']))
                    self.detectorValuesDict[detector]['Minimum Fill Timeout'] = dt.strftime(curTime+minFillDelta,self.timeFormat)
                    #min time the valve can be opened before 
                    self.detectorValuesDict[detector]['Minimum Fill Expired'] = False
                    self.detectorValuesDict[detector]['Maximum Fill Timeout'] = dt.strftime(curTime+maxFillDelta,self.timeFormat)
                    self.EventLog.info('Opening fill valve for %s'%detector)
        
    def checkMinFillTime(self):
        '''
        Check the minimum fill time for the currently filling detector
        '''
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True: #only check min fill time for detectors that have open valves
                if self.detectorValuesDict[detector]['Minimum Fill Expired'] == False: # if the min time has experied don't check it again
                    minTimeout = self.detectorValuesDict[detector]['Minimum Fill Timeout']
#                     print 'Minimum timeout for %s %s'%(detector,minTimeout)
                    if minTimeout == curTime: # the intervals between check the detector should be less than a minute
                        print 'Min Fill Time has Expired', detector
                        self.detectorValuesDict[detector]['Minimum Fill Expired'] = True
                        self.EventLog.debug('Miminum Fill Time Experied for %s'%detector)
                    
                
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
                self.EventLog.info('Closing %s fill valve, LN2 temperature reached'%detector)
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
                    msg = '%s fill has timed out'%(self.detectorConfigDict[detector]['Name'])
                    self.errorList.append(msg) 
        numValves = len(valvesToClose)
        if numValves != 0:
            print 'Closing valves, timeout',valvesToClose
            states = [False]*numValves
            self.writeValveState(valvesToClose,states)
            for detector in valvesToClose:
                self.detectorValuesDict[detector]['Valve State'] = False
                name = self.detectorConfigDict[detector]['Name']
                msg = '%s (%s) fill experied'%(detector,name)
                self.errorList.append(msg)
                self.EventLog.info('Closing %s fill valve, fill timeout reached'%detector)
            self.cleanValuesDict(valvesToClose)
            
    def checkDetectorErrors(self):
        '''
        Check the error in the error dict and compose and email body
        '''   
        if self.errorList == []: #if no errors 
            return
#             self.errorDict = {}
#             self.LJ.writeErrorState(False)
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
    
    def readDetectorErrors(self):
        '''
        Print the contents of the error dict to the screen
        '''
        errorString = ''
        if self.errorDict == {}:
            errorString +='No errors have been reported\n'
        else:
            for (error,numRepeat) in self.errorDict.iteritems():
                msg = '%s has been reported %d times\n'%(error,numRepeat)
                errorString += msg
                self.EventLog.info(msg)
        return errorString
    
    def cleanValuesDict(self,detectors):
        '''
        Reset self.detectorValuesDict after a fill has been completed
        this will reset 'Minimum Fill Timout', 'Minimum Fill Experied', 'Maximum Fill Timout','Fill Started Time'
        :detectors: - list of detectors to clean up
        
        '''
        for detector in detectors:
            if 'Line Chill' == detector:
                continue
            else:
                self.detectorValuesDict[detector]['Minimum Fill Timeout'] = '0:0'
                self.detectorValuesDict[detector]['Minimum Fill Experied'] = False
                self.detectorValuesDict[detector]['Maximum Fill Timeout'] = '0:0'
                self.detectorValuesDict[detector]['Fill Started Time'] = '0:0'
            
    def cleanErrorDict(self):
        '''
        Clean the error dict, only user input will run this method
        '''    
        self.errorDict = {}
        self.LJ.writeErrorState(False)
        return True
    
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
                returnString += '%s %s will be set to: %s \n'%(detector,setting,value)
        self.detectorChangesDict = {} #clean the dict so the settings will not be repeated
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
        self.loadConfigEvent.set() #set the event that will cause the 
        self.cleanValuesDict(sections)
        self.loadDetectorConfig()
        
    def constructSettingsDict(self,sections,options,values):
        '''
        Make the dict of detector settings that will be used to check the fill conflicts and possibly other stuff
        :sections: - list of sections of to be changed, detector names
        :options: - list of options within the section to change, name, fill schedule, etc
        :values: - list of values for the options
        '''
        #make a copy of config dict, so it will not be effected when the new dict is constructed
        settingsDict = copy.deepcopy(self.detectorConfigDict) 
        for (detector,option,value) in zip(sections,options,values):
            settingsDict[detector][option] = value #set the new values for the detectors
        enabledDetectors = []
        for detector in self.detectors:
            if settingsDict[detector]['Fill Enabled'] == 'True':
                enabledDetectors.append(detector)
            else:
                continue
        return settingsDict,enabledDetectors
    
    def checkFillScheduleConflicts(self,settingsDict,enabledDetectors):
        '''
        Check the fill schedule for conflicts between other detector fill schedules, only one detector will be allowed to 
        fill at a time. Each detector will have exclusive control over the fill valve starting at the scheduled start time
        and extending to the Fill Timeout. Other detector can not be scheduled for filling during this time. 
        This check is only done for detectors that are enabled or will become enabled.
        '''
        
        
        if len(enabledDetectors) >= 1:
            startTimes = []
            timeOuts = []
            for detector in enabledDetectors:
                times = []
                fillTime = settingsDict[detector]['Fill Schedule'].split(',')
                for time in fillTime:
                    times.append(dt.strptime(time,self.timeFormat))
                startTimes.append(times)
                timeout = self.detectorConfigDict[detector]['Fill Timeout']
                timeOuts.append(td(minutes=int(timeout)))
            errorStr = self._checkFillOverlap(enabledDetectors, startTimes, timeOuts)
            errorStr += self._checkFillConflicts(enabledDetectors, startTimes, timeOuts)
            if errorStr != '':
                return errorStr
            else:
                return ''
#             return startTimes,timeOuts

        else:
            return ''
        
        #make a fill start and end time, check that other fill start times do not fall between start and end time
    
    def _checkFillOverlap(self,detectors,schedules,timeouts):
        '''
        Check the fill schedule for each detector for overlaping fills within each detector. 
        Detector fill time is defied as start time + fill timeout 
        Example of overlaping  schedule -> [[12:10,12:14]] timeout [5]
        :detectors: - list of detectors to check for overlaps
        :schedules: - nested list of schedules for each detector, should be each entry should be a datetime object
        :timeouts: - list of timout values for each detector, items should be timedelta objects
        '''  
        overlapString = ''
        if len(detectors) < 1:
            return overlapString
        for (detector,schedule,timeout) in zip(detectors,schedules,timeouts):
            numFills = len(schedule)
            if numFills <=1:
                continue
            else:
                SCHStrt = schedule[0]
                SCHStop = schedule[0] +timeout
                for i in range(1,numFills):
                    if schedule[i] <= SCHStop and schedule[i] >= SCHStrt:
                        Sch1 = dt.strftime(SCHStrt,self.timeFormat)
                        Sch2 = dt.strftime(schedule[i],self.timeFormat)
                        Tout = str(timeout).split(':')[1]
                        overlapString += '%s has Schedule Overlap: %s and %s with timeout: %s min \n'%(detector,Sch1,Sch2,Tout)
                        
                    else:
                        continue
        return overlapString
        
    def _checkFillConflicts(self,detectors,schedules,timeouts):
        '''
        Check the fill schedule for conflicts between scheduled fills
        Detector fill time is defied as start time + fill timeout
        Example: Detectors -> [Detector 1, Detector 2], schedules -> [[12:13,15:40],[2:22,12:17]], timeouts -> [5,5]
        :detectors: - list of enabled detectors to check for conflicts
        :schedules: - nested list of fill schedules for each detector, items should be datetime objects
        :timeouts: - list of timeout values for the given detector, items should be timedelta objects
        '''
        conflictString = ''
        numDetectors = len(detectors)
        if numDetectors <=1:
            return conflictString
        for i in range(numDetectors): #interate through all the detectors that will be checked
            detector_i = detectors[i] #set the values that will be checked against all the other detectors, 'master' detector
            schedule_i = schedules[i] #all detectors need to be master detectors
            timeout_i = timeouts[i]
            for h in range(numDetectors):#interage thought all the other detectors, excluding 'master' detector
                if h == i:
                    continue
                else:
                    detector_h = detectors[h]#get the detector values that will be checked against, 
                    schedule_h = schedules[h]
#                     timeout_h = timeouts[h]
                    for start_i in schedule_i: #cycle through the fill times from the 'master' detector
                        end_i = start_i + timeout_i #make the filling window
                        for start_h in schedule_h: #cycle through the detector that will be checked
                            if start_h >= start_i and start_h <= end_i: # check if detector fill start time is within the window of the 'master'
                                strTime_i = dt.strftime(start_i,self.timeFormat)
                                strtime_h = dt.strftime(start_h,self.timeFormat)
                                strtimeout_i = str(timeout_i).split(':')[1]
#                                 strtimeout_h = str(timeout_h).split(':')[1]
                                conStr = '%s fill at %s (timeout %s min) conflicts with %s fill at %s \n'%\
                                        (detector_i,strTime_i,strtimeout_i,detector_h,strtime_h)
                                conflictString += conStr
                            else:
                                continue
        return conflictString
                        
        
    def graphDetectorTemp(self,detName):
        '''
        Make a plot of the recorded temperatures for the give detector number
        :detName: - detector number string that the graph will be made,
        '''
        logFile = self.logDir+'%sLog.txt'%detName
        
        with self.valuesDictLock: #get the values dict lock to prevent logDetectorTemp from grabbing the log file
            with open(logFile, 'r') as FILE:
                detectorTemps = FILE.readlines() #read all the
        temps = []
        times = []
        for line in detectorTemps:
            line = line.strip('\r')
            sline = line.split('|')
            times.append(dt.strptime(self.timeFormat,sline[0]))
            temps.append(float(sline[1]))
        normalFig = plt.figure()
        normalFig.set_size_inches(12,8,forward=True)
#         subtitle = 'Beam Cocktail: %s, Data Date %s'%(self.dataDict[filenames[0]]['Cocktail'],self.dataDate)
        normalFig.canvas.set_window_title('Percent Difference from Calibrated Fluence with Offset from %s'%self.date)
        subtitle = 'Temperature Vs Date'
        normalFig.suptitle(subtitle,fontsize=15)
        normalax = normalFig.add_subplot(111)
        normalax.plot(times,temps,marker='_',label='%s Temperature Log'%detName)
        normalax.set_ylabel('Date')
        normalax.set_xlabel('Detector Temperature (C)')
        plt.show(block=True)