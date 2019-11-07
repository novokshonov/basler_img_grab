import cam_func_module as cam_func
import misc
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rcParams
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


class main_window(QMainWindow):

    def __init__(self, parent=None):
        super(main_window, self).__init__(parent)
        self.main_widget = main_widget(self)
        self.setWindowTitle('Pictures Aquisition')
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.resize(1200,700)
        centerPoint = QDesktopWidget().availableGeometry().center()
        self.move(centerPoint-QPoint(1200/2,700/2))
        self.setCentralWidget(self.main_widget)
        self.show()


class main_widget(QWidget):

    camera = None           # camera class
    pict = None             # collected picture
    bg_pict = None          # BG picture
    folder_to_save = None   # Folder to save the data
    replot_flag = False     # The flag is needed when no new measurement done but just replot initiated. In this case no new numbers will will recorded (like sigmas for instance). See img_replot function

    hor_fit_par = [0., 3000., 1000., 30] # The parameters will be used for fitting initial guesses
    vrt_fit_par = [0., 3000., 820., 20]

    tot_int = misc.lim_list()
    sigma_x = misc.lim_list()
    sigma_y = misc.lim_list()

    hor_range = [0, 100]
    vrt_range = [0, 100]

    img_grab_stop_signal = pyqtSignal()
    
    def __init__(self, parent):
        super(main_widget, self).__init__(parent)
        self.initUI()

    def initUI(self):

        # Main plot
        self.figure = PlotCanvas(self, width=10, height=4.4, dpi=100)


        
        # Connection with the camera
        self.CamConBtn = QPushButton('Connect camera', self)
        self.CamConBtn.setToolTip('Press to connect the camera')
        self.CamConBtn.clicked.connect(self.cam_con)

        # Getting of a picture from the camera
        self.PictAqBtn = QPushButton('One picture', self)
        self.PictAqBtn.setToolTip('Press to get a picture')
        self.PictAqBtn.clicked.connect(self.pict_aq)
        self.PictAqBtn.clicked.connect(self.save_header)

        # Getting of a BG picture
        self.BgPictAqBtn = QPushButton('BG picture', self)
        self.BgPictAqBtn.setToolTip('To collect BG picture')
        self.BgPictAqBtn.clicked.connect(self.bg_pict_aq)

        # BG subtract CheckBox
        self.BgSubtrChBox = QCheckBox('- BG to subtract')
        self.BgSubtrChBox.setChecked(True)
        self.BgSubtrChBox.stateChanged.connect(self.img_replot)

        # Total intensity to_plot check box
        self.TotIntPlotChBox = QCheckBox('- To plot tot. int.?')
        self.TotIntPlotChBox.setChecked(False)
        self.TotIntPlotChBox.stateChanged.connect(self.img_replot)

        # Total intensity to_plot check box
        self.SigmasPlotChBox = QCheckBox('- To plot sigmas?')
        self.SigmasPlotChBox.setChecked(False)
        self.SigmasPlotChBox.stateChanged.connect(self.img_replot)




        
        # Exposure time Line Edit
        self.ExpTimeLnEd = QLineEdit(alignment=Qt.AlignCenter)
        self.ExpTimeLnEd.editingFinished.connect(self.exp_time)

        # Gain Line Edit
        self.GainLnEd = QLineEdit(alignment=Qt.AlignCenter)
        self.GainLnEd.editingFinished.connect(self.gain)

        # Camera Pixel Mode (Mono12 or Mono8)
        self.PixelFormatComBox = QComboBox()
        self.PixelFormatComBox.addItems(['Mono12', 'Mono8'])
        self.PixelFormatComBox.currentIndexChanged.connect(self.pixel_format)




        # Plot scale
        self.PlotScaleComBox = QComboBox()
        self.PlotScaleComBox.addItems(['Greys', 'jet', 'seismic'])
        self.PlotScaleComBox.currentIndexChanged.connect(self.img_replot)

        # Plot hor range
        self.HorLeftSldr = QSlider(Qt.Horizontal, self)
        self.HorLeftSldr.setTickPosition(QSlider.TicksAbove)
        self.HorLeftSldr.sliderReleased.connect(self.rng_sld)
        self.HorRightSldr = QSlider(Qt.Horizontal)
        self.HorRightSldr.setTickPosition(QSlider.TicksAbove)
        self.HorRightSldr.sliderReleased.connect(self.rng_sld)

        # Plot vrt range
        self.VrtTopSldr = QSlider(Qt.Horizontal)
        self.VrtTopSldr.setTickPosition(QSlider.TicksAbove)
        self.VrtTopSldr.sliderReleased.connect(self.rng_sld)
        self.VrtBottomSldr = QSlider(Qt.Horizontal)
        self.VrtBottomSldr.setTickPosition(QSlider.TicksAbove)
        self.VrtBottomSldr.sliderReleased.connect(self.rng_sld)

        # Text window for range
        self.HorRangeLeft = QLineEdit('0', alignment=Qt.AlignCenter)
        self.HorRangeLeft.editingFinished.connect(self.rng_lines)
        self.HorRangeRight = QLineEdit('100', alignment=Qt.AlignCenter)
        self.HorRangeRight.editingFinished.connect(self.rng_lines)
        self.VrtRangeTop = QLineEdit('0', alignment=Qt.AlignCenter)
        self.VrtRangeTop.editingFinished.connect(self.rng_lines)
        self.VrtRangeBottom = QLineEdit('100', alignment=Qt.AlignCenter)
        self.VrtRangeBottom.editingFinished.connect(self.rng_lines)
        



        # File to save name
        self.FolderLnEd = QLineEdit('data', alignment=Qt.AlignCenter)
        self.FolderLnEd.editingFinished.connect(self.folder_name)
        self.FolderLnEd.setToolTip('Enter folder name for pictures saving')
        self.FolderChBox = QCheckBox('save data to the folder - ')
        self.FolderChBox.stateChanged.connect(self.worker_to_save_flag)

        # Number of picture to save
        self.NPictSaveLnEd = QLineEdit('1', alignment=Qt.AlignCenter)
        self.NPictSaveLnEd.setValidator(QtGui.QIntValidator(1,1000))
        self.NPictSaveLnEd.editingFinished.connect(self.n_pict_to_save)
        self.NPictSaveLnEd.setToolTip('from 1 to 1000')

        # Format of the pictures
        self.PictureFormatComBox = QComboBox()
        self.PictureFormatComBox.addItems(['.tif', '.png'])
        self.formats = {'.tif' : 'TIFF', \
                        '.png' : 'PNG'}



        

        # CheckBox to fit
        self.FitChBox = QCheckBox('To fit (Gaussian)')
        self.FitChBox.stateChanged.connect(self.img_replot)
        # To fit CUT or WHOLE PROJECTION
        self.CutOrProjComBox = QComboBox()
        self.CutOrProjComBox.addItems(['Cut', 'Whole proj.'])
        self.CutOrProjComBox.currentIndexChanged.connect(self.img_replot)
        self.CutWidthLnEd = QLineEdit('5', alignment=Qt.AlignCenter)
        self.CutWidthLnEd.editingFinished.connect(self.img_replot)
        self.CutWidthLnEd.setValidator(QtGui.QIntValidator(2,20))
        #self.CurOrProjComBox.currentIndexChanged.connect()
        # Hor Parameters to fit
        self.HorFitParLbl = QLabel('Hor. fit. parameters')
        self.HorFitParLbl.setStyleSheet('color: red')
        self.HorFitParLnEd = QLineEdit(str(self.hor_fit_par[0]) + ',' + str(self.hor_fit_par[1]) + ',' + str(self.hor_fit_par[2]) + ',' + str(self.hor_fit_par[3]), alignment=Qt.AlignCenter)
        self.HorFitParLnEd.editingFinished.connect(self.hor_fit_set)
        self.HorFitParLnEd.editingFinished.connect(self.img_replot)
        self.HorFitParLnEd.setToolTip('There must be 4 numbers separated by coma')

        # Vrt Parameter to fit
        self.VrtFitParLbl = QLabel('Vrt. fit. parameters')
        self.VrtFitParLbl.setStyleSheet('color: red')
        self.VrtFitParLnEd = QLineEdit(str(self.vrt_fit_par[0]) + ',' + str(self.vrt_fit_par[1]) + ',' + str(self.vrt_fit_par[2]) + ',' + str(self.vrt_fit_par[3]), alignment=Qt.AlignCenter)
        self.VrtFitParLnEd.editingFinished.connect(self.vrt_fit_set)
        self.VrtFitParLnEd.editingFinished.connect(self.img_replot)
        self.VrtFitParLnEd.setToolTip('There must be 4 numbers separated by coma')

        # Show max position or not
        self.MaxPosChBox = QCheckBox('Show max pos.?')
        self.MaxPosChBox.stateChanged.connect(self.img_replot)

        # Paramter for pixel to um convertion
        self.ConvertLnEd = QLineEdit('1', alignment=Qt.AlignCenter)




        # Dialog window
        self.MainMsgBox = QTextEdit()
        self.MainMsgBox.setReadOnly(True)
        self.MainMsgBox.setText('Hi!')
        
        


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





        ######## Defining groups for buttons
        # Group for main camera functions
        self.GroupMain = QGroupBox('Main functions')
        self.vboxGroupMain = QVBoxLayout()
        self.vboxGroupMain.addWidget(self.CamConBtn)
        self.vboxGroupMain.addWidget(self.PictAqBtn)
        self.vboxGroupMain.addWidget(self.BgPictAqBtn)
        self.vboxGroupMain.addWidget(self.BgSubtrChBox)
        self.vboxGroupMain.addWidget(self.StartImgGrabBtn)
        self.vboxGroupMain.addWidget(self.StopImgGrabBtn)
        self.vboxGroupMain.addWidget(self.TotIntPlotChBox)
        self.vboxGroupMain.addWidget(self.SigmasPlotChBox)
        self.vboxGroupMain.addStretch(1)
        self.GroupMain.setLayout(self.vboxGroupMain)

        # Group for Plot Settings
        self.GroupPltSet = QGroupBox('Plot settings')
        self.GridGroupPltSet = QGridLayout()
        self.GridGroupPltSet.addWidget(self.PlotScaleComBox,    0,0,1,4)
        self.GridGroupPltSet.addWidget(QLabel('ROI'),           1,0,1,4)
        self.GridGroupPltSet.addWidget(self.HorLeftSldr,        2,0,1,4)
        self.GridGroupPltSet.addWidget(self.HorRightSldr,       3,0,1,4)
        self.GridGroupPltSet.addWidget(self.VrtTopSldr,         4,0,1,4)
        self.GridGroupPltSet.addWidget(self.VrtBottomSldr,      5,0,1,4)
        self.GridGroupPltSet.addWidget(QLabel('Hor. range:'),   6,0,1,1)
        self.GridGroupPltSet.addWidget(self.HorRangeLeft,       6,1,1,1)
        self.GridGroupPltSet.addWidget(QLabel(' to '),          6,2,1,1)
        self.GridGroupPltSet.addWidget(self.HorRangeRight,      6,3,1,1)
        self.GridGroupPltSet.addWidget(QLabel('Vrt. range:'),   7,0,1,1)
        self.GridGroupPltSet.addWidget(self.VrtRangeTop,        7,1,1,1)
        self.GridGroupPltSet.addWidget(QLabel(' to '),          7,2,1,1)
        self.GridGroupPltSet.addWidget(self.VrtRangeBottom,     7,3,1,1)
        self.GroupPltSet.setLayout(self.GridGroupPltSet)
        
        # Group for Camera Settings
        self.GroupCamSet = QGroupBox('Camera settings')
        self.vboxGroupCamSet = QVBoxLayout()
        self.vboxGroupCamSet.addWidget(QLabel('Exposure time:'))
        self.vboxGroupCamSet.addWidget(self.ExpTimeLnEd)
        self.vboxGroupCamSet.addWidget(QLabel('Gain:'))
        self.vboxGroupCamSet.addWidget(self.GainLnEd)
        self.vboxGroupCamSet.addWidget(QLabel('Pixel format:'))
        self.vboxGroupCamSet.addWidget(self.PixelFormatComBox)
        self.vboxGroupCamSet.addStretch(1)
        self.GroupCamSet.setLayout(self.vboxGroupCamSet)

        # Group for Fitting Paramters
        self.GroupFitPar = QGroupBox('Fitting settings')
        self.GridGroupFitPar = QGridLayout()
        self.GridGroupFitPar.addWidget(self.FitChBox,               0,0,1,2)
        self.GridGroupFitPar.addWidget(self.CutOrProjComBox,        1,0,1,2)
        self.GridGroupFitPar.addWidget(QLabel('Cut half width:'),   2,0,1,1)
        self.GridGroupFitPar.addWidget(self.CutWidthLnEd,           2,1,1,1)
        self.GridGroupFitPar.addWidget(self.HorFitParLbl,           3,0,1,2)
        self.GridGroupFitPar.addWidget(self.HorFitParLnEd,          4,0,1,2)
        self.GridGroupFitPar.addWidget(self.VrtFitParLbl,           5,0,1,2)
        self.GridGroupFitPar.addWidget(self.VrtFitParLnEd,          6,0,1,2)
        self.GridGroupFitPar.addWidget(self.MaxPosChBox,            7,0,1,1)
        self.GridGroupFitPar.addWidget(QLabel('Pix. to um factor'), 8,0,1,1)
        self.GridGroupFitPar.addWidget(self.ConvertLnEd,            8,1,1,1)
        self.GroupFitPar.setLayout(self.GridGroupFitPar)

        # Group for Save Options
        self.GroupSave = QGroupBox('Save parameters')
        self.vboxGroupSave = QVBoxLayout()
        self.vboxGroupSave.addWidget(self.FolderChBox)
        self.vboxGroupSave.addWidget(self.FolderLnEd)
        self.vboxGroupSave.addWidget(QLabel('Number of pictures to save'))
        self.vboxGroupSave.addWidget(self.NPictSaveLnEd)
        self.vboxGroupSave.addWidget(QLabel('Picture format'))
        self.vboxGroupSave.addWidget(self.PictureFormatComBox)
        self.vboxGroupSave.addStretch(1)
        self.GroupSave.setLayout(self.vboxGroupSave)

        # VBox for messages
        self.GroupMsg = QGroupBox('Messages')
        self.vboxMsgGroup = QVBoxLayout()
        self.vboxMsgGroup.addWidget(self.MainMsgBox)
        self.GroupMsg.setLayout(self.vboxMsgGroup)

        
        
        
        # Here we're defining the main grid which will contain all the buttons, plots and so on
        self.grid = QGridLayout()
        self.grid.setSpacing(15)
        self.grid.addWidget(self.figure,        0,0,1,6)

        self.grid.addWidget(self.GroupMain,     1,0,1,1)
        self.grid.addWidget(self.GroupPltSet,   1,1,1,1)
        self.grid.addWidget(self.GroupCamSet,   1,2,1,1)
        self.grid.addWidget(self.GroupFitPar,   1,3,1,1)
        self.grid.addWidget(self.GroupSave,     1,4,1,1)
        self.grid.addWidget(self.GroupMsg,      1,5,1,1)
        
        self.setLayout(self.grid)

        self.error_dialog = QMessageBox()
        self.error_dialog.setIcon(QMessageBox.Critical)



        self.cam_con() # Here we're connecting to the camera
        
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

        try:
            self.camera = cam_func.cam_con()    # connect to the camera
            self.ExpTimeLnEd.setText(str(self.camera.ExposureTimeAbs.GetValue())) # Check Exp time of the camera
            self.GainLnEd.setText(str(self.camera.GainRaw.GetValue()))  # check gain of the camera

            self.HorLeftSldr.setMinimum(0)
            self.HorLeftSldr.setMaximum(self.camera.Width.GetValue())
            self.HorRightSldr.setMinimum(0)
            self.HorRightSldr.setMaximum(self.camera.Width.GetValue())
        
            self.VrtTopSldr.setMinimum(0)
            self.VrtTopSldr.setMaximum(self.camera.Height.GetValue())
            self.VrtBottomSldr.setMinimum(0)
            self.VrtBottomSldr.setMaximum(self.camera.Height.GetValue())

            self.HorLeftSldr.setValue(0)
            self.HorRightSldr.setValue(self.camera.Width.GetValue())
            self.VrtTopSldr.setValue(0)
            self.VrtBottomSldr.setValue(self.camera.Height.GetValue())
            
            self.hor_range[1] = self.camera.Width.GetValue()
            self.vrt_range[1] = self.camera.Height.GetValue()
            
            self.HorRangeLeft.setValidator(QtGui.QIntValidator(0, int(round(self.hor_range[1]))))
            self.HorRangeRight.setValidator(QtGui.QIntValidator(0, int(round(self.hor_range[1]))))
            self.VrtRangeTop.setValidator(QtGui.QIntValidator(0, int(round(self.vrt_range[1]))))
            self.VrtRangeBottom.setValidator(QtGui.QIntValidator(0, int(round(self.vrt_range[1]))))
            
            self.HorRangeLeft.setText(str(self.hor_range[0]))
            self.HorRangeRight.setText(str(self.hor_range[1]))
            self.VrtRangeTop.setText(str(self.vrt_range[0]))
            self.VrtRangeBottom.setText(str(self.vrt_range[1]))

            self.MainMsgBox.setText('Camera connected\nCamera name is ' + str(self.camera.GetDeviceInfo().GetModelName()) + '\n')
        except:
            self.MainMsgBox.setText('It seems there is no camera connected!\n')
            print('It seems there is no camera connected!')

    
    def pict_aq(self):
        self.MainMsgBox.setText('Picture acquisition...')
        no_pict_flag = False
        try:
            self.pict = cam_func.pict_aq(self.camera)
            self.MainMsgBox.append('   Picture acquised.')
        except:
            self.MainMsgBox.append('   Picture WAS NOT acquised!')
            no_pict_flag = True;

        if no_pict_flag == False:
            self.tot_int.add(np.sum(np.sum(self.pict)))
            self.figure.plot(pointer=self)

            self.MainMsgBox.append('   Total intensity = ' + str(self.tot_int.last_el()))

            if self.FolderChBox.isChecked() == True:
                self.folder_to_save = self.FolderLnEd.text()
                img = Image.fromarray(self.pict)
                path = os.getcwd() + '\\' + self.FolderLnEd.text()
                
                if os.path.exists(path) == False:
                    os.mkdir(path)
                img.save(path + '\\' + datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + self.PictureFormatComBox.currentText(), format=self.formats[self.PictureFormatComBox.currentText()])
        


    def save_header(self):
        if self.FolderChBox.isChecked() == True:
            self.folder_to_save = self.FolderLnEd.text()
            filename_header = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + '_header.txt'
            filename_BG = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S') + '_BG' + self.PictureFormatComBox.currentText()
            path = os.getcwd() + '\\' + self.FolderLnEd.text()
                
            if os.path.exists(path) == False:
                os.mkdir(path)

            path_header = path + '\\' + filename_header
            path_BG = path + '\\' + filename_BG

            if self.bg_pict is not None:
                if float(self.GainLnEd.text()) != 0:
                    img_bg = Image.fromarray(self.bg_pict * float(self.GainLnEd.text()) * float(self.ExpTimeLnEd.text()))
                else:
                    img_bg = Image.fromarray(self.bg_pict * float(self.ExpTimeLnEd.text()))
                img_bg.save(path_BG, format=self.formats[self.PictureFormatComBox.currentText()])
                    
            file = open(path_header, 'w')
            file.write('Device - ' + self.camera.GetDeviceInfo().GetModelName() + '\n')
            file.write('Exp time - ' + str(self.camera.ExposureTimeAbs.GetValue()) + '\n')
            file.write('Gain - ' + str(self.camera.GainRaw.GetValue()) + '\n')
            file.write('Temperature - ' + str(self.camera.TemperatureAbs.GetValue()) + '\n')
            if self.BgSubtrChBox.isChecked():
                file.write('BG IS subtracted\n')
            else:
                file.write('BG IS NOT subtracted\n')
            file.close()
            time.sleep(0.5)
        

    

    def bg_pict_aq(self):
        self.MainMsgBox.setText('Getting BG picture...')
        self.bg_pict = cam_func.pict_aq(self.camera)
        for i in range(9):
            self.bg_pict = self.bg_pict + cam_func.pict_aq(self.camera)
            time.sleep(0.1)
        self.bg_pict = self.bg_pict / 10 / float(self.ExpTimeLnEd.text())
        if float(self.GainLnEd.text()) != 0:
            self.bg_pict = self.bg_pict / float(self.GainLnEd.text())
        self.MainMsgBox.append('   BG picture is acquised.\n')
        print('BG picture is acquised! \n')

            
    # Changing exposure time
    def exp_time(self):
        cam_func.exp_time(self.camera, float(self.ExpTimeLnEd.text()))


    # Changing Gain
    def gain(self):
        cam_func.gain(self.camera, float(self.GainLnEd.text()))

    # Changing between Mono8 and Mono12 pixel formats
    def pixel_format(self):
        cam_func.pixel_format(self.camera, self.PixelFormatComBox.currentText())

    def rng_sld(self):
        if (self.HorRightSldr.value() - self.HorLeftSldr.value()) <= (int(self.CutWidthLnEd.text())*2 + 1) or (self.VrtBottomSldr.value() - self.VrtTopSldr.value()) <= (int(self.CutWidthLnEd.text())*2 + 1):
            self.HorLeftSldr.setValue(self.hor_range[0])
            self.HorRightSldr.setValue(self.hor_range[1])
            self.VrtTopSldr.setValue(self.vrt_range[0])
            self.VrtBottomSldr.setValue(self.vrt_range[1])
        else:
            self.hor_range[0] = self.HorLeftSldr.value()
            self.hor_range[1] = self.HorRightSldr.value()
            self.vrt_range[0] = self.VrtTopSldr.value()
            self.vrt_range[1] = self.VrtBottomSldr.value()        
        
            self.HorRangeLeft.setText(str(self.hor_range[0]))
            self.HorRangeRight.setText(str(self.hor_range[1]))
            self.VrtRangeTop.setText(str(self.vrt_range[0]))
            self.VrtRangeBottom.setText(str(self.vrt_range[1]))

            if self.pict is not None:
                self.figure.plot(pointer=self)

    
    def rng_lines(self):
        if (int(self.HorRangeRight.text()) - int(self.HorRangeLeft.text())) <= (int(self.CutWidthLnEd.text())*2 + 1) or (int(self.VrtRangeBottom.text()) - int(self.VrtRangeTop.text())) <= (int(self.CutWidthLnEd.text())*2 + 1):
            self.HorRangeLeft.setText(str(self.hor_range[0]))
            self.HorRangeRight.setText(str(self.hor_range[1]))
            self.VrtRangeTop.setText(str(self.vrt_range[0]))
            self.VrtRangeBottom.setText(str(self.vrt_range[1]))
        else:
            self.hor_range[0] = int(self.HorRangeLeft.text())
            self.hor_range[1] = int(self.HorRangeRight.text())
            self.vrt_range[0] = int(self.VrtRangeTop.text())
            self.vrt_range[1] = int(self.VrtRangeBottom.text())

            self.HorLeftSldr.setValue(self.hor_range[0])
            self.HorRightSldr.setValue(self.hor_range[1])
            self.VrtTopSldr.setValue(self.vrt_range[0])
            self.VrtBottomSldr.setValue(self.vrt_range[1])

            if self.pict is not None:
                self.figure.plot(pointer=self)
    


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


    def hor_fit_set(self):
        aaa = self.HorFitParLnEd.text()
        aaa = aaa.split(',')
        if len(aaa) != 4:
            self.error_dialog.setText('Please enter 4 numbers separeted by coma')
            self.error_dialog.exec_()
            self.HorFitParLnEd.setText('1,2,3,4')
        else:
            for i in range(4):
                self.hor_fit_par[i] = float(aaa[i])

    
    def vrt_fit_set(self):
        aaa = self.VrtFitParLnEd.text()
        aaa = aaa.split(',')
        if len(aaa) != 4:
            self.error_dialog.setText('Please enter 4 numbers separeted by coma')
            self.error_dialog.exec_()
            self.VrtFitParLnEd.setText('1,2,3,4')
        else:
            for i in range(4):
                self.vrt_fit_par[i] = float(aaa[i])
            
    # it sets the application in the center of the screen
    def centerscreen(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # when we change img scale (grey, jet...) it plots the img again
    def img_replot(self):
        self.replot_flag = True
        if self.pict is not None:
            self.figure.plot(pointer=self)
        self.replot_flag = False


class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None, width=6.4, height=6.4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        #rcParams.update({'figure.autolayout':True})
        
        self.axes1 = fig.add_subplot(131)
        self.axes1.set_aspect(aspect=1)
        self.axes1.set_ylabel('Y, [pixels]')
        self.axes1.set_xlabel('X, [pixels]')
        self.axes2 = fig.add_subplot(132)
        self.axes2.set_aspect(aspect=1)
        self.axes2.set_title('X proj.')
        self.axes2.set_xlabel('X, [pixels]')
        self.axes3 = fig.add_subplot(133)
        self.axes3.set_aspect(aspect=1)
        self.axes3.set_title('Y proj.')
        self.axes3.set_xlabel('Y, [pixels]')

        fig.tight_layout() # For spacing between the subplots

    
    def plot(self, pointer):

        img = pointer.pict
        if not (np.sum(pointer.bg_pict == None)) and pointer.BgSubtrChBox.isChecked():
            if float(pointer.GainLnEd.text()) != 0:
                img = img - pointer.bg_pict * float(pointer.ExpTimeLnEd.text()) * float(pointer.GainLnEd.text())
            else:
                img = img - pointer.bg_pict * float(pointer.ExpTimeLnEd.text())
        
        img_height = np.size(img,0)
        img_width = np.size(img,1)
        
        if pointer.CutOrProjComBox.currentText() == 'Cut':
            y_max_pos = np.argmax(np.sum(img,1))
            x_max_pos = np.argmax(np.sum(img,0))
            cut_wdth = int(pointer.CutWidthLnEd.text())

            hor_proj = np.sum(img[y_max_pos-cut_wdth:y_max_pos+cut_wdth, :],0) / (2*cut_wdth + 1)
            vrt_proj = np.sum(img[:, x_max_pos-cut_wdth:x_max_pos+cut_wdth],1) / (2*cut_wdth + 1)
            
            xdata = np.linspace(0,img_width,img_width)
            ydata = np.linspace(0,img_height,img_height)

        else:
            hor_proj = np.sum(img,0)/img_height
            vrt_proj = np.sum(img,1)/img_width

            xdata = np.linspace(0,img_width,img_width)
            ydata = np.linspace(0,img_height,img_height)


        def gaus(x, bg, Amp, mu, sigma):
                return bg + Amp * np.exp(- (x - mu)**2 / (2 * sigma**2))
        
        # Here we check if fitting is required and fit the data in case it's required
        #if to_fit == True:
        if pointer.FitChBox.isChecked():
            print('Fitting...')

            pointer.hor_fit_par[0] = np.min(hor_proj)
            pointer.vrt_fit_par[0] = np.min(vrt_proj)
            pointer.hor_fit_par[1] = np.max(hor_proj)
            pointer.vrt_fit_par[1] = np.max(vrt_proj)
            pointer.hor_fit_par[2] = np.argmax(np.sum(img,0))
            pointer.vrt_fit_par[2] = np.argmax(np.sum(img,1))
            
            pointer.hor_fit_par, hor_cov = curve_fit(gaus, xdata, hor_proj, pointer.hor_fit_par)
            pointer.vrt_fit_par, vrt_cov = curve_fit(gaus, ydata, vrt_proj, pointer.vrt_fit_par)
            pointer.HorFitParLnEd.setText(str(round(pointer.hor_fit_par[0])) + ',' + str(round(pointer.hor_fit_par[1])) + ',' + str(round(pointer.hor_fit_par[2])) + ',' + str(round(pointer.hor_fit_par[3])))
            pointer.VrtFitParLnEd.setText(str(round(pointer.vrt_fit_par[0])) + ',' + str(round(pointer.vrt_fit_par[1])) + ',' + str(round(pointer.vrt_fit_par[2])) + ',' + str(round(pointer.vrt_fit_par[3])))
            if pointer.replot_flag == False:
                pointer.sigma_x.add(pointer.hor_fit_par[3])
                pointer.sigma_y.add(pointer.vrt_fit_par[3])
            else:
                pointer.sigma_x.lst[-1] = pointer.hor_fit_par[3]
                pointer.sigma_y.lst[-1] = pointer.vrt_fit_par[3]
            print('    DONE')
        else:
            if pointer.replot_flag == False:
                pointer.sigma_x.add(0)
                pointer.sigma_y.add(0)

        
        self.axes1.clear()
        self.axes1.imshow(img, cmap=pointer.PlotScaleComBox.currentText())
        #self.axes1.imshow(img[pointer.vrt_range[0]:pointer.vrt_range[1]-1, pointer.hor_range[0]:pointer.hor_range[1]-1], cmap=pointer.PlotScaleComBox.currentText())
        if pointer.MaxPosChBox.isChecked():
            self.axes1.scatter(np.argmax(np.sum(img,0)), np.argmax(np.sum(img,1)), s=10, color='gold')
        self.axes1.set_xlim(pointer.hor_range[0], pointer.hor_range[1]-1)
        self.axes1.set_ylim(pointer.vrt_range[0], pointer.vrt_range[1]-1)
        self.axes1.set_aspect(aspect=(pointer.hor_range[1] - pointer.hor_range[0])/(pointer.vrt_range[1] - pointer.vrt_range[0]))
        self.axes1.set_ylabel('Y, [pixels]')
        self.axes1.set_xlabel('X, [pixels]')

        self.axes2.clear()
        self.axes2.plot(xdata, hor_proj)
        if pointer.FitChBox.isChecked():
            self.axes2.plot(xdata, gaus(xdata, *pointer.hor_fit_par)) # Plotting the fitted data
        self.axes2.set_xlim((xdata[int(pointer.hor_range[0])], xdata[int(pointer.hor_range[1]-1)]))
        if (np.max(hor_proj) - np.min(hor_proj)) != 0:
            self.axes2.set_aspect(aspect= 0.9 * (xdata[int(pointer.hor_range[1]-1)] - xdata[int(pointer.hor_range[0])]) / (np.max(hor_proj) - np.min(hor_proj)))
        else:
            self.axes2.set_aspect(aspect= 0.9 * (xdata[int(pointer.hor_range[1]-1)] - xdata[int(pointer.hor_range[0])]) / 0.1)
        self.axes2.grid(True)
        self.axes2.set_title('X proj.')
        self.axes2.set_xlabel('X, [pixels]')
        if pointer.FitChBox.isChecked():
            if pointer.replot_flag == False:
                pointer.MainMsgBox.append('   Sigma_x = ' + str(round(pointer.sigma_x.last_el(),3)))
        
        self.axes3.clear()
        self.axes3.plot(ydata, vrt_proj)
        if pointer.FitChBox.isChecked():
            self.axes3.plot(ydata, gaus(ydata, *pointer.vrt_fit_par))   # Plotting the fitted data
        self.axes3.set_xlim((ydata[int(pointer.vrt_range[0])], ydata[int(pointer.vrt_range[1]-1)]))
        if (np.max(vrt_proj) - np.min(vrt_proj)) != 0:
            self.axes3.set_aspect(aspect= 0.9 * (ydata[int(pointer.vrt_range[1]-1)] - ydata[int(pointer.vrt_range[0])]) / (np.max(vrt_proj) - np.min(vrt_proj)))
        else:
            self.axes3.set_aspect(aspect= 0.9 * (ydata[int(pointer.vrt_range[1]-1)] - ydata[int(pointer.vrt_range[0])]) / 0.1)
        self.axes3.grid(True)
        self.axes3.set_title('Y proj.')
        self.axes3.set_xlabel('Y, [pixels]')
        if pointer.FitChBox.isChecked():
            if pointer.replot_flag == False:
                pointer.MainMsgBox.append('   Sigma_y = ' + str(round(pointer.sigma_y.last_el(),3)) + '\n')
        
        self.draw()

        # Here we plot total intensity on time in additional window
        if (pointer.TotIntPlotChBox.isChecked() and pointer.pict is not None) or (pointer.SigmasPlotChBox.isChecked() and pointer.pict is not None):
            try:
                pointer.time_plots # Here We check if it exists
                if pointer.time_plots.isVisible() == False: # Here we check if its visible and revoke if not
                    pointer.time_plots.show()
                if pointer.TotIntPlotChBox.isChecked():
                    pointer.time_plots.figure.tot_int_plot(pointer.tot_int.lst)
                if pointer.SigmasPlotChBox.isChecked():
                    pointer.time_plots.figure.sigmas_plot(np.array(pointer.sigma_x.lst) * float(pointer.ConvertLnEd.text()), np.array(pointer.sigma_y.lst) * float(pointer.ConvertLnEd.text()))

            except:
                pointer.time_plots = misc.time_plots_window()
                if pointer.TotIntPlotChBox.isChecked():
                    pointer.time_plots.figure.tot_int_plot(pointer.tot_int.lst)
                if pointer.SigmasPlotChBox.isChecked():
                    pointer.time_plots.figure.sigmas_plot(np.array(pointer.sigma_x.lst) * float(pointer.ConvertLnEd.text()), np.array(pointer.sigma_y.lst) * float(pointer.ConvertLnEd.text()))

        

    

    
if __name__== '__main__':

    app = QApplication(sys.argv)
    main_wndw = main_window()
        
    sys.exit(app.exec_())
