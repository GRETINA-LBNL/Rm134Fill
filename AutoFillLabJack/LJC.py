'''
Created on Sep 15, 2016

@author: ADonoghue
'''
from labjack import ljm
from labjack.ljm.ljm import LJMError
from time import sleep
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
        
    
    def controllerInit(self):
        '''
        initalize the controller
        '''
        try:
            self.controller = ljm.openS('T7', 'USB', '470013817')
#             print ljm.eReadName(self.controller,'SERIAL_NUMBER')
        except LJMError as ljerror:
            msg = 'Could not init LabJack %s'%ljerror._errorString
            print msg
        self.loadWiring()
        self.configureTemperatureInputs()
#         serialnumber = ljm.eReadName(self.controller, 'SERIAL_NUMBER')
#         print 'LabJack Serial Number: %f\n'%(serialnumber)
        
    def releaseInit(self):
        '''
        Close the connection to the labjack
        '''
#         print 'release'
        try:
            ljm.close(self.controller)
        except:
            return
    
    def loadWiring(self):
        '''
        Read the wiring config file that contains port names for the detector items (enable LED, Valve Control, etc)
        '''
        self.detectorList = self.wiringcfg.get('Detectors','Names').split(',')
        for detector in self.detectorList:
            self.enableLEDDict[detector] = self.wiringcfg.get(detector,'Enable LED')
            self.valveControlDict[detector] = self.wiringcfg.get(detector,'Valve Control')
            self.detectorTempDict[detector] = self.wiringcfg.get(detector,'Detector Temp')
            self.detectorTempTypeDict[detector] = self.wiringcfg.get(detector,'Detector Temp Type')
            self.valveTempDict[detector] = self.wiringcfg.get(detector,'Valve Temp')
            self.valveTempTypeDict[detector] = self.wiringcfg.get(detector,'Valve Temp Type')
        self.errorLed = self.wiringcfg.get('Common Settings','Error LED')
        self.inhibitLed = self.wiringcfg.get('Common Settings','Inhibit LED')
        self.inhibitInput = self.wiringcfg.get('Common Settings','Inhibit Input')
        self.heartbeatLed = self.wiringcfg.get('Common Settings','Heartbeat LED')
        
    def configureTemperatureInputs(self):
        '''
        Configure the temperature inputs for the detector and vent temp
        '''
        thermoNamesList = []
        rtdNamesList = []
        thermoTypesList = []
        rtdTypesList = []
        for detector in  self.detectorList:
            thermoNamesList.append(self.detectorTempDict[detector])
            rtdNamesList.append(self.valveTempDict[detector])
            thermoTypesList.append(self.valveTempTypeDict[detector]) #valves use thermocouples to read temperature
            rtdTypesList.append(self.detectorTempTypeDict[detector]) #detectors use rtds to read inputs
        self.configureRTDRegisters(rtdTypesList, rtdNamesList)
        self.configureThermocoupleRegisters(thermoTypesList,thermoNamesList)
        
        
    def configureThermocoupleRegisters(self,configurations,names):
        '''
        Set extended features for the analog inputs
        :configuration: - configuration type for the specified channel, string of configuration type will be converted to index number
        :names: - channel to set configration
        '''
        
#         ljm.eWriteName(self.controller,EF_name,index)
        for (name,configuration) in zip(names,configurations):
            index = self.extendedFeaturesIndex[configuration]
            EF_name = name+'_EF_INDEX'
            CONFIG_B_Name = name+'_EF_CONFIG_B'
            CONFIG_D_Name = name+'_EF_CONFIG_D'
            CONFIG_E_Name = name+'_EF_CONFIG_E'
            setting_names = [EF_name,CONFIG_B_Name,CONFIG_D_Name,CONFIG_E_Name]
            setting_values = [index,0,55.56,255.37]
            ljm.eWriteNames(self.controller, 4, setting_names, setting_values)
#             ljm.eWriteName(self.controller, name, index)
            
    def configureRTDRegisters(self,configurations,names):
        '''
        Set the configuration registers for the rtd inputs
        :configurations: - type of rtds to configure
        :names:- names of analog inuputs that will be used
        '''
        for (name,configuration) in zip(names,configurations):
            EF_name = name+'_EF_INDEX'
            CONFIG_A_Name = name+'_EF_CONFIG_A'
            CONFIG_B_Name = name+'_EF_CONFIG_B'
            CONFIG_D_Name = name+'_EF_CONFIG_D'
            CONFIG_E_Name = name+'_EF_CONFIG_E'
            index = self.extendedFeaturesIndex[configuration]
            setting_names =  [EF_name,CONFIG_A_Name,CONFIG_B_Name,CONFIG_D_Name,CONFIG_E_Name]
            setting_values = [index,   2,               0,         55.56,           255.7]
            ljm.eWriteNames(self.controller, 5, setting_names, setting_values)
            
            
    def readValveTemps(self,detectorList):
        '''
        Read the valve temperatures from the list
        :detectorList: - list of string detector names whose temperatures will be read from the labjack
        '''
        names = []
        for detector in detectorList:
            names.append(self.valveTempDict[detector]) #build the list of port names for the requested temperature
        names_readA = map(lambda x: x+'_EF_READ_A', names) #adjust the name to read with the EF options
        stringTemps = self._LJReadValues(names_readA) #return the values
        return map(lambda x: float(x),stringTemps) #conver to list of floats
        
    def readDetectorTemps(self,detectorList):
        '''
        Read the detector temperatures from the list
        :detectorList: - list of string detector names whose temperatures will be read from the labjack
        '''
        names = []
        for detector in detectorList:
            names.append(self.detectorTempDict[detector]) #build the list of port names for the requested temperature
        return self._LJReadValues(names) #return the values
            
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
        return self._LJWriteValues(names,values) #return the values  
    
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
            if value ==True: #convert to On Off to 1,0
                values.append(1)
            elif value == False:
                values.append(0)
        return self._LJWriteValues(names,values) #return the values  
    
    def writeErrorState(self,state):
        '''
        Turn the error led on or off
        :state: - state to set the led
        '''   
        self._LJWriteSingleState(self.errorLed, state)
        
    def writeInhibitState(self,state):
        '''
        wite the state to the inhibit led
        :state: state to ste the inhibit let to, bool
        '''
        self._LJWriteSingleState(self.inhibitLed, state)
        
    def readInhibitState(self):
        '''
        Read the inhibit input 
        '''
        self._LJReadValues(names)
        
    def heartbeatFlash(self):
        '''
        Flash the hearbeat light
        '''
        self.writeHeartbeatState(True)
        sleep(.1)
        self.writeHeartbeatState(False)
        sleep(.1)
        self.writeHeartbeatState(True)
        sleep(.1)
        self.writeHeartbeatState(False)
      
        
    def writeHeartbeatState(self,state):
        '''
        Write the state of the heartbeat led, ie on or off
        :state: state to set the heartbeat status to
        '''
        self._LJWriteSingleState(self.heartbeatLed, state)
        
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
        self._LJWriteValues([name], [value])
                             
                             
    def _LJWriteValues(self,names,values):
        '''
        :names: - list of LJ channels names to write to
        :values: -list of values to write to the channels
        '''
        numFrames = len(names)
#         self.EventLog.debug()
        ljm.eWriteNames(self.controller, numFrames, names, values)
#         print 'E',errorAddress
#         if not errorAddress:
#             msg = 'Problem with writing to address %f'%errorAddress
#             print msg
#             return None
#         return True
    
    def _LJReadValues(self,names):
        '''
        :names: - list of LJ channels names to read from
        '''
        numFrames = len(names)
#         returnValues = [float]*numFrames
        values = ljm.eReadNames(self.controller, numFrames,names)
#         if not errorAddress:
#             msg = 'Problem with reading data from address %f'
#             print msg
#             return None
#         else:
        return values
    def _LJReadValue(self,name):
        value = ljm.eReadName(self.controller,name)
        return value
    
    
        
#     def writeCJCConfiguration(self):
#         '''
#         Write the configuration for the Cold Junction Compencation 
#         '''
        
        