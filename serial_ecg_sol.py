from threading import Thread
import serial
import time
import collections
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import struct
import numpy as np
import neurokit2 as nk


class serialPlot:
    def __init__(self, serialPort = '/dev/ttyUSB0', serialBaud = 38400, plotLength = 100, dataNumBytes = 2):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.dataNumBytes = dataNumBytes
        self.rawData = bytearray(dataNumBytes)
        self.data = collections.deque([0] * plotLength, maxlen=plotLength)
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
        self.previousThreadTimer = 0
        self.ThreadTimer = 0
        self.ThreadCount = 0

        print('Trying to connect to: ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(serialPort, serialBaud, timeout=4)
            print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')

    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)

    def getSerialData(self, frame, lines, lineValueText, lineLabel, timeText, ax, sp):
        #currentTimer = time.time()
        #self.plotTimer = int((currentTimer - self.previousTimer) * 1000)     # the first reading will be erroneous
        #self.previousTimer = currentTimer
        #timeText.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')
        timeText.set_text('Thread Interval = ' + str(int(self.ThreadTimer*10)/10.0) + 'ms')

        data = np.array(self.data).copy()
        if len(data[data>0]) == self.plotMaxLength:
            signals, info = nk.ecg_process(data, sampling_rate=250)
            x = np.arange(signals['ECG_R_Peaks'].size)[signals['ECG_R_Peaks']==1]
            y_raw = signals['ECG_Raw'][signals['ECG_R_Peaks']==1]
            sp.set_data(x,y_raw)
            lineValueText.set_text('[ Heart Rate ] = ' + str(int(signals['ECG_Rate'].iloc[-1]*10)/10.0))
        
        lines.set_data(range(self.plotMaxLength),data)
#        lineValueText.set_text('[' + lineLabel + '] = ' + str(self.data[-1]))
        ax.set_ylim(min(self.data),max(self.data))
        
    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            self.serialConnection.readinto(self.rawData)
            self.isReceiving = True
                        
            value,  = struct.unpack('h', self.rawData)    # use 'h' for a 2 byte integer, 'f' for a 2 byte integer
            self.data.append(value)    # we get the latest data point and append it to our array
            
            with open('data.txt','ab') as f:
                np.savetxt(f, [value], fmt = '%d')

            self.ThreadCount += 1
            if self.ThreadCount>=100:
                self.ThreadCount = 0
                currentTimer = time.perf_counter()
                self.ThreadTimer = (currentTimer - self.previousThreadTimer)*10
#                self.ThreadTimer = (currentTimer - self.previousThreadTimer)*self.plotMaxLength/100
                self.previousThreadTimer = currentTimer
#                print(self.ThreadTimer, value)

    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')


def main():
    portName = 'COM14'     # for windows users
    # portName = '/dev/ttyUSB0'  # for linux users
    baudRate = 38400
    maxPlotLength = 1000
    dataNumBytes = 2        # number of bytes of 1 data point
    s = serialPlot(portName, baudRate, maxPlotLength, dataNumBytes)   # initializes all required variables
    s.readSerialStart()                                               # starts background thread

    # plotting starts below
    pltInterval = 200    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = maxPlotLength
    ymin = min(s.data)
    ymax = max(s.data)
    fig = plt.figure(figsize=(18,6))
    ax = plt.axes(xlim=(xmin, xmax), ylim=(ymin, ymax))
    ax.set_title('Arduino ECG Analog Read')
    ax.set_xlabel("time")
    ax.set_ylabel("AnalogRead ECG Value")
    sp, = ax.plot([],[],label='peak',ms=10,color='r',marker='o',ls='')

    lineLabel = 'ECG Reading Value'
    timeText = ax.text(0.50, 0.95, '', transform=ax.transAxes)
    lines = ax.plot([], [], label=lineLabel)[0]
    lineValueText = ax.text(0.50, 0.90, '', transform=ax.transAxes)
    anim = animation.FuncAnimation(fig, s.getSerialData, fargs=(lines, lineValueText, lineLabel, timeText, ax, sp), interval=pltInterval)    # fargs has to be a tuple

    plt.legend(loc="upper left")
    plt.show()
    s.close()


if __name__ == '__main__':
    main()