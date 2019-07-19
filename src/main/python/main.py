import sys, time

from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5 import QtWidgets, uic, QtCore
from dialog import MyDialog
from comthread import comthread
import serial
import serial.tools.list_ports

import logging

IDLE = 0
READY = 1
BOOTING = 2
TESTING = 3

# class QPlainTextEditLogger(logging.Handler):
#     def __init__(self):
#         super().__init__()
#         self.widget = QtWidgets.QPlainTextEdit()
#         self.widget.setReadOnly(True)

#     def emit(self, record):
#         msg = self.format(record)
#         self.widget.appendPlainText(msg)

# class AppWindow(QtWidgets.QDialog, QPlainTextEditLogger):
class AppWindow(QtWidgets.QDialog):
    sig = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        uic.loadUi('dialog.ui', self)

        self.iscomportopened = False
        '''comboBox control 초기화'''
        self.comboBox = self.findChild(QtWidgets.QComboBox, 'comboBox_Comport')
        self.initComboBox(self.comboBox)

        '''rescan pushbutton과 Event handler를 연결한다'''
        self.rescanbutton = self.findChild(QtWidgets.QPushButton, 'pushButton_Rescan')
        self.rescanbutton.clicked.connect(self.rescanButtonPressed)
        self.show()

        ''' Comport Open pushbutton과 Event handler를 연결한다.'''
        self.openbutton = self.findChild(QtWidgets.QPushButton, 'pushButton_Open')
        self.openbutton.clicked.connect(self.openButtonPressed)
        self.show()

        ''' Test start pushbutton과 Event handler를 연결한다.'''
        self.startbutton = self.findChild(QtWidgets.QPushButton, 'pushButton_Start')
        self.startbutton.clicked.connect(self.startButtonPressed)
        self.startbutton.setEnabled(False)
        self.show()

        ''' Label message를 읽어온다. '''
        self.msglabel = self.findChild(QtWidgets.QLabel, 'label_message')
        self.msglabel.setText('Ready')
        self.show()

        ''' Plain Text Edit '''
        self.logtextedit = self.findChild(QtWidgets.QPlainTextEdit, 'plainTextEdit_log')
        self.show()
        # logTextBox = QPlainTextEditLogger()
        # logging.getLogger().addHandler(logTextBox)
        # logging.getLogger().setLevel(logging.DEBUG)

        ''' Com Port 처리용 Thread 생성 '''
        self.comthread = None

    ''' 콤보박스에 아이템 입력 '''
    def initComboBox(self, combobox):
        comportlist = [comport.device for comport in serial.tools.list_ports.comports()]
        for i in range(len(comportlist)):
            try:
                ser = serial.Serial(comportlist[i], 9600, timeout=1)
                ser.close()
                combobox.addItem(comportlist[i])
            except serial.SerialException as e:
                sys.stdout.write(str(e))

    ''' rescan pushbutton용 Event handler'''
    def rescanButtonPressed(self):
        self.comboBox.clear()
        self.initComboBox(self.comboBox)

    ''' open pushbutton용 Event handler'''
    def openButtonPressed(self):
        if self.iscomportopened is False:
            ''' open com port '''
            self.iscomportopened = True
            self.logtextedit.appendPlainText('Comport is opened')
            self.comthread = comthread(self.comboBox.currentText())
            # self.sig.connect(self.comthread.on_source)
            # self.sig.emit('start thread')
            self.comthread.start()
            self.comthread.signal.connect(self.appendlogtext)
            self.comthread.signal_state.connect(self.statehandler)
            self.openbutton.setText('Close')
        else:
            ''' close com port '''
            self.iscomportopened = False
            self.logtextedit.appendPlainText('Comport is closed')
            self.comthread.stop()
            # self.sig.emit('stop thread')
            self.openbutton.setText('Open')

    def startButtonPressed(self):
        self.comthread.curstate = BOOTING
        self.startbutton.setEnabled(False)

    def appendlogtext(self, logtxt):
        # self.logtextedit.appendPlainText(str(logtxt))
        self.logtextedit.appendPlainText(logtxt)

    def statehandler(self, statetxt):
        # print(statetxt.encode())
        if "FAILED" in statetxt:
            ''' Start button을 Enable 시키고 Label에 'FAILED'를 표시한다. '''
            self.msglabel.setStyleSheet('color: red')
            self.msglabel.setText('FAILED')
            self.startbutton.setEnabled(True)
            pass
        elif "PASSED" in statetxt:
            ''' Start button을 Enable 시키고 Label에 'PASSED'를 표시한다. '''
            self.msglabel.setStyleSheet('color: green')
            self.msglabel.setText('PASSED')
            self.startbutton.setEnabled(True)
            pass
        elif "BOOTING" in statetxt:
            ''' Label에 'BOOTING'을 표시한다. '''
            self.msglabel.setStyleSheet('color: blue')
            self.msglabel.setText('BOOTING...')
            pass
        elif "TESTING" in statetxt:
            ''' Label에 'TESTING...'을 표시한다. '''
            self.msglabel.setStyleSheet('color: blue')
            self.msglabel.setText('TESTTING...')
            pass
        elif "IDLE" in statetxt:
            ''' Start button을 Enable 시킨다. '''
            self.startbutton.setEnabled(True)
            pass
        else:
            self.startbutton.setEnabled(False)
            pass
if __name__ == '__main__':

    appctxt = ApplicationContext()
    w = AppWindow()
    w.show()
    sys.exit(appctxt.app.exec_())
