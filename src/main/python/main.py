import sys
import time
import os
import logging

from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5.QtCore import pyqtSignal
import serial
import serial.tools.list_ports

from comthread import comthread
from barcodethread import barcodethread

IDLE = 0
READY = 1
BOOTING = 2
TESTING = 3
NORMAL = 4
GPIOCHECK = 5

VERSION = 'V0.9.0'


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

        self.setWindowTitle('WIZnet WizFi630S Test Tool ' + VERSION)

        self.iscomportopened = False
        self.isopened_barcodeport = False

        """ comboBox control 초기화 """
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

        """ log directory 생성 """
        self.make_logdir()

    def make_logdir(self):
        logdir = "./logs"
        if not os.path.isdir(logdir):
            os.mkdir(logdir)

    def initComboBox(self, combobox):
        """ 콤보박스에 아이템 입력 """
        comportlist = [comport.device for comport in serial.tools.list_ports.comports()]
        for i in range(len(comportlist)):
            try:
                ser = serial.Serial(comportlist[i], 9600, timeout=1)
                ser.close()
                combobox.addItem(comportlist[i])
            except serial.SerialException as e:
                sys.stdout.write(str(e))

    def check_port(self, port):
        if port == "":
            self.msgbox_error("There is no available port.\bPlease use rescan button.")
            return False
        else:
            try:
                ser = serial.Serial(port, 115200, timeout=1)
                ser.close()
                return True
            except serial.SerialException as e:
                sys.stdout.write('check_port() {}'.format(e))
                return False

    def rescanButtonPressed(self):
        """ rescan pushbutton용 Event handler """
        # ! 기존 연결 close
        # if self.comthread is not None:
        #     self.comthread.stop()
        # if self.barcodethread is not None:
        #     self.barcodethread.stop()

        self.combobox_devport.clear()
        self.combobox_barcode.clear()
        self.initComboBox(self.combobox_devport)
        self.initComboBox(self.combobox_barcode)

    def openButtonPressed(self):
        """ open pushbutton용 Event handler """
        try:
            if self.iscomportopened is False:
                if not self.check_port(self.combobox_devport.currentText()):
                    self.logtextedit.appendPlainText('[ERROR] Cannot open port. Please use Rescan button.')
                    return

                """ open com port """
                self.iscomportopened = True
                self.comthread = comthread(self.combobox_devport.currentText())
                self.comthread.signal.connect(self.appendlogtext)
                self.comthread.signal_state.connect(self.statehandler)
                self.comthread.start()

                # ! test result
                self.comthread.test_result.connect(self.append_resulttext)
                self.logtextedit.appendPlainText('[INFO] Comport is opened')
                self.button_open_devport.setText('Close')
            else:
                """ close com port """
                self.iscomportopened = False
                self.comthread.stop()
                self.logtextedit.appendPlainText('[INFO] Comport is closed')
                self.button_open_devport.setText('Open')
            self.enable_rescanbtn()
        except Exception as e:
            print('ERROR: openButtonPressed:', e)

    def openBarcodeButtonPressed(self):
        """ Barcode port open button """
        try:
            if self.isopened_barcodeport is False:
                if not self.check_port(self.combobox_barcode.currentText()):
                    self.logtextedit_barcode.appendPlainText(
                        '[ERROR] Cannot open port. Please use Rescan button.')
                    return
                self.isopened_barcodeport = True
                self.barcodethread = barcodethread(self.combobox_barcode.currentText())
                self.barcodethread.start()
                self.barcodethread.barcode_signal.connect(self.appendbarcodelog)
                self.barcodethread.barcode_state_signal.connect(self.barcode_statehandler)
                self.button_open_barcodeport.setText('Close\n(barcode)')
                self.logtextedit_barcode.appendPlainText('[INFO] Barcode comport is opened')
                self.enable_startbtn()
            else:
                self.isopened_barcodeport = False
                self.barcodethread.stop()
                self.logtextedit_barcode.appendPlainText('[INFO] Barcode comport is closed')
                self.button_open_barcodeport.setText('Open\n(barcode)')
            self.enable_rescanbtn()
        except Exception as e:
            print('ERROR: openBarcodeButtonPressed:', e)
            self.logtextedit.appendPlainText('[ERROR] barcode port open error')

    def enable_startbtn(self):
        if self.iscomportopened and self.isopened_barcodeport:
            self.startbutton.setEnabled(True)

    def enable_rescanbtn(self):
        if not self.iscomportopened and not self.isopened_barcodeport:
            self.rescanbutton.setEnabled(True)
        else:
            self.rescanbutton.setEnabled(False)

    def appendbarcodelog(self, logtxt):
        self.logtextedit_barcode.appendPlainText(logtxt)

    def startButtonPressed(self):
        self.startbutton.setEnabled(False)
        self.comthread.curstate = BOOTING
        self.barcodethread.curstate = 'START'

    def appendlogtext(self, logtxt):
        # print(len(logtxt), logtxt)
        # ? logtextedit 줄바꿈 방지
        if len(logtxt) > 0:
            self.logtextedit.appendPlainText(logtxt)

    def append_resulttext(self, resulttext):
        self.textedit_result.appendPlainText(resulttext)

    def statehandler(self, statetxt):
        # print('statehandler()', statetxt.encode())
        if "FAILED" in statetxt:
            """ Start button을 Enable 시키고 Label에 'FAILED'를 표시한다. """
            self.msglabel.setStyleSheet('color: red')
            self.msglabel.setText('FAILED')
            self.startbutton.setEnabled(True)
            # ! barcodethread로 종료 신호
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
            # self.startbutton.setEnabled(True)
            self.enable_startbtn()
        elif "GPIO" in statetxt:
            """ """
            self.msglabel.setStyleSheet('color: green')
            self.msglabel.setText('GPIO CHECKING...')
        elif "BARCODE" in statetxt:
            # !
            """ 바코드를 찍지 않은 경우 메시지를 띄움 """
            self.msglabel.setStyleSheet('color: red')
            self.msglabel.setText('READ BARCODE! TEST PAUSED...')
        elif "ERROR" in statetxt:
            self.msgbox_error(statetxt)
        else:
            self.startbutton.setEnabled(False)

    def barcode_statehandler(self, statetxt):
        """ barcode reader handler """
        if 'INVALID' in statetxt:
            txt = statetxt.split('_')
            self.msgbox_invalidmac(txt)

    def msgbox_error(self, errtxt):
        """ Error Messagebox """
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Warning)
        msgbox.setWindowTitle("Error")
        msgbox.setText(errtxt)
        msgbox.exec_()

    def msgbox_invalidmac(self, txt):
        """ 바코드 리더에서 잘못된 값이 들어왔을 때 """
        msgbox = QMessageBox(self)
        reply = msgbox.question(
            self, 'Warning',
            'Invalid mac address: %s\nRetry to read barcode.\nIf press "No" button, use invalid address.' % txt[1],
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            pass
        else:
            # Invalid mac으로 테스트 진행
            self.barcodethread.curstate = 'FORCE'

    def clear_log(self):
        self.logtextedit.setPlainText("")

    def clear_barcodelog(self):
        self.logtextedit_barcode.setPlainText("")

    def clear_result(self):
        self.textedit_result.setPlainText("")


if __name__ == '__main__':
    # for fbs
    appctxt = ApplicationContext()
    maindialog = AppWindow()
    maindialog.show()
    sys.exit(appctxt.app.exec_())

    # for Pyinstaller
    # app = QApplication(sys.argv)
    # maindialog = AppWindow()
    # maindialog.show()
    # app.exec_()
