from ctypes import *
import os
import sys
from time import sleep
import wave

from PyQt4 import QtGui, QtCore
from serial import Serial

import modem

PVOID = c_void_p
INT = c_int
LONG = c_long
ULONG = c_ulong
WORD = c_ushort
DWORD = c_ulong
UCHAR = c_ubyte
STRING = c_char_p
BUFFER = c_buffer

class FT_PROGRAM_DATA(Structure):
    _fields_ = [
        ('Signature1', DWORD),
        ('Signature2', DWORD),
        ('Version', DWORD),
        ('VendorId', WORD),
        ('ProductId', WORD),
        ('Manufacturer', STRING),
        ('ManufacturerId', STRING),
        ('Description', STRING),
        ('SerialNumber', STRING),
        ('MaxPower', WORD),
        ('PnP', WORD),
        ('SelfPowered', WORD),
        ('RemoteWakeup', WORD),
        ('Rev4', UCHAR),
        ('IsoIn', UCHAR),
        ('IsoOut', UCHAR),
        ('PullDownEnable', UCHAR),
        ('SerNumEnable', UCHAR),
        ('USBVersionEnable', UCHAR),
        ('USBVersion', WORD),
        ('Rev5', UCHAR),
        ('IsoInA', UCHAR),
        ('IsoInB', UCHAR),
        ('IsoOutA', UCHAR),
        ('IsoOutB', UCHAR),
        ('PullDownEnable5', UCHAR),
        ('SerNumEnable5', UCHAR),
        ('USBVersionEnable5', UCHAR),
        ('USBVersion5', WORD),
        ('AIsHighCurrent', UCHAR),
        ('BIsHighCurrent', UCHAR),
        ('IFAIsFifo', UCHAR),
        ('IFAIsFifoTar', UCHAR),
        ('IFAIsFastSer', UCHAR),
        ('AIsVCP', UCHAR),
        ('IFBIsFifo', UCHAR),
        ('IFBIsFifoTar', UCHAR),
        ('IFBIsFastSer', UCHAR),
        ('BIsVCP', UCHAR),
        ('UseExtOsc', UCHAR),
        ('HighDriveIOs', UCHAR),
        ('EndpointSize', UCHAR),
        ('PullDownEnableR', UCHAR),
        ('SerNumEnableR', UCHAR),
        ('InvertTXD', UCHAR),
        ('InvertRXD', UCHAR),
        ('InvertRTS', UCHAR),
        ('InvertCTS', UCHAR),
        ('InvertDTR', UCHAR),
        ('InvertDSR', UCHAR),
        ('InvertDCD', UCHAR),
        ('InvertRI', UCHAR),
        ('Cbus0', UCHAR),
        ('Cbus1', UCHAR),
        ('Cbus2', UCHAR),
        ('Cbus3', UCHAR),
        ('Cbus4', UCHAR),
        ('RIsVCP', UCHAR)
    ]

if '_MEIPASS' in dir(sys):
    ftd2xx = WinDLL(os.path.join(sys._MEIPASS, 'ftd2xx.dll'))
else:
    ftd2xx = WinDLL('ftd2xx.dll')

FT_Open = ftd2xx.FT_Open
FT_Open.restype = ULONG
FT_Open.argtypes = [INT, POINTER(PVOID)]

FT_Close = ftd2xx.FT_Close
FT_Close.restype = ULONG
FT_Close.argtypes = [PVOID]

FT_EE_Read = ftd2xx.FT_EE_Read
FT_EE_Read.restype = ULONG
FT_EE_Read.argtypes = [PVOID, POINTER(FT_PROGRAM_DATA)]

FT_GetComPortNumber = ftd2xx.FT_GetComPortNumber
FT_GetComPortNumber.restype = ULONG
FT_GetComPortNumber.argtypes = [PVOID, POINTER(LONG)]

FT_OK = 0

class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        widget = QtGui.QWidget()
        grid = QtGui.QGridLayout()
        widget.setLayout(grid)

        self.fileButton = QtGui.QPushButton('Pick an audio file...')
        self.fileButton.clicked.connect(self.pick)

        self.uploadBar = QtGui.QProgressBar()
        self.progress = self.uploadBar.setValue
        self.progress(0)

        self.uploadButton = QtGui.QPushButton('Upload')
        self.uploadButton.clicked.connect(self.upload)
        self.uploadButton.setEnabled(False)
        
        grid.addWidget(self.fileButton, 0, 0)
        grid.addWidget(self.uploadBar, 1, 0)
        grid.addWidget(self.uploadButton, 2, 0)

        self.status = self.statusBar().showMessage
        self.status('Ready')
        self.worker = WorkerThread(
            self.status, self.progress, self.enableButtons
        )
        self.statusBar().setSizeGripEnabled(False)
        self.setCentralWidget(widget)
        self.setWindowTitle('RS-SBI')
        self.adjustSize()
        self.setFixedSize(256, self.height())
        self.show()

    def pick(self):
        self.filePath = str(QtGui.QFileDialog.getOpenFileName(
            self, 'Pick WAV file', os.getcwd(), 'WAV (*.wav;*.wave;*.w64)'
        ))

        if os.path.exists(self.filePath):
            self.fileSize = os.stat(self.filePath).st_size
            if self.fileSize > 2097152:
                self.update(False, 'ERROR: The file is larger than 2 MB')
                return

            try:
                self.fileWave = wave.open(self.filePath, 'rb')
            except:
                self.update(False, 'ERROR: Not a valid WAV PCM file')
                return

            self.frameRate = self.fileWave.getframerate()
            if self.fileWave.getnchannels() != 1:
                self.update(False, 'ERROR: Only mono supported')
                self.fileWave.close()
                return
            
            self.sampleWidth = self.fileWave.getsampwidth()
            if self.sampleWidth != 2:
                self.update(False, 'ERROR: Only 16 bits/sample supported')
                self.fileWave.close()
                return

            self.fileWave.close()
            self.update(True)
        else:
            self.update(False)

    def update(self, ready, status='Ready'):
        self.status(status)
        self.fileButton.setText(
            os.path.basename(self.filePath) + (' [%.3f' %
            ((self.fileSize - 44) / (self.frameRate * 2.0))) + 's ' +
            str(self.frameRate) + 'Hz]'
            if ready else 'Pick WAV file...'
        )
        self.uploadButton.setEnabled(ready)
        self.progress(0)

    def upload(self):
        self.disableButtons()
        if not os.path.exists(self.filePath):
            self.update(False, 'ERROR: File does not exist')
            self.enableButtons()
            return

        handle = PVOID()
        info = FT_PROGRAM_DATA(
            Signature1=0, Signature2=0xffffffff, Version=2,
            Manufacturer = cast(BUFFER(256), STRING),
            ManufacturerId = cast(BUFFER(256), STRING),
            Description = cast(BUFFER(256), STRING),
            SerialNumber = cast(BUFFER(256), STRING)
        )
        port = LONG()
        i = -1
        while True:
            i += 1
            if FT_Open(i, byref(handle)) != FT_OK:
                FT_Close(handle)
                break

            if (
                FT_EE_Read(handle, byref(info)) == FT_OK and
                info.Manufacturer == 'EKSELCOM' and
                info.Description == 'RS-SBI' and
                FT_GetComPortNumber(handle, byref(port)) == FT_OK
            ):
                FT_Close(handle)
                break

            FT_Close(handle)

        if port.value == 0:
            self.status('ERROR: No device found')
            self.enableButtons()
            return

        self.status('Uploading...')
        self.worker.start(port.value, self.filePath, self.fileSize)

    def disableButtons(self):
        self.fileButton.setEnabled(False)
        self.uploadButton.setEnabled(False)

    def enableButtons(self):
        self.fileButton.setEnabled(True)
        self.uploadButton.setEnabled(True)

class WorkerThread(QtCore.QThread):

    status = QtCore.pyqtSignal('QString')
    progress = QtCore.pyqtSignal(int)
    enableButtons = QtCore.pyqtSignal()

    def __init__(self, status, progress, enableButtons):
        QtCore.QThread.__init__(self)
        self.status.connect(status)
        self.progress.connect(progress)
        self.enableButtons.connect(enableButtons)
        self.modemInstance = modem.MODEM(
            lambda x: self.connection.read(x),
            lambda x: self.connection.write(x),
            lambda x: self.progress.emit(x)
        )

    def start(self, port, filePath, fileSize):
        self.port = port
        self.filePath = filePath
        self.fileSize = fileSize
        QtCore.QThread.start(self)

    def run(self):
        self.connection = Serial(
            'COM' + str(self.port), 115200, timeout=1, writeTimeout=1
        )
        self.connection.setDTR(True)
        sleep(0.1)
        self.connection.setDTR(False)
        fileHandle = open(self.filePath, 'rb')
        try:
            if self.modemInstance.send(fileHandle, self.fileSize):
                self.status.emit('Success!')
            else:
                raise Exception()
        except:
            self.status.emit('ERROR: Upload failed, try again')
            
        fileHandle.close()
        self.connection.close()
        self.enableButtons.emit()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())