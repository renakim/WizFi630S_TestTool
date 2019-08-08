import time
import threading
import serial
import os
import glob
import re

from PyQt5 import QtCore


class barcodethread(QtCore.QThread):
    barcode_signal = QtCore.pyqtSignal(str)
    barcode_state_signal = QtCore.pyqtSignal(str)

    def __init__(self, comport):
        QtCore.QThread.__init__(self)

        self.alive = True
        self.claer_file()
        self.macaddr = None

        # barcode 기기 연결 port
        self.comport = serial.Serial(comport, 115200, timeout=1)

        self.barcodelog = None

        # START / FORCE (invalid mac 일때 사용자 요청에 의해 강제 진행)
        self.curstate = 'START'

    def claer_file(self):
        f = open('06_test_mac_resp.txt', 'w')
        f.close()

    def write_macaddr(self):
        if self.macaddr is not None:
            f = open('06_test_mac_resp.txt', 'w')
            f.write(self.macaddr)
            f.close()

    def save_barcodelog(self, logtxt):
        filepath = 'logs/' + time.strftime('%Y%m', time.localtime(time.time())) + '_WizFi630S_barcode_log.txt'

        if os.path.isfile(filepath):
            self.barcodelog = open(filepath, 'a+')
        else:
            self.barcodelog = open(filepath, 'w+')

        self.barcodelog.write(logtxt + '\n')
        self.barcodelog.close()

    def isvalid_mac(self, addr):
        """ mac 형태 변환 후 올바른 값인지 확인 """
        # 0008DCAABBCC > 00:08:DC:AA:BB:CC
        self.macaddr = ":".join([addr[i:i+2] for i in range(0, len(addr), 2)])
        macexpr = "^([0-9a-fA-F]{2}:){5}([0-9a-fA-F]{2})$"
        prog = re.compile(macexpr)
        if prog.match(self.macaddr):
            print("Valid Mac: %s\r\n" % self.macaddr)
            return True
        else:
            print("Invalid Mac: %s\r\n" % self.macaddr)
            return False

    def run(self):
        while self.alive:
            try:
                if self.comport.isOpen():
                    if 'FORCE' in self.curstate:
                        # main signal -> invlid mac이지만, 어쩔수 없는 경우 진행
                        # 예: 바코드 자체가 잘못되었을 때
                        self.write_macaddr()

                    recvline = self.comport.readline()
                    if recvline.decode() is not "":
                        self.macaddr = recvline.decode().strip()
                        curr_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                        logtxt = "[%s] %s" % (curr_time, self.macaddr)
                        print('barcode mac address', logtxt)
                        if self.isvalid_mac(self.macaddr):
                            self.write_macaddr()
                        else:
                            self.barcode_state_signal.emit('INVALID_' + self.macaddr)
                            logtxt = logtxt + ' ** Invalid Mac'

                        self.barcode_signal.emit(logtxt)
                        self.save_barcodelog(logtxt)

            except Exception as e:
                print('barcodethread', e)

    def stop(self):
        self.claer_file()
        self.alive = False
        if self.comport.isOpen():
            self.comport.close()
