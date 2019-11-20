import cam_func
import misc_class
import misc_func
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
import numpy as np
import sys
import time
import datetime
from PIL import Image
import os


class main_window(QMainWindow):

    def __init__(self, parent=None):
        super(main_window, self).__init__(parent)
        self.main_widget = main_widget(self)
        self.setWindowTitle('Pictures Aquisition')
        #self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.resize(1600,800)
        centerPoint = QDesktopWidget().availableGeometry().center()
        self.move(centerPoint-QPoint(1600/2,800/2))
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

    number_of_points = 20
    tot_int = []
    sigma_x = []
    sigma_y = []

    hor_range = [0, 100]
    vrt_range = [0, 100]

    img_grab_stop_signal = pyqtSignal()
    
    folder_to_save = os.getcwd() + '\data'
    if os.path.isdir(folder_to_save) == False:
        os.mkdir(folder_to_save)
    
    
    def __init__(self, parent):
        super(main_widget, self).__init__(parent)
        self.initUI()

    def initUI(self):
        
        # Main PLOTS
        self.imageWidget = pg.ImageView(view=pg.PlotItem())
        self.imageWidget.view.setTitle('Image', color=(255,255,0))
        self.imageWidget.view.setLabel('left', 'Y, [um]', color='lawngreen')
        self.imageWidget.view.setLabel('bottom', 'X, [um]', color='lawngreen')
        self.imageWidget.ui.histogram.hide()
        self.imageWidget.ui.roiBtn.hide()
        self.imageWidget.ui.menuBtn.hide()
        clr = pg.ColorMap(*zip(*Gradients['grey']['ticks']))
        self.imageWidget.setColorMap(clr)
        
        self.hor_plotWidget = pg.PlotWidget()
        self.hor_plotWidget.showGrid(x=True, y=True)
        self.hor_plotWidget.setTitle('Horizontal cut or projection', color=(255,255,0))
        self.hor_plotWidget.setLabel('left', 'Intensity, [arb.units]', color='lawngreen')
        self.hor_plotWidget.setLabel('bottom', 'X, [um]', color='lawngreen')
        
        self.vrt_plotWidget = pg.PlotWidget()
        self.vrt_plotWidget.showGrid(x=True, y=True)
        self.vrt_plotWidget.setTitle('Vertical cut or projection', color=(255,255,0))
        self.vrt_plotWidget.setLabel('left', 'Intensity, [arb.units]', color='lawngreen')
        self.vrt_plotWidget.setLabel('bottom', 'Y, [um]', color='lawngreen')
        
        
        # Time PLOTS
        self.tot_int_plot = pg.PlotWidget()
        self.tot_int_plot.setBackground('w')
        self.tot_int_plot.showGrid(x=True, y=True)
        self.tot_int_plot.setTitle('Total intensity', color=(255,0,0))
        self.tot_int_plot.setLabel('left', 'Tot. int. [arb.units]')
        self.tot_int_plot.setLabel('bottom', 'Measurement #')
        
        self.hor_sigma_plot = pg.PlotWidget()
        self.hor_sigma_plot.setBackground('w')
        self.hor_sigma_plot.showGrid(x=True, y=True)
        self.hor_sigma_plot.setTitle('Sigma_x', color=(255,0,0))
        self.hor_sigma_plot.setLabel('left', 'sigma_x, [um]')
        self.hor_sigma_plot.setLabel('bottom', 'Measurement #')
        
        self.vrt_sigma_plot = pg.PlotWidget()
        self.vrt_sigma_plot.setBackground('w')
        self.vrt_sigma_plot.showGrid(x=True, y=True)
        self.vrt_sigma_plot.setTitle('Sigma_y', color=(255,0,0))
        self.vrt_sigma_plot.setLabel('left', 'sigma_y, [um]')
        self.vrt_sigma_plot.setLabel('bottom', 'Measurement #')
        
        
        
        

        
        
        
        
        # Connection with the camera
        self.CamConBtn = QPushButton('Connect camera', self)
        self.CamConBtn.setToolTip('Press to connect the camera')
        self.CamConBtn.clicked.connect(self.cam_con)

        # Getting of a picture from the camera
        self.PictAqBtn = QPushButton('One picture', self)
        self.PictAqBtn.setToolTip('Press to get a picture')
        self.PictAqBtn.clicked.connect(self.pict_aq)

        # Getting of a BG picture
        self.BgPictAqBtn = QPushButton('BG picture', self)
        self.BgPictAqBtn.setToolTip('To collect BG picture')
        self.BgPictAqBtn.clicked.connect(self.bg_pict_aq)

        # BG subtract CheckBox
        self.BgSubtrChBox = QCheckBox('- BG to subtract')
        self.BgSubtrChBox.setChecked(True)
        self.BgSubtrChBox.stateChanged.connect(self.img_replot)




        
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
        self.PlotScaleComBox.addItems(['grey', 'greyclip', 'bipolar', 'thermal', 'flame'])
        self.PlotScaleComBox.currentIndexChanged.connect(self.img_replot)
                



        
        
        # File to save name
        self.SaveFolderBtn = QPushButton('Choose Folder', self)
        self.SaveFolderBtn.clicked.connect(self.folder_name)
        self.SaveFolderBtn.setToolTip('Choose the directory to save the data')

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
        
        self.SaveBtn = QPushButton('Take and Save pictures')
        self.SaveBtn.clicked.connect(self.save_pictures)
        self.SaveBtn.setToolTip('Press to take and save')



        

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
        self.HorFitParLbl = QLabel('Hor. estimated sigma')
        self.HorFitParLbl.setStyleSheet('color: red')
        self.HorFitParLnEd = QLineEdit(str(self.hor_fit_par[3]), alignment=Qt.AlignCenter)
        self.HorFitParLnEd.editingFinished.connect(self.hor_fit_set)
        self.HorFitParLnEd.editingFinished.connect(self.img_replot)
        self.HorFitParLnEd.setToolTip('Anticipated sigma_x')

        # Vrt Parameter to fit
        self.VrtFitParLbl = QLabel('Vrt. estimated sigma')
        self.VrtFitParLbl.setStyleSheet('color: red')
        self.VrtFitParLnEd = QLineEdit(str(self.vrt_fit_par[3]), alignment=Qt.AlignCenter)
        self.VrtFitParLnEd.editingFinished.connect(self.vrt_fit_set)
        self.VrtFitParLnEd.editingFinished.connect(self.img_replot)
        self.VrtFitParLnEd.setToolTip('Anticipated sigma_y')

        # Paramter for pixel to um convertion
        self.ConvertLnEd = QLineEdit('1', alignment=Qt.AlignCenter)




        # Dialog window
        self.MainMsgBox = QTextEdit()
        self.MainMsgBox.setReadOnly(True)
        self.MainMsgBox.setText('Hi!')
        
        


        ################################ continuous image grabbing ################
        # Start Image grabbing Button
        self.StartImgGrabBtn = QPushButton('Start Image grabbing', self)
        self.StartImgGrabBtn.setToolTip('Press to initiate image grabbing')
        # Connection to FUNC is in the self.new_thread()

        # Stop Image grabbing Button
        self.StopImgGrabBtn = QPushButton('Stop Image grabbing', self)
        self.StopImgGrabBtn.setToolTip('Press to stop image grabbing')
        # Connection to FUNC is in the self.new_thread()        
        
        # Thread for continuous image grabbing
        # It's done via function because every time we're stopping "image grabbing"...
        # ...we have to kill this thread and start a new one.
        self.new_thread()
        ################################ continuous image grabbing ################
























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
        self.vboxGroupMain.addWidget(self.PlotScaleComBox)
        self.vboxGroupMain.addStretch(1)
        self.GroupMain.setLayout(self.vboxGroupMain)
        
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
        self.GridGroupFitPar.addWidget(QLabel('Pix. to um factor'), 7,0,1,1)
        self.GridGroupFitPar.addWidget(self.ConvertLnEd,            7,1,1,1)
        self.GroupFitPar.setLayout(self.GridGroupFitPar)

        # Group for Save Options
        self.GroupSave = QGroupBox('Save parameters')
        self.vboxGroupSave = QVBoxLayout()
        self.vboxGroupSave.addWidget(self.SaveFolderBtn)
        self.vboxGroupSave.addWidget(QLabel('Number of pictures to save'))
        self.vboxGroupSave.addWidget(self.NPictSaveLnEd)
        self.vboxGroupSave.addWidget(QLabel('Picture format'))
        self.vboxGroupSave.addWidget(self.PictureFormatComBox)
        self.vboxGroupSave.addWidget(self.SaveBtn)
        self.vboxGroupSave.addStretch(1)
        self.GroupSave.setLayout(self.vboxGroupSave)

        # VBox for messages
        self.GroupMsg = QGroupBox('Messages')
        self.vboxMsgGroup = QVBoxLayout()
        self.vboxMsgGroup.addWidget(self.MainMsgBox)
        self.GroupMsg.setLayout(self.vboxMsgGroup)

        
                
        
        
        
        
        
        # Here we're defining the main grid which will contain all the buttons, plots and so on
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        for i in range(6):
            self.grid.setColumnMinimumWidth(i,1600/6)
        self.grid.setRowMinimumHeight(0,300)
                
        self.grid.addWidget(self.imageWidget,           0,0,1,2)
        self.grid.addWidget(self.hor_plotWidget,        0,2,1,2)
        self.grid.addWidget(self.vrt_plotWidget,        0,4,1,2)
        
        self.grid.addWidget(self.tot_int_plot,          1,0,1,2)
        self.grid.addWidget(self.hor_sigma_plot,        1,2,1,2)
        self.grid.addWidget(self.vrt_sigma_plot,        1,4,1,2)

        self.grid.addWidget(self.GroupMain,     2,0,1,2)
        self.grid.addWidget(self.GroupCamSet,   2,2,1,1)
        self.grid.addWidget(self.GroupFitPar,   2,3,1,1)
        self.grid.addWidget(self.GroupSave,     2,4,1,1)
        self.grid.addWidget(self.GroupMsg,      2,5,1,1)
        
        self.setLayout(self.grid)

        self.error_dialog = QMessageBox()
        self.error_dialog.setIcon(QMessageBox.Critical)        
        
        

        self.cam_con() # Here we're connecting to the camera
        
        self.show()

    # Function for a Thread creation
    # The thread is needed for image grabbing in the "background mode"
    def new_thread(self):

        self.img_grab_thread = QThread()
        self.img_grab_worker = misc_class.Img_Grab()
        self.img_grab_stop_signal.connect(self.img_grab_worker.stop)
        self.img_grab_worker.moveToThread(self.img_grab_thread)

        self.img_grab_thread.started.connect(self.img_grab_worker.do_work)
        self.img_grab_thread.finished.connect(self.img_grab_worker.stop)

        self.StartImgGrabBtn.clicked.connect(self.img_grab_thread.start)
        self.StopImgGrabBtn.clicked.connect(self.img_grab_stop_signal.emit)

        self.img_grab_worker.img_grab_and_plot_signal.connect(self.pict_aq)
        self.img_grab_worker.finished.connect(self.img_grab_thread.quit)
        self.img_grab_worker.finished.connect(self.img_grab_worker.deleteLater)
        self.img_grab_thread.finished.connect(self.img_grab_thread.deleteLater)
        self.img_grab_thread.finished.connect(self.new_thread)
    

#######################################################
#######################################################
        # END of THE WINDOWS DEFINITION





    
    def cam_con(self):
        self.MainMsgBox.setText('Camera connection...')
        time.sleep(0.5)
        if self.camera != None:
            self.camera.Close()

        try:
            self.camera = cam_func.cam_con()    # connect to the camera
            self.ExpTimeLnEd.setText(str(self.camera.ExposureTimeAbs.GetValue())) # Check Exp time of the camera
            self.GainLnEd.setText(str(self.camera.GainRaw.GetValue()))  # check gain of the camera

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
            misc_func.list_pop(self.tot_int, self.number_of_points, np.sum(np.sum(self.pict)))
            self.plot()

            self.MainMsgBox.append('   Total intensity = ' + str(self.tot_int[-1]))

        
    # Changing name of the folder pictures to be saved
    def folder_name(self):
        self.folder_to_save = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        print(self.folder_to_save)
        self.MainMsgBox.setText('DIRECTORY FOR DATA SAVING is - ' + '\n' + self.folder_to_save)


    # Saving function
    def save_pictures(self):
        n_pict_to_save = int(self.NPictSaveLnEd.text())
        moment = datetime.datetime.now().strftime('%d_%B_%Y__%H_%M_%S')
        
        header_file = self.folder_to_save + '\\' + moment + '_header.txt'
        bg_file = self.folder_to_save + '\\' + moment + '_BG' + self.PictureFormatComBox.currentText()
        
        self.MainMsgBox.setText('Saving Data... \n')
        
        if self.camera is not None:
            # Writing the header file
            file = open(header_file, 'w')
            file.write('Connected to the Device - ' + str(self.camera.GetDeviceInfo().GetModelName()) + '\n')
            file.write('Exposure time = ' + str(self.camera.ExposureTimeAbs.GetValue()) + ' us' + '\n')
            file.write('Gain = ' + str(self.camera.GainRaw.GetValue()) + '\n')
            file.write('Temperature = ' + str(self.camera.TemperatureAbs.GetValue()) + ' deg' + '\n')
            file.write('Pixel mode is ' + str(self.camera.PixelFormat.GetValue()) + '\n')
            file.close()
            self.MainMsgBox.append('   Header was saved. \n')
            
            # Saving the BG picture
            if self.bg_pict is not None:
                img = Image.fromarray(self.bg_pict)
                img.save(bg_file, format=self.formats[self.PictureFormatComBox.currentText()])
                self.MainMsgBox.append('   BG picture was saved. \n')
            else:
                self.MainMsgBox.append('   It seems there is no BG picture. \n')
                print('   It seems there is no BG picture. \n')
                
                
            # Saving pictures
            for i in range(n_pict_to_save):
                try:
                    img_file = self.folder_to_save + '\\' + moment + '_' + str(i) + self.PictureFormatComBox.currentText()
                    img = cam_func.pict_aq(self.camera)
                    img = Image.fromarray(img)
                    img.save(img_file, format=self.formats[self.PictureFormatComBox.currentText()])
                    self.MainMsgBox.append('   Picture acquised #' + str(i) + ' saved')
                    print('   Picture #' + str(i) + ' saved')
                except:
                    self.MainMsgBox.append('   Picture #' + str(i) + 'was not saved by some reason.')
                    print('   Picture #' + str(i) + 'was not saved by some reason.')
                
        else:
            self.MainMsgBox.append('   It seems there is no camera connected and thus nothing was saved. \n')
            print('   It seems there is no camera connected and thus nothing was saved. \n')
        
        print(header_file)
        print(bg_file)
        
            
    # Getting BG picture
    def bg_pict_aq(self):
        self.MainMsgBox.setText('Getting BG picture...')
        self.bg_pict = cam_func.pict_aq(self.camera)
        for i in range(9):
            self.bg_pict = self.bg_pict + cam_func.pict_aq(self.camera)
            time.sleep(0.1)
        self.bg_pict = self.bg_pict / 10
        self.MainMsgBox.append('   BG picture is received.\n')
        print('    BG picture is received! \n')

            
    # Changing exposure time
    def exp_time(self):
        cam_func.exp_time(self.camera, float(self.ExpTimeLnEd.text()))


    # Changing Gain
    def gain(self):
        cam_func.gain(self.camera, float(self.GainLnEd.text()))

    # Changing between Mono8 and Mono12 pixel formats
    def pixel_format(self):
        try:
            cam_func.pixel_format(self.camera, self.PixelFormatComBox.currentText())
            self.MainMsgBox.setText('Pixel Format is set to ' + self.camera.PixelFormat.GetValue())
        except:
            print('SOmething went wrong with exchanging the pixel format')
            self.MainMsgBox.setText('Pixel Format is not changed! Something went wrong')


                

    # Chnging number of pictures to be saved
    def n_pict_to_save(self):
        self.img_grab_worker.n_pict_save = int(self.NPictSaveLnEd.text())


    def worker_to_save_flag(self):
        self.img_grab_worker.to_save_flag = self.FolderChBox.isChecked()


    def hor_fit_set(self):
        aaa = self.HorFitParLnEd.text()
        try:
            aaa = float(aaa)
            self.hor_fit_par[3] = float(aaa)
        except:
            self.HorFitParLnEd.setText('10')
            self.MainMsgBox.setText('Hor sigma should be a NUMBER')
            

    
    def vrt_fit_set(self):
        aaa = self.VrtFitParLnEd.text()
        try:
            aaa = float(aaa)
            self.vrt_fit_par[3] = float(aaa)    
        except:
            self.VrtFitParLnEd.setText('10')
            self.MainMsgBox.setText('Vrt sigma should be a NUMBER')
    
            
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
            self.plot()
        self.replot_flag = False
        
    
    def plot(self):

        img = self.pict
        if not (np.sum(self.bg_pict == None)) and self.BgSubtrChBox.isChecked():
            img = img - self.bg_pict
           
        def gaus(x, bg, Amp, mu, sigma):
                return bg + Amp * np.exp(- (x - mu)**2 / (2 * sigma**2))
            
            
        # The next line is fitting. It will check if it's necessary to fit and Cut or Projection
        hor_proj, vrt_proj, xdata, ydata, self.hor_fit_par, self.vrt_fit_par, x_max_pos, y_max_pos, msg = misc_func.gaus_fit(img, self.hor_fit_par[3], self.vrt_fit_par[3], self.CutOrProjComBox.currentText(), int(self.CutWidthLnEd.text()), self.FitChBox.isChecked())
        self.MainMsgBox.append('\n' + msg + '\n')
        self.MainMsgBox.append('    X position of maximum = ' + str(x_max_pos))
        self.MainMsgBox.append('    Y position of maximum = ' + str(y_max_pos) + '\n')
        self.HorFitParLnEd.setText(str(round(self.hor_fit_par[3]*float(self.ConvertLnEd.text()))))
        self.VrtFitParLnEd.setText(str(round(self.vrt_fit_par[3]*float(self.ConvertLnEd.text()))))
        if self.replot_flag == False:
            misc_func.list_pop(self.sigma_x, self.number_of_points, self.hor_fit_par[3]*float(self.ConvertLnEd.text()))
            misc_func.list_pop(self.sigma_y, self.number_of_points, self.vrt_fit_par[3]*float(self.ConvertLnEd.text()))
        else:
            self.sigma_x[-1] = self.hor_fit_par[3]*float(self.ConvertLnEd.text())
            self.sigma_y[-1] = self.vrt_fit_par[3]*float(self.ConvertLnEd.text())
        
        
        pen1 = pg.mkPen(color=(255, 0, 0), width=4)
        pen2 = pg.mkPen(color=(125, 255, 0), width=2)
        pen3 = pg.mkPen(color=(0, 0, 255), width=2)
        
        
        # PLOTTING PICTURE and CUTS or PROJECTIONS
        self.imageWidget.setImage(img, autoRange=False)
        clr = pg.ColorMap(*zip(*Gradients[self.PlotScaleComBox.currentText()]['ticks']))
        self.imageWidget.setColorMap(clr)
                
        self.hor_plotWidget.clear()
        self.hor_plotWidget.plot(xdata, hor_proj, pen=pen1)
        if self.FitChBox.isChecked():
            self.hor_plotWidget.plot(xdata*float(self.ConvertLnEd.text()), gaus(xdata, *self.hor_fit_par), pen=pen2)
        if self.FitChBox.isChecked(): # Here write sigma_x in the message window
            if self.replot_flag == False:
                self.MainMsgBox.append('   Sigma_x = ' + str(round(self.hor_fit_par[3],3)))
        
        self.vrt_plotWidget.clear()
        self.vrt_plotWidget.plot(ydata*float(self.ConvertLnEd.text()), vrt_proj, pen=pen1)
        if self.FitChBox.isChecked():
            self.vrt_plotWidget.plot(ydata, gaus(ydata, *self.vrt_fit_par), pen=pen2)
        if self.FitChBox.isChecked():
            if self.replot_flag == False:
                self.MainMsgBox.append('   Sigma_y = ' + str(round(self.vrt_fit_par[3],3)) + '\n')
                
                
                
        
        # PLOTTIMG TIME PLOTS
        self.tot_int_plot.clear()
        self.tot_int_plot.plot(self.tot_int, pen=pen3, symbol='o', symbolSize=10, symbolBrush=('r'))
        
        self.hor_sigma_plot.clear()
        self.hor_sigma_plot.plot(self.sigma_x, pen=pen3, symbol='o', symbolSize=10, symbolBrush=('r'))
        
        self.vrt_sigma_plot.clear()
        self.vrt_sigma_plot.plot(self.sigma_y, pen=pen3, symbol='o', symbolSize=10, symbolBrush=('r'))




    

    
if __name__== '__main__':

    app = QApplication(sys.argv)
    main_wndw = main_window()
        
    sys.exit(app.exec_())
