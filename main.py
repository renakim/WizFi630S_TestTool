import sys
import time
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import pyqtSignal

from comthread import comthread
from barcodethread import barcodethread
import serial
import serial.tools.list_ports

import logging

IDLE = 0
READY = 1
BOOTING = 2
TESTING = 3
NORMAL = 4
GPIOCHECK = 5


def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# Load ui file
main_dialog = uic.loadUiType(resource_path('./mainwindow.ui'))[0]


class AppWindow(QMainWindow, main_dialog):
    sig = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.iscomportopened = False
        self.isopened_barcodeport = False

        """comboBox control 초기화"""
        self.initComboBox(self.combobox_devport)

        # For barcode serial port connetion
        self.initComboBox(self.combobox_barcode)

        """ rescan pushbutton과 Event handler를 연결한다. """
        self.rescanbutton.clicked.connect(self.rescanButtonPressed)

        """ Comport Open pushbutton과 Event handler를 연결한다."""
        self.button_open_devport.clicked.connect(self.openButtonPressed)

        """ 바코드 기기 연결 포트 handler """
        self.button_open_barcodeport.clicked.connect(self.openBarcodeButtonPressed)

        """ Test start pushbutton과 Event handler를 연결한다."""
        self.startbutton.clicked.connect(self.startButtonPressed)
        self.startbutton.setEnabled(False)

        """ Label message를 읽어온다. """
        self.msglabel.setText('Ready')

        """ Clear buttons """
        self.button_clear_log.clicked.connect(self.clear_log)
        self.button_clear_barcodelog.clicked.connect(self.clear_barcodelog)
        self.button_clear_result.clicked.connect(self.clear_result)

        # logTextBox = QPlainTextEditLogger()
        # logging.getLogger().addHandler(logTextBox)
        # logging.getLogger().setLevel(logging.DEBUG)

        """ Com Port 처리용 Thread 생성 """
        self.comthread = None

        """ Barcode 기기 연결 com port """
        self.barcodethread = None

    """ 콤보박스에 아이템 입력 """

    def initComboBox(self, combobox):
        comportlist = [comport.device for comport in serial.tools.list_ports.comports()]
        for i in range(len(comportlist)):
            try:
                ser = serial.Serial(comportlist[i], 9600, timeout=1)
                ser.close()
                combobox.addItem(comportlist[i])
            except serial.SerialException as e:
                sys.stdout.write(str(e))

    """ rescan pushbutton용 Event handler"""

    def rescanButtonPressed(self):
        self.combobox_devport.clear()
        self.initComboBox(self.combobox_devport)

    """ open pushbutton용 Event handler"""

    def openButtonPressed(self):
        if self.iscomportopened is False:
            """ open com port """
            self.iscomportopened = True
            self.logtextedit.appendPlainText('=============== Comport is opened ===============')
            self.comthread = comthread(self.combobox_devport.currentText())
            # self.sig.connect(self.comthread.on_source)
            # self.sig.emit('start thread')
            self.comthread.start()
            self.comthread.signal.connect(self.appendlogtext)
            self.comthread.signal_state.connect(self.statehandler)
            # ! test result
            self.comthread.test_result.connect(self.append_resulttext)
            self.button_open_devport.setText('Close')
        else:
            """ close com port """
            self.iscomportopened = False
            self.logtextedit.appendPlainText('=============== Comport is closed ===============')
            self.comthread.stop()
            # self.sig.emit('stop thread')
            self.button_open_devport.setText('Open')

    def openBarcodeButtonPressed(self):
        if self.isopened_barcodeport is False:
            self.isopened_barcodeport = True
            self.logtextedit_barcode.appendPlainText('Barcode comport is opened')
            self.barcodethread = barcodethread(self.combobox_barcode.currentText())
            self.barcodethread.start()
            self.barcodethread.barcode_signal.connect(self.appendbarcodelog)
            self.button_open_barcodeport.setText('Close\n(barcode)')
        else:
            self.isopened_barcodeport = False
            self.logtextedit_barcode.appendPlainText('Barcode comport is closed')
            if self.barcodethread is not None:
                self.barcodethread.stop()
            # self.sig.emit('stop thread')
            self.button_open_barcodeport.setText('Open(barcode)')

    def appendbarcodelog(self, logtxt):
        self.logtextedit_barcode.appendPlainText(logtxt)

    def startButtonPressed(self):
        self.comthread.curstate = BOOTING
        self.startbutton.setEnabled(False)

    def appendlogtext(self, logtxt):
        # print(len(logtxt), logtxt)
        # ? logtextedit 줄바꿈 방지
        if len(logtxt) > 0:
            self.logtextedit.appendPlainText(logtxt)

    def append_resulttext(self, resulttext):
        self.textedit_result.appendPlainText(resulttext)

    def statehandler(self, statetxt):
        print('statehandler()', statetxt.encode())
        if "FAILED" in statetxt:
            """ Start button을 Enable 시키고 Label에 'FAILED'를 표시한다. """
            self.msglabel.setStyleSheet('color: red')
            self.msglabel.setText('FAILED')
            self.startbutton.setEnabled(True)
        elif "PASSED" in statetxt:
            """ Start button을 Enable 시키고 Label에 'PASSED'를 표시한다. """
            self.msglabel.setStyleSheet('color: green')
            self.msglabel.setText('PASSED')
            self.startbutton.setEnabled(True)
        elif "BOOTING" in statetxt:
            """ Label에 'BOOTING'을 표시한다. """
            self.msglabel.setStyleSheet('color: blue')
            self.msglabel.setText('BOOTING...')
        elif "TESTING" in statetxt:
            """ Label에 'TESTING...'을 표시한다. """
            self.msglabel.setStyleSheet('color: blue')
            self.msglabel.setText('TESTING...')
        elif "IDLE" in statetxt:
            """ Start button을 Enable 시킨다. """
            self.startbutton.setEnabled(True)
        elif "GPIO" in statetxt:
            """ """
            self.msglabel.setStyleSheet('color: green')
            self.msglabel.setText('GPIO CHECKING...')
        else:
            self.startbutton.setEnabled(False)

    def clear_log(self):
        self.logtextedit.setPlainText("")

    def clear_barcodelog(self):
        self.logtextedit_barcode.setPlainText("")

    def clear_result(self):
        self.textedit_result.setPlainText("")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    maindialog = AppWindow()
    maindialog.show()
    app.exec_()
