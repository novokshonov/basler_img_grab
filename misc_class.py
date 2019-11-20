import numpy as np
import time
from PyQt5.QtCore import QObject, pyqtSignal
import threading







# The class represents a "worker" collecting and plotting pictures
# It's necessary to be defined because the process will be ongoing in the background thread (see QThread)
class Img_Grab(QObject):

    finished = pyqtSignal()
    img_grab_and_plot_signal = pyqtSignal() # the signal initiate picture grabbing
    
    def __init__(self, parent = None):   
        QObject.__init__(self, parent=parent)
        self.continue_run = True

    def do_work(self):
        print('Image grabbing has started...')
        while (self.continue_run):
            print(threading.currentThread().ident)
            self.img_grab_and_plot_signal.emit()
            time.sleep(1)
        
        print('Image grabbing has finished\n')
        self.finished.emit()

    def stop(self):
        self.continue_run = False

    ''' END OF THE CLASS DEFINITION '''



