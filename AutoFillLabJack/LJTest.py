'''
Created on Sep 15, 2016

@author: ADonoghue
'''
import unittest
from AutoFillLabJack import LJC
from AutoFillLabJack.AutoFillInterface import AutoFillInterface
from AutoFillLabJack.AutoFillGUI import AutoFillGUI
import ConfigParser
import time
from datetime import datetime as dt


class Test(unittest.TestCase):


    def setUp(self):
#         cnfgFile = ConfigParser.RawConfigParser()
#         cnfgFile.read('C:\Python\Misc\AutoFillLabJack\PortWiring.cfg')
#         self.LJ = LJC.LJC(cnfgFile)
#         
#         self.LJ.controllerInit()
#         self.interface = AutoFillInterface()
#         self.interface.initController()

        self.GUI = AutoFillGUI()
        self.GUI.initInterface()
        
#     def testLights(self):
#         print self.interface.LJ.readInhibitState()
#         while self.interface.LJ.readInhibitState() == True:
#             for detector in self.interface.detectors:
# #                 print detector
#                 states = [True]
#                 self.interface.writeEnableLEDState([detector], states)      
#                 self.interface.writeValveState([detector], states)    
#                 time.sleep(.4)
#                 states = [False]
#                 self.interface.writeEnableLEDState([detector], states)
#                 self.interface.writeValveState([detector], states)
#             self.interface.writeEnableLEDState(['Line Chill'], [True])
#             self.interface.writeValveState(['Line Chill'], [True])
#             time.sleep(.4)
#             self.interface.writeEnableLEDState(['Line Chill'], [False])
#             self.interface.writeValveState(['Line Chill'], [False])
#             self.interface.LJ.heartbeatFlash()
#             self.interface.writeEnableLEDState(['Line Chill'], [True])
#             time.sleep(.1)
#             self.interface.writeEnableLEDState(['Line Chill'], [False])
#             self.interface.LJ.writeErrorState(True)
#             time.sleep(.1)
#             self.interface.LJ.writeErrorState(False)
#             self.interface.LJ.writeInhibitState(True)
#             time.sleep(.1)
#             self.interface.LJ.writeInhibitState(False)
      
#     def testTemp(self):
#         '''
#         Test the temp
#         '''      
#         time.sleep(2)
#         self.interface.LJ.heartbeatFlash()
#         time.sleep(1)
        
#     def testThread(self):
#         '''
#         Test the run thread
#         '''
#         print 'Schedule',self.interface.detectorConfigDict['Detector 4']['Fill Schedule']
#         while self.interface.LJ.readInhibitState() == True:
#             self.interface.runThread()
#             print 'Vent Temp',self.interface.detectorValuesDict['Detector 4']['Vent Temperature']
#             time.sleep(3)

#     def testConfigWrite(self):
#         print self.interface.readDetectorConfig('Detector 3')
#         self.interface.changeDetectorSetting('Detector 3', 'Name', "Bang 3")
#         self.interface.changeDetectorSetting('Detector 3', 'Fill Timeout', '4')
#         sections,options,values = self.interface.writeDetectorSetting()
#         self.interface._writeCfgFile(sections, options, values)
#         self.interface.loadDetectorConfig()
#         print self.interface.readDetectorConfig('Detector 3')

#     def testGUI(self):
#         '''
#         Test the GUI
#         '''
#         inputStr = '1 enabled False'
#         self.GUI.textInput(inputStr)
#         inputStr = '3 schedule 12:15'
#         self.GUI.textInput(inputStr)
#         inputStr = '3 enabled False'
#         self.GUI.textInput(inputStr)
#         inputStr = '4 enabled False'
#         self.GUI.textInput(inputStr)
#         detectors,settings,values = self.GUI.checkDetectorChanges()
#         self.GUI.writeDetectorChanges(detectors, settings, values)
#         self.GUI.interface.loadDetectorConfig()
#         self.GUI.checkDetectorSettings('1')
#         self.GUI.checkDetectorSettings('3')
#         
     
    def testTheadTempGet(self):
        '''
        Test the main running thread with and getting the detector temperature
        '''   
        print 'Starting Thread!'
        self.GUI.interface.startRunThread()
        print 'Thread Started test!'
        time.sleep(.2)
        self.GUI.detectorTempInput('2')
        time.sleep(.2)
#         self.GUI.detectorTempInput('All')
        time.sleep(10)
        self.GUI.interface.stopRunningEvent.set()
#     def testInhibit(self):
#         i = 0
#         while i < 100000:
#             inhibit = self.interface.LJ.readInhibitState()
#             if inhibit == False:
#                 self.interface.LJ.writeInhibitState(True)
#             elif inhibit == True:
#                 self.interface.LJ.writeInhibitState(False)
#             i+=1

#     def testTemperature(self):
#         '''
#         Test reading the temperature for the 
#         '''
#         i = 0
#         curTime = dt.today()
#         curTimeStr = curTime.strftime('%H:%M')
#         self.interface.detectorConfigDict['Detector 4']['Fill Schedule'] = [curTimeStr]
#         while self.interface.LJ.readInhibitState() == True:
#             self.interface.checkStartDetectorFills()
#             self.interface.readValveTemps()
#             self.interface.checkVentTemp()
#             print self.interface.detectorValuesDict['Detector 4']['Valve Temperature']
#             time.sleep(.1)
#             i+=1
#                 
    def tearDown(self):
        pass
#         self.interface.initRelease()


#     def testLJ(self):
# #         self.LJ.writeValveState(['Line Chill','Detector 6'], ['On','Off'])
#         self.interface.runThread()
# #         self.LJ.writeEnableLEDState(['Line Chill','Detector 6'], ['On','Off'])


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testLJ']
    unittest.main()