import cam_func_module as cam_func
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import sys
import time
import datetime
from scipy.optimize import curve_fit
from PIL import Image
import os

# The class represents a "worker" collecting and plotting pictures
# It's necessary to be defined because the process will be ongoing in the background thread (see QThread)
class Img_Grab(QObject):

    finished = pyqtSignal()
    img_grab_and_plot_signal = pyqtSignal()
    header_to_save_signal = pyqtSignal()
    n_pict_save = 1
    to_save_flag = False
    
    def __init__(self, parent = None):
        QObject.__init__(self, parent=parent)
        self.continue_run = True

    def do_work(self):
        print('Image grabbing has started...')
        if self.to_save_flag == False:
            while (self.continue_run):
                self.img_grab_and_plot_signal.emit()
                time.sleep(1)
        else:
            self.header_to_save_signal.emit()
            for i in range(self.n_pict_save):
                self.img_grab_and_plot_signal.emit()
                time.sleep(1)
        print('Image grabbing has finished\n')
        self.finished.emit()

    def stop(self):
        self.continue_run = False

    ''' END OF THE CLASS DEFINITION '''
    

class main_window(QWidget):

    camera = None           # camera class
    pict = None             # collected picture
    bg_pict = None               # BG picture
    folder_to_save = None

    hor_init_fit_par = [0., 1., 0., 0.1] # The parameters will be used for fitting initial guesses
    vrt_init_fit_par = [0., 1., 0., 0.1]

    img_grab_stop_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.cam_con()
        
        self.resize(1100,600)
        self.centerscreen()
        self.setWindowTitle('Pictures Aquisition')

        # Main plot
        self.figure = PlotCanvas(self, width=10, height=3.4, dpi=100)

        # Connection with the camera
        self.CamConBtn = QPushButton('Connect camera', self)
        self.CamConBtn.setToolTip('Press to connect the camera')

        # Getting of a picture from the camera
        self.PictAqBtn = QPushButton('One picture', self)
        self.PictAqBtn.setToolTip('Press to get a picture')
        self.PictAqBtn.clicked.connect(self.pict_aq)
        self.PictAqBtn.clicked.connect(self.save_header)

        # Getting of a BG picture
        self.BgPictAqBtn = QPushButton('BG picture', self)
        self.BgPictAqBtn.setToolTip('To collect BG picture')
        self.BgPictAqBtn.clicked.connect(self.bg_pict_aq)
        
        # Exposure time Line Edit
        self.ExpTimeLnEd = QLineEdit(str(self.camera.ExposureTimeAbs.GetValue()))
        self.ExpTimeLnEd.setFixedWidth(100)
        self.ExpTimeLnEd.editingFinished.connect(self.exp_time)
        self.ExpTimeLnEd.setAlignment(Qt.AlignCenter)
        self.ExpTimeLbl = QLabel('Exposure time', self)

        # Gain Line Edit
        self.GainLnEd = QLineEdit(str(self.camera.GainRaw.GetValue()))
        self.GainLnEd.setFixedWidth(100)
        self.GainLnEd.editingFinished.connect(self.gain)
        self.GainLnEd.setAlignment(Qt.AlignCenter)
        self.GainLbl = QLabel('Gain', self)

        # File to save name
        self.FolderLnEd = QLineEdit('data')
        self.FolderLnEd.setFixedWidth(200)
        self.FolderLnEd.editingFinished.connect(self.folder_name)
        self.FolderLnEd.setToolTip('Enter folder name for pictures saving')
        self.FolderChBox = QCheckBox('save data to the folder - ')
        self.FolderChBox.stateChanged.connect(self.worker_to_save_flag)

        # Number of picture to save
        self.NPictSaveLnEd = QLineEdit('1')
        self.NPictSaveLnEd.setValidator(QtGui.QIntValidator(1,1000))
        self.NPictSaveLnEd.editingFinished.connect(self.n_pict_to_save)
        self.NPictSaveLnEd.setFixedWidth(100)
        self.NPictSaveLnEd.setAlignment(Qt.AlignCenter)
        self.NPictSaveLnEd.setToolTip('from 1 to 1000')
        self.NPictSaveLbl = QLabel('Number of pictures to save')

        # CheckBox to fit
        self.FitChBox = QCheckBox('To fit the data')
        # Hor Parameters to fit
        self.HorFitParLbl = QLabel('Hor. fit parameters')
        self.PlotInitHorParChBox = QCheckBox('To plot it?')
        self.HorFitParLnEd = QLineEdit(str(self.hor_init_fit_par[0]) + ',' + str(self.hor_init_fit_par[1]) + ',' + str(self.hor_init_fit_par[2]) + ',' + str(self.hor_init_fit_par[3]))
        self.HorFitParLnEd.editingFinished.connect(self.hor_init_fit_set)
        self.HorFitParLnEd.setToolTip('There must be 4 numbers separated by coma')
        self.HorFitParLnEd.setFixedWidth(100)
        self.HorFitParHBox = QHBoxLayout()
        self.HorFitParHBox.addWidget(self.HorFitParLbl, alignment=Qt.AlignRight)
        self.HorFitParHBox.addWidget(self.HorFitParLnEd, alignment=Qt.AlignCenter)
        self.HorFitParHBox.addWidget(self.PlotInitHorParChBox, alignment=Qt.AlignLeft)
        # Vrt Parameter to fit
        self.VrtFitParLbl = QLabel('Vrt. fit parameters')
        self.PlotInitVrtParChBox = QCheckBox('To plot it?')
        self.VrtFitParLnEd = QLineEdit(str(self.vrt_init_fit_par[0]) + ',' + str(self.vrt_init_fit_par[1]) + ',' + str(self.vrt_init_fit_par[2]) + ',' + str(self.vrt_init_fit_par[3]))
        self.VrtFitParLnEd.editingFinished.connect(self.vrt_init_fit_set)
        self.VrtFitParLnEd.setToolTip('There must be 4 numbers separated by coma')
        self.VrtFitParLnEd.setFixedWidth(100)
        self.VrtFitParHBox = QHBoxLayout()
        self.VrtFitParHBox.addWidget(self.VrtFitParLbl, alignment=Qt.AlignRight)
        self.VrtFitParHBox.addWidget(self.VrtFitParLnEd, alignment=Qt.AlignCenter)
        self.VrtFitParHBox.addWidget(self.PlotInitVrtParChBox, alignment=Qt.AlignLeft)


        ################################ Conteneous image grabbing ################
        # Start Image grabbing Button
        self.StartImgGrabBtn = QPushButton('Start Image grabbing', self)
        self.StartImgGrabBtn.setToolTip('Press to initiate image grabbing')
        # Connection to FUNC is in the self.new_thread()

        # Stop Image grabbing Button
        self.StopImgGrabBtn = QPushButton('Stop Image grabbing', self)
        self.StopImgGrabBtn.setToolTip('Press to stop image grabbing')
        # Connection to FUNC is in the self.new_thread()

        # Thread for contineous image grabbing declaration
        # It's done via function because every time we're stopping "image grabbing"...
        # ...we have to kill this thread and start a new one.
        self.new_thread()
        ################################ Conteneous image grabbing ################

        
        
        # Here we're defining the main grid which will contain all the buttons, plots and so on
        self.grid = QGridLayout()
        self.grid.setSpacing(15)
        self.grid.addWidget(self.figure,        0,0,1,5)
        self.grid.addWidget(self.CamConBtn,     1,0,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.PictAqBtn,     2,0,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.BgPictAqBtn,   3,0,1,1,alignment=Qt.AlignCenter)
        
        self.grid.addWidget(self.StartImgGrabBtn,   1,1,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.StopImgGrabBtn,    2,1,1,1,alignment=Qt.AlignCenter)

        self.grid.addWidget(self.ExpTimeLbl,    1,3,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.ExpTimeLnEd,   1,4,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.GainLbl,       2,3,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.GainLnEd,      2,4,1,1,alignment=Qt.AlignCenter)

        self.grid.addWidget(self.FolderChBox,   4,3,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.FolderLnEd,    4,4,1,1,alignment=Qt.AlignCenter)

        self.grid.addWidget(self.NPictSaveLbl,  5,3,1,1,alignment=Qt.AlignCenter)
        self.grid.addWidget(self.NPictSaveLnEd, 5,4,1,1,alignment=Qt.AlignCenter)

        self.grid.addWidget(self.FitChBox,      3,1,1,1,alignment=Qt.AlignCenter)

        self.grid.addLayout(self.HorFitParHBox, 4,0,1,3)
        self.grid.addLayout(self.VrtFitParHBox, 5,0,1,3)

        self.setLayout(self.grid)

        self.error_dialog = QMessageBox()
        self.error_dialog.setIcon(QMessageBox.Critical)
        
        self.show()

    # Function for a Thread creation
    # The thread is needed for image grabbing in the "background mode"
    def new_thread(self):

        self.img_grab_thread = QThread()
        self.img_grab_worker = Img_Grab()
        self.img_grab_stop_signal.connect(self.img_grab_worker.stop)
        self.img_grab_worker.moveToThread(self.img_grab_thread)
        self.img_grab_worker.n_pict_save = int(self.NPictSaveLnEd.text())
        self.img_grab_worker.to_save_flag = self.FolderChBox.isChecked()

        self.img_grab_thread.started.connect(self.img_grab_worker.do_work)
        self.img_grab_thread.finished.connect(self.img_grab_worker.stop)

        self.StartImgGrabBtn.clicked.connect(self.img_grab_thread.start)
        self.StopImgGrabBtn.clicked.connect(self.img_grab_stop_signal.emit)

        self.img_grab_worker.img_grab_and_plot_signal.connect(self.pict_aq)
        self.img_grab_worker.header_to_save_signal.connect(self.save_header)
        self.img_grab_worker.finished.connect(self.img_grab_thread.quit)
        self.img_grab_worker.finished.connect(self.img_grab_worker.deleteLater)
        self.img_grab_thread.finished.connect(self.img_grab_thread.deleteLater)
        self.img_grab_thread.finished.connect(self.new_thread)
    

#######################################################
#######################################################
        # END of THE WINDOWS DEFINITION





    
    def cam_con(self):
        if self.camera != None:
            self.camera.Close()
        self.camera = cam_func.cam_con()

    
    def pict_aq(self):
        self.pict = cam_func.pict_aq(self.camera)
        self.figure.plot(pointer=self)

        if self.FolderChBox.isChecked() == True:
            self.folder_to_save = self.FolderLnEd.text()
            img = Image.fromarray(self.pict)
            if self.folder_to_save == None:
                path = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + '.png'
                img.save(path)
            else:
                filename = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + '.png'
                path = os.getcwd() + '\\' + self.folder_to_save
                if not os.path.isdir(path):
                    os.mkdir(path)
                img.save(path + '\\' + filename)


    def save_header(self):
        self.folder_to_save = self.FolderLnEd.text()
        if self.folder_to_save == None:
            path = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + '_header.txt'
        else:
            filename = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + '_header.txt'
            path = os.getcwd() + '\\' + self.folder_to_save
            if not os.path.isdir(path):
                os.mkdir(path)
            path = path + '\\' + filename
        file = open(path, 'w')
        file.write('Device - ' + self.camera.GetDeviceInfo().GetModelName() + '\n')
        file.write('Exp time - ' + str(self.camera.ExposureTimeAbs.GetValue()) + '\n')
        file.write('Gain - ' + str(self.camera.GainRaw.GetValue()) + '\n')
        file.write('Temperature - ' + str(self.camera.TemperatureAbs.GetValue()) + '\n')
        file.close()
        time.sleep(0.5)
        

    

    def bg_pict_aq(self):
        self.bg_pict = cam_func.pict_aq(self.camera)
        for i in range(9):
            self.bg_pict = self.bg_pict + cam_func.pict_aq(self.camera)
            time.sleep(0.1)
        self.bg_pict = self.bg_pict / 10

            
    # Changing exposure time
    def exp_time(self):
        cam_func.exp_time(self.camera, float(self.ExpTimeLnEd.text()))


    # Changing Gain
    def gain(self):
        cam_func.gain(self.camera, float(self.GainLnEd.text()))


    # Changing name of the folder pictures to be saved
    def folder_name(self):
        self.folder_to_save = self.FolderLnEd.text()
        if self.folder_to_save == '':
            self.folder_to_save = None


    # Chnging number of pictures to be saved
    def n_pict_to_save(self):
        self.img_grab_worker.n_pict_save = int(self.NPictSaveLnEd.text())


    def worker_to_save_flag(self):
        self.img_grab_worker.to_save_flag = self.FolderChBox.isChecked()


    def hor_init_fit_set(self):
        aaa = self.HorFitParLnEd.text()
        aaa = aaa.split(',')
        if len(aaa) != 4:
            self.error_dialog.setText('Please enter 4 numbers separeted by coma')
            self.error_dialog.exec_()
            self.HorFitParLnEd.setText('1,2,3,4')
        else:
            for i in range(4):
                self.hor_init_fit_par[i] = float(aaa[i])

    
    def vrt_init_fit_set(self):
        aaa = self.VrtFitParLnEd.text()
        aaa = aaa.split(',')
        if len(aaa) != 4:
            self.error_dialog.setText('Please enter 4 numbers separeted by coma')
            self.error_dialog.exec_()
            self.VrtFitParLnEd.setText('1,2,3,4')
        else:
            for i in range(4):
                self.vrt_init_fit_par[i] = float(aaa[i])
            
    
    def centerscreen(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None, width=6.4, height=3.4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.axes1 = fig.add_subplot(131)
        self.axes1.set_aspect(aspect=1)
        self.axes2 = fig.add_subplot(132)
        self.axes2.set_aspect(aspect=1)
        self.axes3 = fig.add_subplot(133)
        self.axes3.set_aspect(aspect=1)

        fig.tight_layout() # For spacing between the subplots

    
    def plot(self, pointer):

        img = pointer.pict
        if not (np.sum(pointer.bg_pict == None)):
            img = img - pointer.bg_pict
        
        img_height = np.size(img,0)
        img_width = np.size(img,1)

        hor_proj = np.sum(img,0)/img_height - np.min(np.sum(img,0)/img_height)
        vrt_proj = np.sum(img,1)/img_width - np.min(np.sum(img,0)/img_height)

        xdata = np.linspace(-1,1,len(hor_proj))
        ydata = np.linspace(-1,1,len(vrt_proj))

        # Here we check if fitting is required and fit the data in case it's required
        #if to_fit == True:
        if pointer.FitChBox.isChecked():
            print('Fitting...')
            def gaus(x, bg, Amp, mu, sigma):
                return bg + Amp * np.exp(- (x - mu)**2 / (2 * sigma**2))

            pointer.hor_init_fit_par[1] = np.max(hor_proj)
            pointer.vrt_init_fit_par[1] = np.max(vrt_proj)
            hor_opt, hor_cov = curve_fit(gaus, xdata, hor_proj, pointer.hor_init_fit_par)
            vrt_opt, vrt_cov = curve_fit(gaus, ydata, vrt_proj, pointer.hor_init_fit_par)
            print('    DONE')
        
        self.axes1.clear()
        self.axes1.imshow(img)
        self.axes1.set_aspect(aspect=img_width/img_height)
        self.axes1.set_ylabel('Y, [pixels]')
        self.axes1.set_xlabel('X, [pixels]')

        self.axes2.clear()
        self.axes2.plot(xdata, hor_proj)
        if pointer.FitChBox.isChecked():
            self.axes2.plot(xdata, gaus(xdata, *hor_opt))
        if pointer.PlotInitHorParChBox.isChecked():
            self.axes2.plot(xdata, gaus(xdata, *pointer.hor_init_fit_par))
        self.axes2.set_aspect(aspect=2/np.max(hor_proj))
        self.axes2.grid(True)
        self.axes2.set_title('X proj.')
        self.axes2.set_xlabel('X, [pixels]')

        self.axes3.clear()
        self.axes3.plot(ydata, vrt_proj)
        if pointer.FitChBox.isChecked():
            self.axes3.plot(ydata, gaus(ydata, *vrt_opt))
        if pointer.PlotInitVrtParChBox.isChecked():
            self.axes3.plot(ydata, gaus(ydata, *pointer.vrt_init_fit_par))
        self.axes3.set_aspect(aspect=2/np.max(vrt_proj))
        self.axes3.grid(True)
        self.axes3.set_title('Y proj.')
        self.axes3.set_xlabel('Y, [pixels]')
        
        self.draw()

    

    
if __name__== '__main__':

    app = QApplication(sys.argv)
    main_wndw = main_window()
        
    sys.exit(app.exec_())
