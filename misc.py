from PIL import Image
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rcParams
import matplotlib.pyplot as plt
import numpy as np
import time
import sys

# Limited list for Sigma_x, Sigma_y and total intensity
class lim_list(object):

    def __init__(self, max_sz=300):
        self.lst = []
        self.max_sz = max_sz

    def add(self, num):
        if len(self.lst) < self.max_sz:
            self.lst.append(num)
        else:
            self.lst.pop(0)
            self.lst.append(num)

    def last_el(self):
        return(self.lst[-1])

    def size_ch(self, max_sz):
        self.max_sz = max_sz








##### The two classes below define additional window where total intesity numbers would be plot#################
        
class tot_int_window(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Total Intensity on Time')

        self.figure = TotIntPlotCanvas(self)

        self.grid = QGridLayout()
        self.grid.addWidget(self.figure,   0,0,1,1)

        self.setLayout(self.grid)
        
        self.show()

class TotIntPlotCanvas(FigureCanvas):

    def __init__(self, parent=None):

        fig = Figure(figsize=(5, 4), dpi=100)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        #rcParams.update({'figure.autolayout':True})
        
        self.axes1 = fig.add_subplot(111)
        self.axes1.set_title('Picture total intensity')
        self.axes1.set_xlabel('Measurement #')

        fig.tight_layout() # For spacing between the subplots

    
    def plot(self, tot_int):

        self.axes1.clear()
        self.axes1.plot(tot_int)
        self.axes1.set_title('Picture total intensity')
        self.axes1.set_xlabel('Measurement #')
        self.axes1.grid(True)
        
        self.draw()

#############################################################################################################













##### The two classes below define additional window where total intesity numbers would be plot#################
        
class sigmas_window(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Sigmas on Time')

        self.figure = SigmasPlotCanvas(self)

        self.grid = QGridLayout()
        self.grid.addWidget(self.figure,   0,0,1,1)

        self.setLayout(self.grid)
        
        self.show()

class SigmasPlotCanvas(FigureCanvas):

    def __init__(self, parent=None):

        fig = Figure(figsize=(8, 4), dpi=100)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        #rcParams.update({'figure.autolayout':True})
        
        self.axes1 = fig.add_subplot(121)
        self.axes1.set_title('Sigma_X')
        self.axes1.set_xlabel('Measurement #')

        self.axes2 = fig.add_subplot(122)
        self.axes2.set_title('Sigma_Y')
        self.axes2.set_xlabel('Measurement #')


        fig.tight_layout() # For spacing between the subplots

    
    def plot(self, sigma_x, sigma_y):

        self.axes1.clear()
        self.axes1.plot(sigma_x)
        self.axes1.set_title('Sigma_x')
        self.axes1.set_xlabel('Measurement #')
        self.axes1.grid(True)

        self.axes2.clear()
        self.axes2.plot(sigma_y)
        self.axes2.set_title('Sigma_y')
        self.axes2.set_xlabel('Measurement #')
        self.axes2.grid(True)
        
        self.draw()

#############################################################################################################

















    
