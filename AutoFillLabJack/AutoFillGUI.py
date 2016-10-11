'''
Created on Sep 16, 2016

@author: ADonoghue
'''
import curses
import time
class AutoFillGUI():
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
        
    def startWindow(self):
        stdscr = curses.initscr()
        window = stdscr.subwin(23,79,0,0)
        curses.wrapper(window.addstr('Hello Grill!'))
        time.sleep(4)
        curses.endwin()
#         self.window = curses.newwin(5,20,20,7)
#         self.window.keypad(1)
#         self.window.newwin(5,40,20,7)
    
    def addText(self):
        '''
        Add some text to the window
        '''
        self.window.addstr('Hello Grill!')
        time.sleep(3)
        
    def endWindow(self):
        curses.endwin()
        
        
if __name__ == '__main__':
    AutoFillGUI = AutoFillGUI()
    AutoFillGUI.startWindow()
#     AutoFillGUI.addText()
#     AutoFillGUI.endWindow()