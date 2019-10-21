from PIL import Image
from pypylon import pylon
import matplotlib.pyplot as plt
import numpy as np
import time
import sys

# connecting to the camera
def cam_con():
    cam = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    time.sleep(2)
    cam.Open()
    print('Connected to the Device - ', cam.GetDeviceInfo().GetModelName())
    print('    Exposure time = ', cam.ExposureTimeAbs.GetValue(), ' us')
    print('    Gain = ', cam.GainRaw.GetValue())
    print('    Temperature = ', cam.TemperatureAbs.GetValue(), ' degrees')
    cam.ExposureAuto.SetValue('Off')
    cam.GainAuto.SetValue('Off')
    print('    Camera Gain and Exp. Time "AUTO" mode is OFF\n')

    return(cam)
    
def pict_aq(camera):
    print('Picture acquisition...')
    pict = np.zeros((camera.Height.GetValue(), camera.Width.GetValue()))

    camera.StartGrabbingMax(1)
    while camera.IsGrabbing():
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        time.sleep(0.1)
        if grabResult.GrabSucceeded():
            img = grabResult.Array
            pict = np.reshape(img, (camera.Height.GetValue(), camera.Width.GetValue()))
            print('    Picture aquised\n')
        else:
            print('    Error: ', grabResult.ErrorCode, grabResult.ErrorDescription,'\n')

        grabResult.Release()
    return pict

def exp_time(camera, num):
    camera.ExposureTimeAbs.SetValue(num)
    print('Camera exposure time is set to ', camera.ExposureTimeAbs.GetValue(), ' us')

def gain(camera, num):
    camera.GainRaw.SetValue(round(num))
    print('Camera gain is set to ', camera.GainRaw.GetValue())

    
