'''
Created on Sep 15, 2016

@author: ADonoghue
'''
import unittest
from AutoFillLabJack import LJC
import ConfigParser


class Test(unittest.TestCase):


    def setUp(self):
        cnfgFile = ConfigParser.RawConfigParser()
        cnfgFile.read('C:\Python\Misc\AutoFillLabJack\PortWiring.cfg')
        self.LJ = LJC.LJControl(cnfgFile)
        
        self.LJ.controllerInit()
        


    def tearDown(self):
        self.LJ.releaseInit()


    def testLJ(self):
#         self.LJ.writeValveState(['Line Chill','Detector 6'], ['On','Off'])
        self.LJ.writeEnableLEDState(['Line Chill','Detector 6'], ['On','Off'])


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testLJ']
    unittest.main()