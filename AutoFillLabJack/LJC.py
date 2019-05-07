'''
Created on Sep 15, 2016

@author: ADonoghue
'''
from labjack import ljm
from labjack.ljm import LJMError
from time import sleep
import logging
import time

# from multiprocessing.managers import State
# from ConfigParser import RawConfigParser

class LJC(object):
    '''
    classdocs
    '''


    def __init__(self,cnfgFile ):
        '''
        Constructor
        '''
#         self.serialNumber = serialNumber
#         self.connectionType = connectionType
        self.wiringcfg = cnfgFile
        self.enableLEDDict = {}
        self.valveControlDict = {}
        self.detectorTempDict = {}
        self.detectorTempTypeDict ={}
        self.valveTempDict = {}
        self.valveTempTypeDict= {}
        self.extendedFeaturesIndex = {'None':0,
                                      'Thermocouple K':22,
                                      'RTD PT100':40}
        self.EventLog = logging.getLogger('EventLog')
        
    
    def controllerInit(self):
        '''
        initalize the controller
        '''
        i = 0
        msg = ''
       
        self.controller = ljm.openS('T7', 'USB', '470013817')
        self.loadWiring()
        msg = self.checkRelayPower()
        i=4 # If everything worked out break the while loop
        self.configureTemperatureInputs()
        return msg
 
    def releaseInit(self):
        '''
        Close the connection to the labjack
        '''
#         print 'release'
        try:
            ljm.close(self.controller)
            del self.controller
            self.EventLog.info('Releasing LabJack Controller')
        except:
            return
    
    def loadWiring(self):
        '''
        Read the wiring config file that contains port names for the detector items (enable LED, Valve Control, etc)
        '''
        self.EventLog.debug('Loading wiring config file.')
        self.detectorList = self.wiringcfg.get('Detectors','Names').split(',')
        for detector in self.detectorList:
            self.enableLEDDict[detector] = self.wiringcfg.get(detector,'Enable LED')
            self.valveControlDict[detector] = self.wiringcfg.get(detector,'Valve Control')
            self.detectorTempDict[detector] = self.wiringcfg.get(detector,'Detector Temp')
            self.detectorTempTypeDict[detector] = self.wiringcfg.get(detector,'Detector Temp Type')
            self.valveTempDict[detector] = self.wiringcfg.get(detector,'Valve Temp')
            self.valveTempTypeDict[detector] = self.wiringcfg.get(detector,'Valve Temp Type')
        common = 'Common Settings'
        self.errorLed = self.wiringcfg.get(common,'Error LED')
        self.inhibitLed = self.wiringcfg.get(common,'Inhibit LED')
        self.inhibitInput = self.wiringcfg.get(common,'Inhibit Input')
        self.heartbeatLed = self.wiringcfg.get(common,'Heartbeat LED')
        self.relayPower = self.wiringcfg.get(common,'Relay Power Check')
        
    def configureTemperatureInputs(self):
        '''
        Configure the temperature inputs for the detector and vent temp
        '''
        thermoNamesList = []
        rtdNamesList = []
        thermoTypesList = []
        rtdTypesList = []
        for detector in  self.detectorList:
            thermoNamesList.append(self.valveTempDict[detector])
            rtdNamesList.append(self.detectorTempDict[detector])
            thermoTypesList.append(self.valveTempTypeDict[detector]) #valves use thermocouples to read temperature
            rtdTypesList.append(self.detectorTempTypeDict[detector]) #detectors use rtds to read inputs
#        self.EventLog.debug("Setting %s to RTD"%repr(rtdNamesList))
	self.configureRTDRegisters(rtdTypesList, rtdNamesList)
#	self.EventLog.debug("Setting %s to Thermocouple"%repr(thermoNamesList))
        self.configureThermocoupleRegisters(thermoTypesList,thermoNamesList)
        
        
    def configureThermocoupleRegisters(self,configurations,names):
        '''
        Set extended features for the analog inputs
        :configuration: - configuration type for the specified channel, string of configuration type will be converted to index number
        :names: - channel to set configration
        '''
        
#         ljm.eWriteName(self.controller,EF_name,index)
        
        for (name,configuration) in zip(names,configurations):
            self.EventLog.debug('Configuring analog input %s for Thermocouple.'%name)
            index = self.extendedFeaturesIndex[configuration]
            EF_name = name+'_EF_INDEX'
            CONFIG_A_Name = name+'_EF_CONFIG_A'
            CONFIG_B_Name = name+'_EF_CONFIG_B'
            CONFIG_D_Name = name+'_EF_CONFIG_D'
            CONFIG_E_Name = name+'_EF_CONFIG_E'
            setting_names = [EF_name,CONFIG_A_Name,CONFIG_B_Name,CONFIG_D_Name,CONFIG_E_Name]
            setting_values = [index,    1,              0,           55.56,        255.37]
            numFrames = len(setting_values)
            ljm.eWriteNames(self.controller, numFrames, setting_names, setting_values)
#             ljm.eWriteName(self.controller, name, index)
            
    def configureRTDRegisters(self,configurations,names):
        '''
        Set the configuration registers for the rtd inputs
        :configurations: - type of rtds to configure
        :names:- names of analog inuputs that will be used
        '''
        
        for (name,configuration) in zip(names,configurations):
            self.EventLog.debug('Configuring analog input %s for RTD.'%name)
            EF_name = name+'_EF_INDEX'
            CONFIG_A_Name = name+'_EF_CONFIG_A' #temperature display
            CONFIG_B_Name = name+'_EF_CONFIG_B' #excitation circuit
            CONFIG_D_Name = name+'_EF_CONFIG_D' #excitation Voltage
            CONFIG_E_Name = name+'_EF_CONFIG_E' #excitation resistance
            index = self.extendedFeaturesIndex[configuration]
            setting_names =  [EF_name,CONFIG_A_Name,CONFIG_B_Name,CONFIG_D_Name,CONFIG_E_Name]
            setting_values = [index,  1,            4,            2.500,        1000]
            numFrames = len(setting_values)
            ljm.eWriteNames(self.controller, numFrames, setting_names, setting_values)
            
            
    def readVentTemps(self,detectorList):
        '''
        Read the valve temperatures from the list
        :detectorList: - list of string detector names whose temperatures will be read from the labjack
        '''
        names = []
        for detector in detectorList:
            names.append(self.valveTempDict[detector]) #build the list of port names for the requested temperature
        names_readA = map(lambda x: x+'_EF_READ_A', names) #adjust the name to read with the EF options
        self.EventLog.debug('Reading vent temperatures from %s'%repr(names_readA))
        stringTemps = self._LJReadWrite(names_readA) #return the values
        return stringTemps
#         return map(lambda x: float(x),stringTemps) #conver to list of floats
        
    def readDetectorTemps(self,detectorList):
        '''
        Read the detector temperatures from the list
        :detectorList: - list of string detector names whose temperatures will be read from the labjack
        '''
        names = []
        for detector in detectorList:
            names.append(self.detectorTempDict[detector]) #build the list of port names for the requested temperature
        names_readA = map(lambda x: x+'_EF_READ_A', names) #adjust the name to read with the EF options
        self.EventLog.debug('Reading detector temps from %s.'%repr(names))
        return self._LJReadWrite(names_readA) #return the values
            
    def writeValveStates(self,detectorList, valveStates):
        '''
        write the valve states for the detector list, on or off
        :detectorList: - list of string detector names whose temperatures will be read from the labjack
        :valveStates: - list the valve states for the detector in the detector list, [bool]
        '''      
        names = []
        values = []
        for (detector,value) in zip(detectorList,valveStates):
            names.append(self.valveControlDict[detector]) #build the list of port names for the requested temperature
            if value == True: #convert to On Off to 1,0
                values.append(1)
            elif value == False:
                values.append(0)
        self.EventLog.debug('Writing fill valve states %s to %s'%(values,names))
        return self._LJReadWrite(names,values) #return the values  
    
    def writeEnableLEDState(self,detectorList,ledStates):
        '''
        write the valve states for the detector list, on or off
        :detectorList: - list of string detector names whose temperatures will be read from the labjack
        :ledStates: - list of LED states for the detectors in the detector lists, [bool]
        ''' 
        names = []
        values = []
        for (detector,value) in zip(detectorList,ledStates):
            names.append(self.enableLEDDict[detector]) #build the list of port names to write the
            if value == True: #convert to On Off to 1,0
                values.append(1)
            elif value == False:
                values.append(0)
            else:
                msg="Not A Valid Option"
                print repr(value), msg
        self.EventLog.debug('Writing %s to enable leds for %s'%(values,names))
        return self._LJReadWrite(names,values) #return the values  
    
    def writeErrorState(self,state):
        '''
        Turn the error led on or off
        :state: - state to set the led
        '''   
        self.EventLog.debug('Writing error led to %s'%state)
        self._LJWriteSingleState(self.errorLed, state)
        
    def writeInhibitState(self,state):
        '''
        wite the state to the inhibit led
        :state: state to ste the inhibit let to, bool
        '''
        self.EventLog.debug('Writing inhibit led to %s'%state)
        self._LJWriteSingleState(self.inhibitLed, state)
        
    def readInhibitState(self):
        '''
        Read the inhibit input 
        '''
        return self._LJReadSingleState(self.inhibitInput)
        
    def heartbeatFlash(self):
        '''
        Flash the hearbeat light
        '''
        self.writeHeartbeatState(True)
        sleep(.03)
        self.writeHeartbeatState(False)
        sleep(.03)
        self.writeHeartbeatState(True)
        sleep(.03)
        self.writeHeartbeatState(False)
      
    def stopOperationFlash(self):
        '''
        Flash the heatbeat light to let the operator know the filling operation has stopped
        Two long flashes
        '''   
        self.writeHeartbeatState(True)
        sleep(.15)
        self.writeHeartbeatState(False)
        sleep(.15)
        self.writeHeartbeatState(True)
        sleep(.15)
        self.writeHeartbeatState(False)
    
    def releaseInitFlash(self):
        '''
	Flash the heatbeat light to let the operator know the filling program will closed, ie exit was called


        '''
	self.writeHeartbeatState(True)
	sleep(0.3)
	self.writeHeartbeatState(False) 
    def writeHeartbeatState(self,state):
        '''
        Write the state of the heartbeat led, ie on or off
        :state: state to set the heartbeat status to
        '''
        self._LJWriteSingleState(self.heartbeatLed, state)
    
    def checkRelayPower(self):
        '''
        Check the relay power is on, input CIO0 is connected to the 12VDC power supply
        If the AC power is not on the DC power will not be on and the input will be 0
        '''    
        value = self._LJReadSingleState(self.relayPower)
#         print 'AC power value', value
        if value == False: #power is off tell the user!
            msg = 'Relay (AC) Power is Off!'
            return msg #the error will be handled by the Interface
#             raise LJMError(errorString=msg)
        elif value == True:
            return '' 
   
    def _LJWriteSingleState(self,name,state):
        '''
        Write a single value to the 
        :name: string name of the to set state to
        :state: state to write the name, bool. will be converted to value
        '''
        if state == True:
            value = 1
        elif state == False:
            value = 0
        self._LJReadWrite([name], [value])
                             
    def _LJReadSingleState(self,name):
        '''
        Read a single value from a digital input, convert it to bool
        :name: - string name of input to read
        '''           
        value = self._LJReadWrite(name)
        if value == 0:
            state = False
        elif value == 1:
            state = True
        return state

    def _LJReadWrite(self,names,values=None):
        '''
        Read or Write the given names and values from the LabJack
        :names: - list of names or single name to read or write 
        :values: - list of values or single value to write, if not given the function will read and return the values
        
        '''
#        tries = 0
#        while tries < 2:
#        try:
        if values == None:
            if type(names) == type([]):
                returnValues = self._LJReadValues(names)
            elif type(names) == type(""):
                returnValues = self._LJReadValue(names)
            else:
                msg = "%s not a valid type for _LJReadWrite"%(type(names))
                returnValues = msg
#                tries = 4
            return returnValues
        else:
            if type(names) == type([]):
                returnValue = self._LJWriteValues(names,values)
            else:
                msg = "Failed, %s not a vlid type for writing"%type(names)
                returnValue = msg
#                tries = 4
            return returnValue
#        except LJMError as LJError:
            
#            tries += 1
#            print "Failed to read/write, try# %d"%tries
#            time.sleep(1)#sleep the thread before trying to talk with the LabJack again
                
#        if tries == 2:
#            raise LJError
            

    def _LJWriteValues(self,names,values):
        '''
        :names: - list of LJ channels names to write to
        :values: -list of values to write to the channels
        '''
        numFrames = len(names)
        ljm.eWriteNames(self.controller, numFrames, names, values)
    
    def _LJReadValues(self,names):
        '''
        :names: - list of LJ channels names to read from
        '''
        numFrames = len(names)
        values = ljm.eReadNames(self.controller, numFrames,names)
        return values
    
    def _LJReadValue(self,name):
        '''
        read a single value from the LabJack
        :name: - string, name of channel to read
        '''
        value = ljm.eReadName(self.controller,name)     
        return value
    
    
        
#     def writeCJCConfiguration(self):
#         '''
#         Write the configuration for the Cold Junction Compencation 
#         '''
        
        
