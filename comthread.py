import sys
import time
import threading
import serial
import os
import glob

from io import StringIO
from PyQt5 import QtCore

IDLE = 0
READY = 1
BOOTING = 2
TESTING = 3
NORMAL = 4

promptstr = 'root@wizfi630s:/#'


class comthread(QtCore.QThread):
    signal = QtCore.pyqtSignal(str)
    signal_state = QtCore.pyqtSignal(str)
    test_result = QtCore.pyqtSignal(str)

    def __init__(self, comport, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.alive = True
        self.source_txt = ''
        self.comport = serial.Serial(comport, 115200, timeout=1)  # exception 추가?
        self.curstate = IDLE
        self.testresult = True
        self.substate = 0
        self.testlist = {}

        # Final result log
        self.total_result = {}

    def load_testfiles(self):
        filelist = glob.glob("*.txt")
        # ! 예외 파일 제거 / 하위 폴더 사용?
        filelist.remove('requirements.txt')
        # filelist = glob.glob("testfiles/*.txt")
        for file in filelist:
            items = file.split('.')[0].split('_')
            # print(items[0], ' '.join(txt for txt in items[1:len(items)-1]), items[len(items) - 1])

            if items[0] not in self.testlist.keys():
                testitem = {}
                testitem['testname'] = ' '.join(txt for txt in items[1:len(items)-1])
                testitem['req'] = ""
                testitem['resp'] = ""
                # result 추가
                testitem['result'] = None
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

        # print("load_testfiles()", self.testlist)

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
                    # ? 명령을 여러 번 입력해야 결과가 발생하는 case
                    if responsetxt is not "":
                        if responsetxt in responsebuffer:
                            # ! 결과 추가
                            self.testlist[testitem]['result'] = 'pass'
                            self.signal.emit(testitem + ' ' + self.testlist[testitem]['testname'] + ' PASSED')
                            responsebuffer = ""
                            return
                        else:
                            # !
                            self.testlist[testitem]['result'] = 'fail'
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

    def get_result(self):
        fail_list = []
        # print('get_result()', self.testlist)
        for testnum in self.testlist.keys():
            # all case
            # test = testnum + '_' + self.testlist[testnum]['testname']
            test = "[%s][00:08:DC:AA:BB:CC] %s) %-15s | %-5s" % (
                time.strftime('%c', time.localtime(time.time())),
                testnum, self.testlist[testnum]['testname'], self.testlist[testnum]['result'])
            self.test_result.emit(test)
            print(test)

            if self.testlist[testnum]['result'] is 'fail':
                # fail case
                fail_list.append(test)
        print('get_result:failcase:', fail_list)

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
                self.substate = IDLE
            elif self.curstate is READY:
                pass
            elif self.curstate is BOOTING:
                recv = self.comport.readline()
                if recv is not '':
                    tmprcv = recv.strip().decode("utf-8")
                    if self.substate == IDLE:
                        self.signal.emit(tmprcv)
                        # if "REBOOT" in tmprcv:
                        # 부팅 체크 string 변경
                        if "Booting" in tmprcv:
                            # self.signal.emit(tmprcv)
                            self.signal_state.emit('BOOTING')
                            self.substate = READY
                    elif self.substate == READY:
                        # 체크 메시지 변경
                        # if "br-lan: link becomes ready" in tmprcv:
                        if "device ra0 entered promiscuous mode" in tmprcv:
                            self.signal_state.emit('NORMAL')
                            self.signal.emit(tmprcv)
                            self.comport.write(b'\r\n')
                            self.substate = BOOTING
                        else:
                            self.signal.emit(tmprcv)
                    elif self.substate == BOOTING:
                        self.signal.emit(tmprcv)
                        if "root@wizfi630s:" in tmprcv:
                            self.curstate = TESTING
                            self.signal_state.emit('TESTING')
                            self.substate = IDLE
            elif self.curstate is TESTING:
                #! 06_test_mac 테스트 시 체크:
                # 바코드가 찍히지 않았다면 메시지 띄움
                # thread 시그널 또는 파일 체크
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
                            if index < (len(cmdlines) - 1):
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

                # ? 하나라도 Fail이 발생하면 Fail로 판단
                if self.testresult:
                    self.signal_state.emit('PASSED')
                else:
                    self.signal_state.emit('FAILED')

                self.signal.emit('ALL test was done')
                # ! 테스트 결과 확인/출력
                self.get_result()
                self.curstate = IDLE

        self.signal.emit('comthread is stopped')
