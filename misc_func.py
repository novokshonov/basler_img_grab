from PyQt5 import QtGui
from scipy.optimize import curve_fit
import numpy as np


# Fitting routine function
def gaus_fit(img, hor_sigma, vrt_sigma, cut_or_proj, cut_wdth, to_fit):

    def gaus(x, bg, Amp, mu, sigma):
                return bg + Amp * np.exp(- (x - mu)**2 / (2 * sigma**2))


    if cut_or_proj == 'Cut': # Fitting cuts

        # Finding maximum positions
        x_max_pos = np.argmax(np.sum(img,0))
        y_max_pos = np.argmax(np.sum(img,1))
        
        img_height = np.size(img,0)
        img_width = np.size(img,1)

        # Calculating the cuts and X and Y data for fitting
        hor_data = np.sum(img[y_max_pos-cut_wdth:y_max_pos+cut_wdth, :],0) / (2*cut_wdth + 1)
        vrt_data = np.sum(img[:, x_max_pos-cut_wdth:x_max_pos+cut_wdth],1) / (2*cut_wdth + 1)
        xdata = np.linspace(0,img_width,img_width)
        ydata = np.linspace(0,img_height,img_height)

        # Initial parameters for fitting
        hor_fit_par = [np.min(hor_data), np.max(hor_data) - np.min(hor_data), x_max_pos, hor_sigma]
        vrt_fit_par = [np.min(vrt_data), np.max(vrt_data) - np.min(vrt_data), y_max_pos, vrt_sigma]

        # Fitting itself
        if to_fit == True: # Here we check if it's necessary to fit
            try:
                hor_fit_par, hor_cov = curve_fit(gaus, xdata, hor_data, hor_fit_par)
                vrt_fit_par, vrt_cov = curve_fit(gaus, ydata, vrt_data, vrt_fit_par)
                hor_fit_par[3] = np.abs(hor_fit_par[3])
                vrt_fit_par[3] = np.abs(vrt_fit_par[3])
                message = 'Fitting is done!'
                return hor_data, vrt_data, xdata, ydata, hor_fit_par, vrt_fit_par, x_max_pos, y_max_pos, message
            except:
                hor_fit_par[3] = 10
                vrt_fit_par[3] = 10
                message = 'Fitting ERROR!'
                return hor_data, vrt_data, xdata, ydata, hor_fit_par, vrt_fit_par, x_max_pos, y_max_pos, message
        else:
            message = 'There was no fitting'
            return hor_data, vrt_data, xdata, ydata, hor_fit_par, vrt_fit_par, x_max_pos, y_max_pos, message
            

    else: # Fitting projections

        # Finding maximum positions
        x_max_pos = np.argmax(np.sum(img,0))
        y_max_pos = np.argmax(np.sum(img,1))

        img_height = np.size(img,0)
        img_width = np.size(img,1)
        
        # Calculating the cuts and X and Y data for fitting
        hor_data = np.sum(img,0) / img_height
        vrt_data = np.sum(img,1) / img_width
        xdata = np.linspace(0,img_width,img_width)
        ydata = np.linspace(0,img_height,img_height)

        # Initial parameters for fitting
        hor_fit_par = [np.min(hor_data), np.max(hor_data) - np.min(hor_data), x_max_pos, hor_sigma]
        vrt_fit_par = [np.min(vrt_data), np.max(vrt_data) - np.min(vrt_data), y_max_pos, vrt_sigma]

        # Fitting itself
        if to_fit == True: # Here we check if it's necessary to fit
            try:
                hor_fit_par, hor_cov = curve_fit(gaus, xdata, hor_data, hor_fit_par)
                vrt_fit_par, vrt_cov = curve_fit(gaus, ydata, vrt_data, vrt_fit_par)
                hor_fit_par[3] = np.abs(hor_fit_par[3])
                vrt_fit_par[3] = np.abs(vrt_fit_par[3])
                message = 'Fitting is done!'
                return hor_data, vrt_data, xdata, ydata, hor_fit_par, vrt_fit_par, x_max_pos, y_max_pos, message
            except:
                hor_fit_par[3] = 10
                vrt_fit_par[3] = 10
                message = 'Fitting ERROR!'
                return hor_data, vrt_data, xdata, ydata, hor_fit_par, vrt_fit_par, x_max_pos, y_max_pos, message
        else:
            message = 'There was no fitting'
            return hor_data, vrt_data, xdata, ydata, hor_fit_par, vrt_fit_par, x_max_pos, y_max_pos, message

        












# Function for append numbers in the tot_int sigma_x sigma_y lists
def list_pop(lst, max_length, n):
    if len(lst)<max_length:
        lst.append(n)
    elif len(lst) == max_length:
        lst.remove(lst[0])
        lst.append(n)
    else:
        lst = lst[int(len(lst)-max_length+1):]
        lst.append(n)




