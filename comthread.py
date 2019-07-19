import sys
import time
import threading
import serial
import os, glob

from io import StringIO
from PyQt5 import QtCore


IDLE = 0
READY = 1
BOOTING = 2
TESTING = 3


promptstr = 'root@wizfi630s:/#'

class comthread(QtCore.QThread):
    signal = QtCore.pyqtSignal(str)
    signal_state = QtCore.pyqtSignal(str)

    def __init__(self, comport, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.alive = True
        self.source_txt = ''
        self.comport = serial.Serial(comport, 115200, timeout=1) # exception 추가?
        self.curstate = IDLE
        self.testresult = True
        self.substate = 0
        self.testlist = {}

    def load_testfiles(self):
        filelist = glob.glob("*.txt")
        for file in filelist:
            items = file.split('.')[0].split('_')
            # print(items[0], ' '.join(txt for txt in items[1:len(items)-1]), items[len(items) - 1])
            
            if items[0] not in self.testlist.keys():
                testitem = {}
                testitem['testname'] = ' '.join(txt for txt in items[1:len(items)-1])
                testitem['req'] = ""
                testitem['resp'] = ""
                if 'req' in items[len(items) - 1]:
                    testitem['req'] = file
                elif 'resp' in items[len(items) - 1]:
                    testitem['resp'] = file
                self.testlist[items[0]] = testitem

            else:
                if 'req' in items[len(items) - 1]:
                    self.testlist[items[0]]['req'] = file
                elif 'resp' in items[len(items) - 1]:
                    self.testlist[items[0]]['resp'] = file

    def responsecheck(self, cmdtxt, responsetxt, testitem):
        responsebuffer = ""
        while True:
            try:
                recvline = self.comport.readline()
                print(recvline.strip().decode('utf-8'))
                tmprcv = recvline.strip().decode('utf-8')
                self.signal.emit(tmprcv)
                if cmdtxt in tmprcv:
                    pass
                elif promptstr in tmprcv:
                    if responsetxt is not "":
                        if responsetxt in responsebuffer:
                            self.signal.emit(testitem + ' ' + self.testlist[testitem]['testname'] + ' PASSED')
                            responsebuffer = ""
                            return
                        else:
                            self.signal.emit(testitem + ' ' + self.testlist[testitem]['testname'] + ' FAILED')
                            self.testresult = False
                            responsebuffer = ""
                            return
                    else:
                        if tmprcv.split(promptstr)[1] is "":
                            return
                            
                else:
                    responsebuffer += tmprcv
            except serial.SerialException as e:
                sys.stdout.write(str(e))

    def stop(self):
        self.alive = False
        if self.comport.isOpen():
            self.comport.close()

    def run(self):
        # self.signal.emit('%s is opened' % self.comport)

        while self.alive:
            if self.curstate is IDLE:
                self.signal.emit('새로운 모듈을 꽂았는 지 확인하시오.')
                self.signal_state.emit('IDLE')
                self.load_testfiles()
                self.curstate = READY
                self.substate = 0
            elif self.curstate is READY:
                pass
            elif self.curstate is BOOTING:
                recv = self.comport.readline()
                if recv is not '':
                    tmprcv = recv.strip().decode("utf-8")
                    if self.substate == 0:
                        self.signal.emit(tmprcv)
                        if "REBOOT" in tmprcv:
                            # self.signal.emit(tmprcv)
                            self.signal_state.emit('BOOTING')
                            self.substate = 1
                    elif self.substate == 1:
                        if "br-lan: link becomes ready" in tmprcv:
                            self.signal.emit(tmprcv)
                            self.comport.write(b'\r\n')
                            self.substate = 2
                        else:
                            self.signal.emit(tmprcv)
                    elif self.substate == 2:
                        self.signal.emit(tmprcv)
                        if "root@wizfi630s:" in tmprcv:
                            self.curstate = TESTING
                            self.signal_state.emit('TESTING')
                            self.substate = 0
            elif self.curstate is TESTING:
                for testitem in self.testlist.keys():
                    self.signal.emit(testitem + ' ' + self.testlist[testitem]['testname'] + ' is starting')
                    cmdfile = open(self.testlist[testitem]['req'], "r")
                    respfile = open(self.testlist[testitem]['resp'], "r")
                    responsetxt = respfile.readline()
                    responsetxt = responsetxt.strip()
                    # self.signal.emit(responsetxt)
                    cmdlines = cmdfile.readlines()
                    if len(cmdlines) > 1:
                        for index, line in enumerate(cmdlines):
                            print(index, line, sep=' ')
                            print(line.encode())
                            self.comport.write(line.encode())
                            recvline = self.comport.readline()
                            print(recvline.strip().decode('utf-8'))
                            self.signal.emit(recvline.strip().decode('utf-8'))
                            self.comport.write(b'\n')
                            if index < (len(cmdlines) - 1 ):
                                self.responsecheck(line, "", testitem)
                            else:
                                self.responsecheck(line, responsetxt, testitem)
                            time.sleep(1)
                    else:
                        line = cmdlines[0]
                        # line += '\r\n'
                        self.comport.write(line.encode())
                        recvline = self.comport.readline()
                        # print(recvline)
                        self.signal.emit(recvline.strip().decode('utf-8'))
                        self.comport.write(b'\r\n')
                        self.responsecheck(line, responsetxt, testitem)   
                        time.sleep(1)

                if self.testresult:
                    self.signal_state.emit('PASSED')
                else:
                    self.signal_state.emit('FAILED')

                self.signal.emit('ALL test was done')
                self.curstate = IDLE

        self.signal.emit('comthread is stopped')

