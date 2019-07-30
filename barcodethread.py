import time
import threading
import serial
import os
import glob

from PyQt5 import QtCore


class barcodethread(QtCore.QThread):
    barcode_signal = QtCore.pyqtSignal(str)

    def __init__(self, comport):
        QtCore.QThread.__init__(self)

        self.init_respfile()

        self.isread_macaddr = False

        # barcode 기기 연결 port
        self.comport = serial.Serial(comport, 115200, timeout=1)

    def init_respfile(self):
        # 파일 내용 초기화
        f = open('06_test_mac_resp.txt', 'w')
        f.close()

    def write_macaddr(self):
        pass

    def run(self):
        while not self.isread_macaddr:
            try:
                recvline = self.comport.readline()
                if recvline.decode() is not "":
                    curr_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    logtxt = "%s: %s" % (curr_time, recvline.decode())
                    print('barcode mac address', logtxt)
                    self.if_read = True
                    self.barcode_signal.emit(logtxt)
            except Exception as e:
                print(e)

    def stop(self):
        if self.comport.isOpen():
            self.comport.close()
