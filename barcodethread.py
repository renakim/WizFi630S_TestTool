import time
import threading
import serial
import os
import glob

from PyQt5 import QtCore


class barcodethread(QtCore.QThread):
    barcode_signal = QtCore.pyqtSignal(str)
    start_signal = QtCore.pyqtSignal(str)

    def __init__(self, comport):
        QtCore.QThread.__init__(self)

        self.alive = True
        self.init_file()
        self.isread_mac = False
        self.curstate = ""

        # barcode 기기 연결 port
        self.comport = serial.Serial(comport, 115200, timeout=1)

    def init_file(self):
        # 파일 내용 초기화
        f = open('06_test_mac_resp.txt', 'w')
        f.close()

    def write_macaddr(self, addr):
        f = open('06_test_mac_resp.txt', 'w')
        f.write(addr)
        f.close()

    def run(self):
        while self.alive:
            try:
                if self.start_signal:
                    pass
                if self.comport.isOpen():
                    recvline = self.comport.readline()
                    if recvline.decode() is not "":
                        curr_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                        logtxt = "[%s] %s" % (curr_time, recvline.decode())
                        print('barcode mac address', logtxt)
                        self.isread_mac = True
                        self.write_macaddr(recvline.decode())
                        self.barcode_signal.emit(logtxt)
            except Exception as e:
                print('barcodethread', e)

    def stop(self):
        self.init_file()
        self.alive = False
        if self.comport.isOpen():
            self.comport.close()
