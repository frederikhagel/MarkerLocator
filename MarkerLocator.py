from time import time
import sys
import numpy as np
#import cv
import cv2.cv as cv

'''
2012-10-10
Script developed by Henrik Skov Midtiby (henrikmidtiby@gmail.com).
Provided for free but use at your own risk.
'''


class MarkerTracker:
    '''
    Purpose: Locate a certain marker in an image.
    '''
    def __init__(self, order, kernelSize, scaleFactor):
        (kernelReal, kernelImag) = self.generateSymmetryDetectorKernel(order, kernelSize)
            
        self.matReal = cv.CreateMat(kernelSize, kernelSize, cv.CV_32FC1)
        self.matImag = cv.CreateMat(kernelSize, kernelSize, cv.CV_32FC1)
        for i in range(kernelSize):
        	for j in range(kernelSize):
        		self.matReal[i, j] = kernelReal[i][j] / scaleFactor
        		self.matImag[i, j] = kernelImag[i][j] / scaleFactor
        self.lastMarkerLocation = (None, None)
                  
    def generateSymmetryDetectorKernel(self, order, kernelsize):
        valueRange = np.linspace(-1, 1, kernelsize);
        temp1 = np.meshgrid(valueRange, valueRange)
        kernel = temp1[0] + 1j*temp1[1];
            
        magni = abs(kernel);
        kernel = kernel**order;
        kernel = kernel*np.exp(-8*magni**2);
         
        return (np.real(kernel), np.imag(kernel))

    def allocateSpaceGivenFirstFrame(self, frame):
        self.newFrameImage32F = cv.CreateImage((frame.width, frame.height), cv.IPL_DEPTH_32F, 3)
        self.frameRealSq = cv.CreateImage ((frame.width, frame.height), cv.IPL_DEPTH_32F, 1)
        self.frameImagSq = cv.CreateImage ((frame.width, frame.height), cv.IPL_DEPTH_32F, 1)
        self.frameSumSq = cv.CreateImage ((frame.width, frame.height), cv.IPL_DEPTH_32F, 1)

    
    def locateMarker(self, frame):
        frameReal = cv.CloneImage(frame)
        frameImag = cv.CloneImage(frame)

        cv.Filter2D(frameReal, frameReal, self.matReal)
        cv.Filter2D(frameImag, frameImag, self.matImag)
        cv.Mul(frameReal, frameReal, self.frameRealSq)
        cv.Mul(frameImag, frameImag, self.frameImagSq)
        cv.Add(self.frameRealSq, self.frameImagSq, self.frameSumSq)
        
        min_val, max_val, min_loc, max_loc = cv.MinMaxLoc(self.frameSumSq)
        self.lastMarkerLocation = max_loc
        (xm, ym) = max_loc
        return max_loc

class ImageAnalyzer:
    '''
    Purpose: Locate markers in the presented images.
    '''
    def __init__(self, downscaleFactor = 2):
        self.downscaleFactor = downscaleFactor
        self.markerTrackers = []
        self.tempImage = None
        self.greyScaleImage = None
        self.subClassesInitialized = False
        self.markerLocationsX = []
        self.markerLocationsY = []
        pass

    def addMarkerToTrack(self, order, kernelSize, scaleFactor):
        self.markerTrackers.append(MarkerTracker(order, kernelSize, scaleFactor))
        self.markerLocationsX.append(0)
        self.markerLocationsY.append(0)
        self.subClassesInitialized = False 
    
    # Is called with a colour image.
    def initializeSubClasses(self, frame):
        self.subClassesInitialized = True
        reducedWidth = frame.width / self.downscaleFactor
        reducedHeight = frame.height / self.downscaleFactor
        reducedDimensions = (reducedWidth, reducedHeight)
        self.frameGray = cv.CreateImage (reducedDimensions, cv.IPL_DEPTH_32F, 1)
        self.originalImage = cv.CreateImage(reducedDimensions, cv.IPL_DEPTH_32F, 3)
        self.reducedImage = cv.CreateImage(reducedDimensions, frame.depth, frame.nChannels)
        for k in range(len(self.markerTrackers)):
            self.markerTrackers[k].allocateSpaceGivenFirstFrame(self.reducedImage)
    
    # Is called with a colour image.
    def analyzeImage(self, frame):
        if(self.subClassesInitialized is False):
            self.initializeSubClasses(frame)

        cv.Resize(frame, self.reducedImage)

        cv.ConvertScale(self.reducedImage, self.originalImage)
        cv.CvtColor(self.originalImage, self.frameGray, cv.CV_RGB2GRAY)

        for k in range(len(self.markerTrackers)):
            markerLocation = self.markerTrackers[k].locateMarker(self.frameGray)
            (xm, ym) = markerLocation
            (xm, ym) = (self.downscaleFactor * xm, self.downscaleFactor * ym)
            self.markerLocationsX[k] = xm
            self.markerLocationsY[k] = ym
            #cv.Line(frame, (0, ym), (frame.width, ym), (0, 0, 255)) # B, G, R
            #cv.Line(frame, (xm, 0), (xm, frame.height), (0, 0, 255))

        return frame

class TrackerInWindowMode:
    def __init__(self, order = 7):
        #cv.NamedWindow('reducedWindow', cv.CV_WINDOW_AUTOSIZE)
        self.windowWidth = 100
        self.windowHeight = 100
        self.frameGray = cv.CreateImage ((self.windowWidth, self.windowHeight), cv.IPL_DEPTH_32F, 1)
        self.originalImage = cv.CreateImage((self.windowWidth, self.windowHeight), cv.IPL_DEPTH_32F, 3)
        self.markerTracker = MarkerTracker(order, 21, 2500)
        self.trackerIsInitialized = False
        self.subImagePosition = None
        pass
    
    def cropFrame(self, frame, lastMarkerLocationX, lastMarkerLocationY):
        if(not self.trackerIsInitialized):
            self.markerTracker.allocateSpaceGivenFirstFrame(self.originalImage)
            self.reducedImage = cv.CreateImage((self.windowWidth, self.windowHeight), frame.depth, 3)
        xCornerPos = lastMarkerLocationX - self.windowWidth / 2
        yCornerPos = lastMarkerLocationY - self.windowHeight / 2
        # Ensure that extracted window is inside the original image.
        if(xCornerPos < 1):
            xCornerPos = 1
        if(yCornerPos < 1):
            yCornerPos = 1
        if(xCornerPos > frame.width - self.windowWidth):
            xCornerPos = frame.width - self.windowWidth
        if(yCornerPos > frame.height - self.windowHeight):
            yCornerPos = frame.height - self.windowHeight
        try:
            self.subImagePosition = (xCornerPos, yCornerPos, self.windowWidth, self.windowHeight)
            self.reducedImage = cv.GetSubRect(frame, self.subImagePosition)
            cv.ConvertScale(self.reducedImage, self.originalImage)
            cv.CvtColor(self.originalImage, self.frameGray, cv.CV_RGB2GRAY)
        except:
            print("frame: ", frame.depth)
            print("originalImage: ", self.originalImage.height, self.originalImage.width, self.originalImage)
            print("frameGray: ", self.frameGray.height, self.frameGray.width, self.frameGray.depth)
            print "Unexpected error:", sys.exc_info()[0]
            #quit(0)
            pass
        
    def locateMarker(self):
        (xm, ym) = self.markerTracker.locateMarker(self.frameGray)
        #xm = 50
        #ym = 50
        cv.Line(self.reducedImage, (0, ym), (self.originalImage.width, ym), (0, 0, 255)) # B, G, R
        cv.Line(self.reducedImage, (xm, 0), (xm, self.originalImage.height), (0, 0, 255))
        
        xm = xm + self.subImagePosition[0]
        ym = ym + self.subImagePosition[1]
        print((xm, ym))
        return [xm, ym]
        
    def showCroppedImage(self):
        pass
        #cv.ShowImage('reducedWindow', self.reducedImage)
        #cv.ShowImage('reducedWindow', self.originalImage)
        #cv.ShowImage('reducedWindow', self.frameGray)
        #cv.ShowImage('reducedWindow', self.markerTracker.frameSumSq)
        
    
    
class CameraDriver:
    ''' 
    Purpose: capture images from a camera and delegate procesing of the 
    images to a different class.
    '''
    def __init__(self, markerOrders = [7, 8], defaultKernelSize = 21, scalingParameter = 2500):
        cv.NamedWindow('filterdemo', cv.CV_WINDOW_AUTOSIZE)
        self.camera = cv.CaptureFromCAM(0)
        self.currentFrame = None
        self.processedFrame = None
        self.running = True
        self.trackers = []
        self.windowedTrackers = []
        self.oldLocations = []
        for markerOrder in markerOrders:
            temp = ImageAnalyzer(1)
            temp.addMarkerToTrack(markerOrder, defaultKernelSize, scalingParameter)
            self.trackers.append(temp)
            self.windowedTrackers.append(TrackerInWindowMode(markerOrder))
            self.oldLocations.append(None)
        self.cnt = 0

    
    def getImage(self):
        self.currentFrame = cv.QueryFrame(self.camera)
        
    def processFrame(self):
        for k in range(len(self.trackers)):
            if(self.oldLocations[k] is None):
                self.processedFrame = self.trackers[k].analyzeImage(self.currentFrame)
                markerX = self.trackers[k].markerLocationsX[0]
                markerY = self.trackers[k].markerLocationsY[0]
                self.oldLocations[k] = [markerX, markerY]
            self.windowedTrackers[k].cropFrame(self.currentFrame, self.oldLocations[k][0], self.oldLocations[k][1])
            self.oldLocations[k] = self.windowedTrackers[k].locateMarker()
            self.windowedTrackers[k].showCroppedImage()
    
    def showProcessedFrame(self):
        cv.ShowImage('filterdemo', self.processedFrame)
        pass

    def resetAllLocations(self):
        for k in range(len(self.trackers)):
            self.oldLocations[k] = None
        
    def handleKeyboardEvents(self):
        key = cv.WaitKey(20)
        if key == 27: # Esc
            self.running = False
        if key == 1048690: # r
            print("Resetting")
            self.resetAllLocations()
        if key == 1048691: # s
            # save image
            print("Saving image")
            cv.SaveImage("output/filename%03d.png" % self.cnt, self.currentFrame)
            self.cnt = self.cnt + 1
    
    def returnPosition(self):
        return self.oldLocation

def mainTwo():
    
    t0 = time()
    t1 = time()
    t2 = time()

    print 'function vers1 takes %f' %(t1-t0)
    print 'function vers2 takes %f' %(t2-t1)
    
    cd = CameraDriver([5, 6])
    t0 = time()
     
    while cd.running:
        (t1, t0) = (t0, time())
      #  print "time for one iteration: %f" % (t0 - t1)
        cd.getImage()
        cd.processFrame()
        cd.showProcessedFrame()
        cd.handleKeyboardEvents()
        y = cd.returnPosition()     
        print y

        
    print("Stopping")


mainTwo()
