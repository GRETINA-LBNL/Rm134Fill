'''
Created on Sep 26, 2016

@author: ADonoghue
'''
import threading
from labjack.ljm import LJMError
from AutoFillLabJack.LJC import LJC
import ConfigParser
from datetime import datetime as dt
from datetime import timedelta as td
import time
from email.mime.text import MIMEText
import smtplib
from subprocess import Popen, PIPE
import copy
import logging
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as pltdates
import numpy as np
import psutil

#import psutil

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
        self.errorEmailDict = {} #storage for the errors that have been emailed
        self.detectorConfigDict = {} #locations for setting for the detector
        self.detectorValuesDict = {} #storage for the detectors current settings
        self.detectorChangesDict = {}       
        self.detectorNamesDict = {} #Dict for connecting detector name and number, used in the GUI
        self.tempLoggingDict = {}
        self.EventLog = eventLog
#         hostname = socket.gethostname()
        if hostname == 'MMStrohmeier-S67':
            self.detectorConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\DetectorConfiguration.cfg'
            self.detectorWiringConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\PortWiring.cfg'
            self.logDir = "C:\Python\Rm134Fill\AutoFillLabJack\Logs\\"#the last \ can not be alone
#             self.loggingConfigFile = 'C:\Python\Rm134Fill\AutoFillLabJack\winLogging.cfg'
        elif hostname == 'localhost':
            self.detectorConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/DetectorConfiguration.cfg'
            self.detectorWiringConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/PortWiring.cfg'
            self.logDir = '/home/gretina/Rm134Fill/Logs/'
#             self.loggingConfigFile = '/home/gretina/Rm134Fill/AutoFillLabJack/logging.cfg'
        #Settings for each
        self.loadConfigEvent = threading.Event()
        self.fillInhibitEvent = threading.Event()
        self.stopRunningEvent = threading.Event()
        self.initReleaseEvent = threading.Event() #Event to stop the socket listening thread and close everything
        self.timeFormat = '%H:%M'
        self.loggingTimeFormat = '%b-%d-%Y %H:%M:%S '
        self.ventCloseThresholdTemp = -230 #Temp of vent at which fill valve will be closed.
        self.inihibitFills = False
        self.errorRepeatLimit = 30 #number of times the error needs to show before it is emaild
        self.errorEmailRepeatLimit = 12 #number of error has crosses errorRepeatLimit before getting emailed again
        self.emailRecipents = 'ADonoghue@lbl.gov'
        self.senderEmail    = 'gretinafilling@gmail.com'
        self.emailSignature = '\nCheers,\nRoom 134 Auto Fill Sytem'
        self.mainThreadName = 'MainControlThread'
        self.valuesDictLock = threading.Lock()
        self.configDictLock = threading.Lock()
#         self.infoGatherLock = threading.Lock()
        self.remoteCmdDict = {'get':self.readDetectorConfig,'temp':self.getDetectorTemps,
                                'error':self.readDetectorErrors}
        self.pollTime = 30 #in seconds
        self.hardDriveUsageLimit = 95.5 #limit for space used on the hard drive, ensuring there is 
            #enough space for the program to work 

        
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
            msg = self.LJ.controllerInit()
        except LJMError as ljmerror:
            self.EventLog.error(sys.exc_info()[0]) #log the error from the labjack
#             print 'Interface did not Initalize'
            raise 
        msgLst = self.loadDetectorConfig() 
        if msg != '':
            msgLst += '\n\t'+msg
        self.getTemperatureLogs()
       
        return msgLst
    
    def initRelease(self):
        '''
        Clean enerything up before closing
        turn off all the leds and valves
        '''  
        try:
            self.stopRunThread(EXIT=True)
            self.initReleaseEvent.set()
            threads = threading.enumerate()
            for thread in threads: #Stop the thread that runs the communication socket
#                print 
                if thread.name == self.mainThreadName:
                    thread.join()
            self.LJ.releaseInitFlash()
            self.LJ.releaseInit()
            msg = "Proper LJ Shutdown Succeeded"
        except:
            msg = "Proper LJ Shutdown Failed, Deleted Instead."
        del self.LJ
        return msg
    
    
    def readDetectorTemps(self):
        '''
        Read all of the detector temperatures 
        '''
        with self.valuesDictLock:
            temperatures = self.LJ.readDetectorTemps(self.detectors)
            for (temp,detector) in zip(temperatures,self.detectors):
                cropTemp = "%.2f"%(float(temp))
                self.detectorValuesDict[detector]['Detector Temperature'] = cropTemp
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
                    self.tempLoggingDict[detector].info('%s C'%temp)
                    
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
        Gather the detector temps using the list of detectors given
        :detectors: list of detector names(string) to read temperature
        '''
        self.valuesDictLock.acquire()
        temps = []
        for detector in detectors:
            temps.append(self.detectorValuesDict[detector]['Detector Temperature'])
        self.valuesDictLock.release()
        #now get the names from the config dict
        self.configDictLock.acquire()
        names = []
        for detector in detectors:
            names.append(self.detectorConfigDict[detector]['Name'])
        self.configDictLock.release()
        return temps,names
    
    def getValveStatus(self):
        '''
        Get the current status of all the valves, return string showing which valves are open
        '''
        self.valuesDictLock.acquire()   
        openValves = []
        for detector in self.detectorValuesDict.iterkeys():
            if self.detectorValuesDict[detector]["Valve State"] == True:
                openValves.append(detector)
        self.valuesDictLock.release()
        if not openValves:
            valveList = 'None'
        else:        
            valveList = ','.join(openValves)
        return "\tFill Valve(s) currently open: "+bcolors.OKGREEN+valveList+bcolors.ENDC
    
    def getNextFillScheduled(self):
        '''
        Get the next detector that will be filled

        '''
        self.configDictLock.acquire()
        curTime = dt.today()
#        curTimeStr = curTime.strftime(self.timeFormat)
        detectorNames = []
        detectorGivenNames= []
        detectorDiffFromNow = []
        detectorFillTime = []
        timeZero = td(hours=0,minutes=0,seconds=0)
        timeZeroToday = dt(hour=0,minute=0,second=0,year=curTime.year,\
                                            month=curTime.month,day=curTime.day)
        for detector in self.enabledDetectors:
            schedule = self.detectorConfigDict[detector]["Fill Schedule"]
            splitSchedule = schedule.split(",")
            for fillTime in splitSchedule:
                splitFill = fillTime.split(':')
                fillTimeToday = timeZeroToday+td(minutes=int(splitFill[1]),hours=int(splitFill[0]))
                timeDifference = fillTimeToday-curTime        
                if timeDifference >= timeZero: #only include fills that will happen after the current time
                    detectorNames.append(detector)
                    detectorGivenNames.append(self.detectorConfigDict[detector]["Name"])
                    detectorDiffFromNow.append(timeDifference)
                    detectorFillTime.append(fillTime) 
                      
        
        sortedIndex = np.argsort(detectorDiffFromNow)
        if len(sortedIndex)!=0:
            returnString = "\tNext detector to be filled today is %s%s(%s)%s at %s%s%s"%(\
                    bcolors.OKGREEN,detectorNames[sortedIndex[0]],detectorGivenNames[sortedIndex[0]],\
                           bcolors.ENDC,bcolors.OKGREEN,detectorFillTime[sortedIndex[0]],\
                            bcolors.ENDC)
        else:
            returnString=''        
        self.configDictLock.release()
        return returnString

    
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
        self.valuesDictLock.acquire()
        self.configDictLock.acquire()
        self.EventLog.info('Load Detector Configuration from %s'%self.detectorConfigFile)
        cnfgFile = ConfigParser.RawConfigParser()
        cnfgFile.read(self.detectorConfigFile)
        detectors = cnfgFile.get('Detectors','Names').split(',')
        self.detectorSettings = cnfgFile.get('Detectors','Settings').split(',')
        self.detectorNumbers = []
        self.detectorNamesDict = {}
        for detector in detectors:
            config = {}
            for setting in self.detectorSettings:   
                config[setting] = cnfgFile.get(detector, setting)
            self.detectorConfigDict[detector] = config
            number = detector.split(' ')[1]
            self.detectorNumbers.append(number)
        self.enabledDetectors = []
        self.loggingDetectors = []
        self.detectors = []
        self.lineChillEnabled = False
        self.lineChillTimeout = 0
        for detector in self.detectorConfigDict.keys():
            if 'Detector' in detector: #make sure it is a detector not the line chill
                self.detectors.append(detector)
            
                self.detectorValuesDict[detector] = {'Detector Temperature':'N/A','Vent Temperature':'N/A',\
                                'Valve State':False,'Fill Started Time':'N/A',"Fill Expired":False,\
                                'Fill Inhibited':False}
                if self.detectorConfigDict[detector]['Fill Enabled'] == 'True':
                    self.enabledDetectors.append(detector)
                if self.detectorConfigDict[detector]['Temperature Logging'] == 'True':
                    self.loggingDetectors.append(detector)
                self.detectorNamesDict[self.detectorConfigDict[detector]["Name"]] = detector.split(' ')[1]
                #Just get the detector number, 'Detector' will be added inthe GUI
                
        lineChillEnabled = cnfgFile.get('Line Chill','Fill Enabled')
        if lineChillEnabled == 'True' or lineChillEnabled == 'False':
            self.lineChillEnabled = lineChillEnabled
        
        self.lineChillTimeout = float(cnfgFile.get('Line Chill','Maximum Fill Time'))  
        self.valuesDictLock.release()
        self.configDictLock.release()
        errorMsgLst = self.checkValidConfiguration(self.detectorConfigDict,self.enabledDetectors)
        
        return errorMsgLst
       
    def applyDetectorConfig(self):
        '''
        Apply the configuration loaded by self.loadDetectorConfig
        '''
        offStates = [False]*len(self.detectors)
        self.writeEnableLEDState(self.detectors, offStates)
        if len(self.enabledDetectors) != 0: #if there are no enabled detectors then do turn any of the leds on
            states = [True]*len(self.enabledDetectors)
            self.writeEnableLEDState(self.enabledDetectors, states)
        if self.lineChillEnabled == 'True':
            chillState = True
        elif self.lineChillEnabled == 'False':
            chillState = False
        self.writeEnableLEDState(['Line Chill'],[chillState])
        
        self.loadConfigEvent.clear()
    
    def startRunThread(self):
        '''
        Start the thread that will run
        '''   
        errorStr = self.checkValidConfiguration(self.detectorConfigDict,self.enabledDetectors)
        errorStr += self.LJ.checkRelayPower()
        runningThreads = threading.enumerate()
        for thread in runningThreads:
            if thread.name == self.mainThreadName:
                errorStr+='Thread already running.'
        if errorStr != '':
            return errorStr
        else:
            mainThread = threading.Thread(target=self.runThread,name=self.mainThreadName,args=())
            mainThread.start()
            return ''
#         print 'end of run start'
    
    def stopRunThread(self,EXIT=False):
        '''
        Stop the MainControlThread 
        This will do the same thing as initRelease
        :EXIT: - bool, option for for turning everything off or just stopping the thread
        '''   
        self.stopRunningEvent.set()
        threads = threading.enumerate()
        for thread in threads: #join the thread
            if thread.name == self.mainThreadName:
                thread.join()
                
        states = [False] * len(self.detectors)
        self.writeValveState(self.detectors,states)
        self.writeEnableLEDState(self.detectors, states)
        self.writeEnableLEDState(['Line Chill'], [False])
        self.writeValveState(['Line Chill'], [False])
        self.LJ.writeErrorState(False)
        self.LJ.writeInhibitState(False)
        if EXIT == False: #another type of flash will be used when exiting the program
            self.LJ.stopOperationFlash() #let the user know everything has stopped
        self.stopRunningEvent.clear()
        
    def runThread(self):
        '''
        Thread run the detector filling
        '''

        self.stopRunningEvent.clear()
        self.applyDetectorConfig()
        self.LJ.heartbeatFlash()
        self.errorList = [] #clean the error list for at the beginning of each run
        while self.stopRunningEvent.isSet() == False:
            # read all the detector temps temperatures
            self.readDetectorTemps()
            self.logDetectorTemps() #log the temps that are enabled.
            # if the check configuration event is set read the configuration 
                #list to get a list of enabled detectors and other  
            # check temperatures for any enabled detectors that are 
                #above Maximum temperature, set error LED and send email is nessassary
            
            self.checkDetectorTemperatures()
            # check enabled detector's settings and start fills if needed
            self.checkFillInhibit()
            self.checkStartDetectorFills()
            self.checkInhibitedFill() #check for previous fills that have been inhibited
            self.checkHardDriveCapacity() #see if the hard drive is full
#             print 'Detector 1 valve state',self.detectorValuesDict['Detector 1']['Valve State']
            if self.inihibitFills == False: #if the inhibit fills is true no new 
                                            #fills will be started so don't do anyother checking
                # check currently filling detectors for min fill time breach
                self.checkMinFillTime()
                # for filling detectrors check for vent temp reaching LN levels
                self.checkVentTemp()
                #check for errors with filling or detector temperature
                self.checkExpiredFill()
                # check for filling timeout, set error and close valve if nessassary   
                self.checkFillTimeout()
                

            curTime = time.time()
            startScan = curTime + self.pollTime
            self.decideToSendEmail()
            if self.errorList != []:
                self.LJ.writeErrorState(True)
            self.LJ.heartbeatFlash() #flash the heart beat before any breaks can happen, 
                                        #different flash is used when stopping thread 
            while curTime < startScan: #while the thread sleeps check the fill inhibit, stoprunning, loadconfig
                if self.stopRunningEvent.isSet() == True:
                    break
                if self.loadConfigEvent.is_set(): # check if the config file has been changed and reload it if nessary
                    self.applyDetectorConfig()
                    self.loadConfigEvent.clear()
                self.checkFillInhibit()
                time.sleep(.5) #A LJM reconnect error is thrown at checkFillInhibit on a regular basis
                                # perhaps the sleep will give the USB some rest
                curTime = time.time()

         
    
    def checkDetectorTemperatures(self):
        '''
        Check the enabled detectors to see if there temperatures exceed the Maximum temp limits 
        
        '''  
        self.configDictLock.acquire()
        self.valuesDictLock.acquire()
        for detector in self.enabledDetectors:
            maxTemp = float(self.detectorConfigDict[detector]['Detector Max Temperature'])
            curTemp = float(self.detectorValuesDict[detector]['Detector Temperature'])
            if curTemp > maxTemp:
                name = self.detectorConfigDict[detector]['Name']
                msg = '%s (%s) temperature has exceeded its max allowed temperature'%(detector,name)
                self.errorList.append(msg)
        self.configDictLock.release()
        self.valuesDictLock.release()               
        
    def checkStartDetectorFills(self):
        '''
        Check the schedule for each detector and start a fill if needed     
        '''    
        detectorToOpen = []
        curTime = dt.today()
        curTimeStr = curTime.strftime(self.timeFormat) #get the current time as a sting with format Hour:Min
        
        for detector in self.enabledDetectors:
            schedule = self.detectorConfigDict[detector]['Fill Schedule']
            logMsg = "Checking %s, Time: %s, Schedule: %s"%(detector,curTimeStr,repr(schedule))
            self.EventLog.debug(logMsg)
            if curTimeStr in schedule:
#                print "Detector to Fill: ", detector, "Schedule: ",schedule,"Current Time: ",curTimeStr    
                if self.detectorValuesDict[detector]['Valve State'] == False: 
                        #check to make sure the valve has not already been opened
                    detectorToOpen.append(detector) #make the list of valves to open
#                    print "ValvesToOpen: ",detectorToOpen
                    
        numValves = len(detectorToOpen)
        if self.inihibitFills == True:
            if numValves != 0:
                detectorName = self.detectorConfigDict[detectorToOpen[0]]["Name"]
                msg = 'Fill inhibit prevented %s (%s) from starting a fill'%\
                        (detectorToOpen[0],detectorName)
                self.detectorValuesDict[detector]['Fill Inhibited'] = True                
                self.errorList.append(msg)                
                self.EventLog.info(msg)
        else: #if the fills are not inhibited start the filling process
            if numValves != 0:
                states = [True] *numValves
                self.writeValveState(detectorToOpen,states)
                for detector in detectorToOpen:
                    self.detectorValuesDict[detector]['Valve State'] = True
#                    print 'Opening valve for detector', detector
                    self.detectorValuesDict[detector]['Fill Start'] = curTimeStr
                    minFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Minimum Fill Time']))
                    maxFillDelta = td(minutes=int(self.detectorConfigDict[detector]['Maximum Fill Time']))
                    self.detectorValuesDict[detector]['Minimum Fill Time'] = dt.strftime(\
                                                                    curTime+minFillDelta,self.timeFormat)
                    #min time the valve can be opened before 
                    self.detectorValuesDict[detector]['Minimum Fill Expired'] = False
                    self.detectorValuesDict[detector]['Maximum Fill Time'] = dt.strftime(\
                                                                    curTime+maxFillDelta,self.timeFormat)
                    self.EventLog.info('Opening fill valve for %s'%detector)
        
    def checkMinFillTime(self):
        '''
        Check the minimum fill time for the currently filling detector
        '''
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True: #only check min fill time for detectors that have open valves
                if self.detectorValuesDict[detector]['Minimum Fill Expired'] == False: # if the min time has expired don't check it again
                    minTimeout = self.detectorValuesDict[detector]['Minimum Fill Time']
#                     print 'Minimum timeout for %s %s'%(detector,minTimeout)
                    if minTimeout == curTime: # the intervals between check the detector should be less than a minute
                        print 'Min Fill Time has Expired', detector
                        self.detectorValuesDict[detector]['Minimum Fill Expired'] = True
                        self.EventLog.debug('Miminum Fill Time Expired for %s'%detector)
                    
                
    def threadRunningCheck(self):
        '''
        Check to see if the thread is running and return status
        '''    
        threadRunning = False
        threads = threading.enumerate()
        for thread in threads: #join the thread
            if thread.name == 'MainControlThread':
                threadRunning = True
        return threadRunning
        

    def checkVentTemp(self):
        '''
        Check the vent temperatures on filling detectors and see if it has reached liquid nitrogen temperatures
        '''
        self.valuesDictLock.acquire()
        valvesToClose = []
#         detectorValveTemps = self.LJ.readValveTemps(self.enabledDetectors)
        self.readVentTemps()
        for detector in self.enabledDetectors:
            ventTemp = self.detectorValuesDict[detector]['Vent Temperature']
            if self.detectorValuesDict[detector]['Valve State'] == True:
                if self.detectorValuesDict[detector]['Minimum Fill Expired'] == True:
                    if ventTemp <= self.ventCloseThresholdTemp:
                        valvesToClose.append(detector)
        numValves = len(valvesToClose)
        if numValves != 0:
            states = [False] * numValves
            print 'Closing valves, vent',valvesToClose
            self.writeValveState(valvesToClose,states)
            for detector in valvesToClose:
                self.detectorValuesDict[detector]['Valve State'] = False
                self.detectorValuesDict[detector]['Fill Expired'] = False
                self.EventLog.info('Closing %s fill valve, LN2 temperature reached'%detector)
           
        self.valuesDictLock.release()
        self.cleanValuesDict(valvesToClose) #clean the values dict after releasing the lock  
     
    def checkFillTimeout(self):
        '''
        Check to see if any fills have timedout
        '''
        self.valuesDictLock.acquire()
        self.configDictLock.acquire()
        valvesToClose = []
        curTime = dt.today().strftime(self.timeFormat)
        for detector in self.enabledDetectors:
            if self.detectorValuesDict[detector]['Valve State'] == True:
#                 timeoutTime = curTime + td(minutes=int(self.detetorValuesDict[detector]['Maximum Fill Time'])
                if curTime >= self.detectorValuesDict[detector]['Maximum Fill Time']:
                    valvesToClose.append(detector)
#                    msg = '%s fill has timed out'%(self.detectorConfigDict[detector]['Name'])
#                    self.errorList.append(msg) 
        numValves = len(valvesToClose)
        if numValves != 0:
#            print 'Closing valves, timeout',valvesToClose
            states = [False]*numValves
            self.writeValveState(valvesToClose,states)
            for detector in valvesToClose:
                
                self.detectorValuesDict[detector]['Valve State'] = False
                name = self.detectorConfigDict[detector]['Name']
                self.detectorValuesDict[detector]['Fill Expired'] = True
                                
                msg = '%s (%s) fill expired'%(detector,name)
                self.errorList.append(msg)
                self.EventLog.info('Closing %s fill valve, Maximum Fill Time reached'%detector)
        self.configDictLock.release()
        self.valuesDictLock.release()
        # Clean the values dict after releasing the dict locks   
        self.cleanValuesDict(valvesToClose)

    def checkExpiredFill(self):
        '''
        Check the values dict and see if there has been an expired fill
        '''
        
        self.valuesDictLock.acquire()
        self.configDictLock.acquire()
        for detector in self.enabledDetectors:
#            print "Values Dict",self.detectorValuesDict[detector]
            try:
                if self.detectorValuesDict[detector]['Fill Expired'] == True:
                    name = self.detectorConfigDict[detector]['Name']
                    msg = '%s (%s) fill expired'%(detector,name)
                    self.errorList.append(msg)                
            except KeyError:
#                print "KeyError", detector
                continue
        self.configDictLock.release()
        self.valuesDictLock.release()
    
    def checkInhibitedFill(self):
        '''
        Check the values dict and see if a fill has been inhibited and report it to the error listen
        
        '''
        self.valuesDictLock.acquire()
        self.configDictLock.acquire()
        for detector in self.enabledDetectors:
            try:
                if self.detectorValuesDict[detector]['Fill Inhibited'] == True:
                    name = self.detectorConfigDict[detector]['Name']
                    msg = 'Fill inhibit prevented %s (%s) from starting a fill'%(detector,name)
                    self.EventLog.info(msg)
                    self.errorList.append(msg)                
            except KeyError:
#                print "KeyError", detector
                continue

        self.configDictLock.release()
        self.valuesDictLock.release()

    def checkHardDriveCapacity(self):
        '''
        Get the current free capacity of the hard drive and report an error if it is 
        above the limits.
        If the hard drive fills up then the auto fill may not funciton properly
        '''         
        percentFree = psutil.disk_usage('/').percent
        if percentFree >= self.hardDriveUsageLimit:
            msg = "Hard Drive has exceeded is usage limit. Program may not function properly."
            self.errorList.append(msg)

    def constructDetectorErrors(self):
        '''
        Check the error in the error dict and compose and email body
        '''   
        if self.errorList == []: #if no errors 
            return ''
#             self.errorDict = {}
#             self.LJ.writeErrorState(False)
        errorDict = {} #rewrite the error dict each time to make sure errors do not get counted mulitple times        
        for error in self.errorList:
            try:
                errorDict[error] += 1
#                print error,': ',errorDict[error]
            except KeyError:
                errorDict[error] = 1
        
        emailBody = ''
        emailErrorList = []
        for (error, numRepeat) in self.errorDict.iteritems():
#            print "Construct ",error,": ",numRepeat
            if numRepeat >= self.errorRepeatLimit:
                emailErrorList.append(error)
                errorDict[error] = 0 #reset the error counter 
                self.errorList = filter(lambda x: x != error, self.errorList) 
                                #remove the errors that have been reported
                               
            else:
                continue
        emailBody = ",".join(emailErrorList)
        self.errorDict = errorDict        
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
                msg = '"%s" has been reported %d time(s)\n'%(error,numRepeat)
                errorString += msg
                self.EventLog.info(msg)
        return errorString
    
    def cleanValuesDict(self,detectors):
        '''
        Reset self.detectorValuesDict after a fill has been completed
        this will reset 'Minimum Fill Time', 'Minimum Fill Expired', 'Maximum Fill Timout','Fill Started Time'
        :detectors: - list of detectors to clean up
        
        '''
        self.valuesDictLock.acquire()
        self.EventLog.debug("Cleaning detector values dictionary")
        for detector in detectors:
            if 'Line Chill' == detector:
                continue
            else:
                self.detectorValuesDict[detector]['Minimum Fill Time'] = '0'
                self.detectorValuesDict[detector]['Minimum Fill Expired'] = False
                self.detectorValuesDict[detector]['Maximum Fill Time'] = '0'
                self.detectorValuesDict[detector]['Fill Started Time'] = '0:0'
        self.valuesDictLock.release()
            
    def cleanErrorDict(self):
        '''
        Clean the error dict, only user input will run this method
        '''    
        self.errorDict = {}
        self.errorList = []
        self.LJ.writeErrorState(False)
        self.errorEmailDict = {}
        return True
    
    def decideToSendEmail(self):
        '''
        Decide what (if any) emails need to be sent and what is in the email
        '''
        validErrors = self.constructDetectorErrors();
        emailErrorList = []
        if validErrors=='':
            return 
        for error in validErrors.split(','):
            try:
                errorCount = self.errorEmailDict[error]
#                print "Decide:",error,': ',errorCount
                if errorCount > self.errorEmailRepeatLimit:
                    emailErrorList.append(error)
                    self.errorEmailDict[error] = 0
                else:
                    self.errorEmailDict[error] = errorCount+1
            except KeyError: #send the error the first time it is reported
                self.errorEmailDict[error] = 0
                emailErrorList.append(error)
#        print "ErrorDict", self.errorEmailDict
        if emailErrorList != []:
            emailBody = ','.join(emailErrorList)        
            self.sendEmail(emailBody)

        
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
        
        with self.valuesDictLock and self.configDictLock:
            for detector in self.enabledDetectors: #make a string of the last read detector temperatures
                temp = self.detectorValuesDict[detector]['Detector Temperature']
                name = self.detectorConfigDict[detector]["Name"]
                detStr = '%s (%s) current temperature %sC\n'%(detector,name,temp)
                tempString+=detStr
#        print "Sending Email!"
        errorBody += '\n'+tempString
        self.EventLog.info('Sending Email:'+repr(errorBody))
        msg = MIMEText(errorBody+self.emailSignature)
        msg['Subject'] = 'Room 134 Liquid Nitrogen Fill System'
        msg['From'] = self.senderEmail
        msg['To'] = self.emailRecipents
        p = Popen(["msmtp", "-a", "gmail",'-t'], stdin=PIPE)
        p.communicate(msg.as_string())         
            
            
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
            self.inihibitFills = state
            self.fillInhibitEvent.clear()
#             self.LJ.writeInhibitState(state)
        
        
    def readDetectorConfig(self,detector):
        '''
        Read the detector configuration from the config dict and return a string of the stuff
        :detector: -name of detector to read
        '''
        if detector == 'Line Chill':
            returnString = '\t'+detector+'\n'
            returnString += '\t'+ 'Fill Enabled-> ' +bcolors.OKGREEN+self.lineChillEnabled+bcolors.ENDC+'\n'\
                            +'\t'+'Maximum Fill Time-> '+bcolors.OKGREEN+'%d'%self.lineChillTimeout+bcolors.ENDC
        else:
            returnString = '\t'+detector+'\n'
            for setting in self.detectorSettings:
                returnString+='\t'+setting+' -> '+bcolors.OKGREEN+self.detectorConfigDict[detector][setting]\
                            +bcolors.ENDC + '\n'
        
        return returnString
    
    def changeDetectorSetting(self,detector,setting,value):
        '''
        Collect the settings that will be made to the detector settings. This will not write to the config file or change any settings  
        :detector: - string, detector name 
        :setting: - string, name of setting that will be changed
        :value: - string, value of setting to be written
    
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
                with self.configDictLock:
                    name = self.detectorConfigDict[detector]['Name']
                returnString += '%s (%s) %s will be set to ->'%(detector,name,setting)+\
                                bcolors.OKGREEN+' %s \n'%(value)+bcolors.ENDC
        self.detectorChangesDict = {} #clean the dict so the settings will not be repeated
        return detectors,settings,values,returnString
        
    def writeDetectorSettings(self,sections,options,values): 
        '''
        load and write the config file using the inputs
        :sections: - list section names that will be written to, will be detector names
        :options: - list option within the section to write value to, ie name, Maximum Fill Time, fill schedule
        :values: - list of values to that will be corresponding option will be set to
        '''
        cnfgFile = ConfigParser.RawConfigParser()
        cnfgFile.read(self.detectorConfigFile)
        for (section,option,value) in zip(sections,options,values):
            cnfgFile.set(section, option, value)
        with open(self.detectorConfigFile, 'w') as FILE:
            cnfgFile.write(FILE)

        self.cleanValuesDict(sections)
#            print "Write Finished" 
        self.loadDetectorConfig()
           
        self.loadConfigEvent.set()
        
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
            if detector == 'Line Chill':
                if option == 'Fill Enabled':
                    self.lineChillEnabled=value
                elif option == 'Maximum Fill Time':
                    self.lineChillTimeout=value
            else:
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
            Check the fill schedule for conflicts between other detector fill schedules, 
        only one detector will be allowed to fill at a time. Each detector will have exclusive
        control over the fill valve starting at the scheduled start time and extending to the
        Maximum Fill Time. Other detector can not be scheduled for filling during this time. 
        This check is only done for detectors that are enabled or will become enabled.
        
        :settingsDict: - dict of current detector settingsDict
        :enabledDetectors: - list of detector names that will be/are enabled
        '''
        
        self.configDictLock.acquire()
        if len(enabledDetectors) >= 1:
            startTimes = []
            timeOuts = []
            detectorNames = []
            for detector in enabledDetectors:
                times = []
                fillTime = settingsDict[detector]['Fill Schedule'].split(',')
                for time in fillTime:
                    times.append(dt.strptime(time,self.timeFormat))
                startTimes.append(times)
                timeout = self.detectorConfigDict[detector]['Maximum Fill Time']
                timeOuts.append(td(minutes=int(timeout)))
                detectorNames.append(self.detectorConfigDict[detector]['Name'])
            errorList = []
            errorList += self._checkFillOverlap(enabledDetectors, detectorNames, startTimes, timeOuts)
            errorList += self._checkFillConflicts(enabledDetectors, detectorNames, startTimes, timeOuts)
            self.configDictLock.release()
            return errorList
        else:
            self.configDictLock.release()
            return []
        #make a fill start and end time, check that other fill start times do not fall between start and end time

    def checkValidName(self,detectorConfigDict):
        '''
        Check for conflicts in the detector names, ie no detectors should have the same nameText
        :detectorConfigDict: - dictionary of the settings 
        '''
        names = []
        errorList = []
        for detectorNum in detectorConfigDict.iterkeys():
            name = detectorConfigDict[detectorNum]['Name']
            if ' ' in name:        
                errMsg = '"%s" not a valid name for %s, name contains a space.'%(name,detectorNum)
                errorList.append(errMsg)
            if name == 'chill':
                errMsg = '"%s" not a valid name for %s, name can not be chill.'%(name,detectorNum)
                errorList.append(errMsg)
            if name in names:
                errMsg = '"%s" not a valid name for %s, name already used.'%(name,detectorNum)
                errorList.append(errMsg)
            names.append(name)
        return errorList

    def _checkFillOverlap(self,detectors,detectorNames,schedules,timeouts):
        '''
        Check the fill schedule for each detector for overlaping fills within each detector. 
        Detector fill time is defied as start time + Maximum Fill Time 
        Example of overlaping  schedule -> [[12:10,12:14]] timeout [5]
        :detectors: - list of detectors to check for overlaps
        :schedules: - nested list of schedules for each detector, should be each entry should be a datetime object
        :timeouts: - list of timout values for each detector, items should be timedelta objects
        '''  
        overlapList = []
        if len(detectors) < 1:
            return overlapList
        for (detector,detName,schedule,timeout) in zip(detectors,detectorNames,schedules,timeouts):
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
                        msg = '%s(%s) has Schedule Overlap: %s and %s with timeout: %s min'%\
                                    (detector,detName,Sch1,Sch2,Tout)
                        overlapString.append(msg)
                        
                    else:
                        continue
        return overlapList
        
    def _checkFillConflicts(self,detectors,detectorNames,schedules,timeouts):
        '''
        Check the fill schedule for conflicts between scheduled fills
        Detector fill time is defied as start time + Maximum Fill Time
        Example: Detectors -> [Detector 1, Detector 2], schedules -> [[12:13,15:40],[2:22,12:17]], timeouts -> [5,5]
        :detectors: - list of enabled detectors to check for conflicts
        :schedules: - nested list of fill schedules for each detector, items should be datetime objects
        :timeouts: - list of timeout values for the given detector, items should be timedelta objects
        '''
        conflictList = []
        numDetectors = len(detectors)
        if numDetectors <=1:
            return conflictList
        for i in range(numDetectors): #interate through all the detectors that will be checked
            detector_i = detectors[i] #set the values that will be checked against all the other detectors, 'master' detector
            detector_i_name = detectorNames[i]
            schedule_i = schedules[i] #all detectors need to be master detectors
            timeout_i = timeouts[i]
        
            for h in range(numDetectors):#interage thought all the other detectors, excluding 'master' detector
                if h == i:
                    continue
                else:
                    detector_h = detectors[h]#get the detector values that will be checked against, 
                    schedule_h = schedules[h]
                    detector_h_name = detectorNames[h]
#                     timeout_h = timeouts[h]
                    for start_i in schedule_i: #cycle through the fill times from the 'master' detector
                        end_i = start_i + timeout_i #make the filling window
                        for start_h in schedule_h: #cycle through the detector that will be checked
                            if start_h >= start_i and start_h <= end_i: # check if detector fill start time is within the window of the 'master'
                                strTime_i = dt.strftime(start_i,self.timeFormat)
                                strtime_h = dt.strftime(start_h,self.timeFormat)
                                strtimeout_i = str(timeout_i).split(':')[1]
#                                 strtimeout_h = str(timeout_h).split(':')[1]
                                conStr = '%s(%s) fill at %s (%s min timeout) conflicts with %s(%s) fill at %s'%\
                                        (detector_i,detector_i_name,strTime_i,strtimeout_i,
                                        detector_h,detector_h_name,strtime_h)
                                conflictList.append(conStr)
                            else:
                                continue
        return conflictList
                        
    def checkMinFillMaxFillConflicts(self,detectorSettingsDict):
        '''
        Check the min fill time is less than the max fill time
        :detectorSettingsDict: -- settings dict that will be checked for conflicts
        '''    
        detectors = []
        timeouts = []
        for detector in detectorSettingsDict.iterkeys():
            detectors.append(detector)
            minimumFill = detectorSettingsDict[detector]['Minimum Fill Time']
            MaximumFill = detectorSettingsDict[detector]['Maximum Fill Time']
            timeouts.append((minimumFill,MaximumFill))
        msgLst=[]
        for (detector,timeout) in zip(detectors,timeouts):
            (minFill,maxFill) = timeout
            intMinFill = int(minFill)
            intMaxFill = int(maxFill)
            if intMinFill >= intMaxFill:
                detectorName = detectorSettingsDict[detector]["Name"]
                msg = "%s (%s) has invalid Maximum/Minimum Fill Time, Minimum Fill (%s) >= Max Fill (%s)"%\
                        (detectorName,detector,minFill,maxFill)
                msgLst.append(msg)
        return msgLst

    def checkValidConfiguration(self,detectorSettingsDict,enabledDetectors):
        '''
        Check that the Detector Configuration is valid
        :detectorSettingsDict: -- dictionary containing detector configurations
        :enabledDetectors: -- list of detectors that are currently enabled
        '''
        errorLst = []
        errorLst += self.checkFillScheduleConflicts(detectorSettingsDict,enabledDetectors)
        errorLst += self.checkMinFillMaxFillConflicts(detectorSettingsDict)
        errorLst += self.checkValidName(detectorSettingsDict)
        errors = []
        for error in errorLst:
            if error != '':
                errors.append(error)
        errorStr = '\n\t'.join(errors)
        return errorStr

    def graphDetectorTemp(self,detName):
        '''
        Make a plot of the recorded temperatures for the give detector number
        :detName: - detector number string that the graph will be made,
        '''
        fileName = detName.replace(' ','') #take the space out of detector name to match file name
        logFile = self.logDir+'%sLog.txt'%fileName
        
        with self.valuesDictLock and self.configDictLock: 
            #get the values dict lock to prevent logDetectorTemp from grabbing the log file
            with open(logFile, 'r') as FILE:
                detectorTemps = FILE.readlines() #read all the
            detectorName = self.detectorConfigDict[detName]['Name']
        temps = []
        times = []
        dataDate = detectorTemps[-1].split('|')[0].split(' ')[0] #Log files only record for one day, get that date
                            #get the date at the end of the file, ie the most current values
        for line in detectorTemps:
            line = line.strip('\r')
            sline = line.split('|')
            dateNum = pltdates.date2num(dt.strptime(sline[0],self.loggingTimeFormat))
            times.append(dateNum)
            cleanTemp = sline[1].replace(' C','')
            temps.append(float(cleanTemp))
        normalFig = plt.figure()
        normalFig.set_size_inches(12,6,forward=True)
#         subtitle = 'Beam Cocktail: %s, Data Date %s'%(self.dataDict[filenames[0]]['Cocktail'],self.dataDate)
        normalFig.canvas.set_window_title('Temperature Vs Time for %s(%s)'%(detName,detectorName))
        subtitle = 'Temperature Vs Time'
        normalFig.suptitle(subtitle,fontsize=15)
        normalax = normalFig.add_subplot(111)
        normalax.plot_date(times,temps,'-',linewidth=1.0,label='%s(%s) Temperature Log'%(detName,detectorName))
        normalax.set_xlabel('Date (%s)'%dataDate)
        normalax.set_ylabel('Detector Temperature (C)')
        normalax.autoscale_view()
        xaxisFormat = pltdates.DateFormatter('%H:%M:%S') #only show the time the data was taken, its only from one day
        normalax.xaxis.set_major_formatter(xaxisFormat)
        plt.show(block=True)
        
        
    


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
#     def getMemoryUsage(self):
#         '''
#         I think the ram might be filling up and causing the segmentation error
#         get it and log it in the event log
#         '''
#         mem = psutil.virtual_memory()
#         msg = "Current Memory usage %.2f"%mem.percent
#         self.EventLog.info(msg)

