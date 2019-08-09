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
        try:
            self.comport = serial.Serial(comport, 115200, timeout=1)
        except serial.SerialException as e:
            self.comport = None
            self.signal_state.emit('ERROR:' + str(e))
        self.curstate = IDLE
        self.testresult = True
        self.substate = 0
        self.testlist = {}

        self.gpiocheck_result = None
        self.macaddr = None
        self.logfile = None

    def load_testfiles(self):
        filelist = glob.glob("*.txt")
        if 'requirements.txt' in filelist:
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
                    if responsetxt is not "":
                        # Save mac address
                        if 'mac' in self.testlist[testitem]['testname']:
                            self.macaddr = responsebuffer

                        if responsetxt in responsebuffer:
                            self.testlist[testitem]['result'] = 'PASS'
                            self.signal.emit(testitem + ' ' + self.testlist[testitem]['testname'] + ' PASSED')
                            responsebuffer = ""
                            return
                        else:
                            self.testlist[testitem]['result'] = 'FAIL'
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

    def get_result_oneline(self):
        failed_list = []
        self.testlist['07'] = {
            'testname': 'gpio check',
            'result': self.gpiocheck_result
        }

        if self.macaddr is not None:
            self.test_result.emit('\n')
            for testnum in self.testlist.keys():
                if self.testlist[testnum]['result'] is 'FAIL':
                    # fail case
                    failed_list.append(self.testlist[testnum]['testname'])

            # failed list to string
            failstr = ",".join(failed_list)

            logline = "%s | %s | " % (
                time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(time.time())), self.macaddr)
            if self.testresult:
                logline = logline + 'PASS'
            else:
                logline = logline + 'FAIL' + ' | ' + failstr

            # log file 저장
            self.test_result.emit(logline)
            self.save_log_oneline(logline)
            # self.claer_objects()
        else:
            pass

    def get_result(self):
        failed_list = []
        total_result = ""
        # print('get_result()', self.testlist)

        self.testlist['07'] = {
            'testname': 'gpio check',
            'result': self.gpiocheck_result
        }

        if self.macaddr is not None:
            self.test_result.emit('\n\n')
            for testnum in self.testlist.keys():
                # all case
                # test = testnum + '_' + self.testlist[testnum]['testname']
                test = "%s | %s | %s) %-15s | %-5s" % (
                    time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(time.time())), self.macaddr,
                    testnum, self.testlist[testnum]['testname'], self.testlist[testnum]['result'])
                self.test_result.emit(test)
                print(test)
                if 'FAIL' in test:
                    total_result = total_result + test + '<<=====' + '\n'
                else:
                    total_result = total_result + test + '\n'

                if self.testlist[testnum]['result'] is 'FAIL':
                    # fail case
                    failed_list.append(test)

            # print('total_result:', total_result)
            self.save_log(total_result)
            self.claer_objects()
        else:
            pass

    def save_log_oneline(self, logtxt):
        filepath = 'logs/' + time.strftime('%Y%m', time.localtime(time.time())) + '_WizFi630S_test_oneline_log.txt'

        tested_mac_list = []

        if os.path.isfile(filepath):
            readfile = open(filepath, 'r+')
            loglines = readfile.readlines()
        else:
            readfile = open(filepath, 'w+')
            loglines = []

        if len(loglines) > 0:
            loglines[-1] = logtxt + '\n'    # last line 대체
        else:
            loglines.append(logtxt + '\n')

        print('loglines:', len(loglines), loglines)

        passnum = 0
        failnum = 0

        for line in loglines:
            if 'FAIL' in line or 'PASS' in line:
                tmp = line.split('|')
                addr = tmp[1].strip()
                if addr not in tested_mac_list:
                    result = tmp[2].strip()
                    if 'PASS' in result:
                        passnum = passnum + 1
                    else:
                        failnum = failnum + 1
                    tested_mac_list.append(addr)

        print('tested maclist', len(tested_mac_list), tested_mac_list)

        finallog = "Total: %d | Pass: %d | Fail: %d" % (passnum+failnum, passnum, failnum)
        loglines.append(finallog)

        logfile = open(filepath, 'w')
        logfile.write("".join(loglines))
        logfile.close()

    def save_log(self, logtxt):
        filepath = 'logs/' + time.strftime('%Y%m', time.localtime(time.time())) + '_WizFi630S_test_log.txt'
        self.logfile = open(filepath, 'a+')
        self.logfile.write(logtxt + '\n')

    def claer_objects(self):
        # 테스트 종료 후 clear
        print('Clear objects...')
        self.testlist = {}
        self.testresult = True
        f = open('06_test_mac_resp.txt', 'w')
        f.close()
        self.logfile.close()

    def check_barcode(self):
        macfile = open('06_test_mac_resp.txt', 'r')
        barcodemac = macfile.readline()
        if len(barcodemac) > 0:
            return True
        else:
            return False

    def stop(self):
        self.alive = False
        if self.comport is not None:
            if self.comport.isOpen():
                self.comport.close()

    def run(self):
        # self.signal.emit('%s is opened' % self.comport)

        while self.alive:
            if self.curstate is IDLE:
                self.signal.emit('새로운 모듈을 꽂았는 지 확인하세요.')
                self.signal_state.emit('IDLE')
                self.load_testfiles()
                self.curstate = READY
                # self.substate = 0
                self.substate = 3  # ! GPIO 테스트 먼저 진행
            elif self.curstate is READY:
                pass
            elif self.curstate is BOOTING:
                recv = self.comport.readline()
                if recv is not '':
                    tmprcv = recv.strip().decode("utf-8")
                    if self.substate == 0:
                        self.signal.emit(tmprcv)
                        # Booting 체크 string
                        if "Booting" in tmprcv:
                            # self.signal.emit(tmprcv)
                            self.signal_state.emit('BOOTING')
                            self.substate = 1
                    elif self.substate == 1:
                        # if "br-lan: link becomes ready" in tmprcv:
                        if "device ra0 entered promiscuous mode" in tmprcv:
                            self.signal_state.emit('NORMAL')
                            self.signal.emit(tmprcv)
                            self.comport.write(b'\r\n')
                            self.substate = 2
                        else:
                            self.signal.emit(tmprcv)
                    elif self.substate == 2:
                        self.signal.emit(tmprcv)
                        if promptstr in tmprcv:
                            self.curstate = TESTING
                            self.signal_state.emit('TESTING')
                            self.substate = 0
                    if self.substate == 3:
                        """ GPIO Check """
                        self.signal.emit(tmprcv)
                        if 'Please choose the operation' in tmprcv:
                            self.signal_state.emit('GPIO')
                            self.comport.write(b'a')

                        if 'OK' in tmprcv or 'FAIL' in tmprcv:
                            if 'OK' in tmprcv:
                                self.gpiocheck_result = 'PASS'
                            elif 'FAIL' in tmprcv:
                                self.gpiocheck_result = 'FAIL'
                                self.testresult = False
                            # 테스트가 끝나면 \n 입력
                            self.substate = 0
                            self.comport.write(b'\n')
                            self.comport.write(b'\n')

            elif self.curstate is TESTING:
                try:
                    for testitem in self.testlist.keys():
                        self.signal.emit(
                            '===============' + testitem + ' ' + self.testlist[testitem]['testname'] + ' is starting ===============')
                        #! 06_test_mac 테스트 시 체크:
                        # 바코드가 찍히지 않은 경우, 테스트 일시 중단 & 파일 체크
                        if 'mac' in self.testlist[testitem]['testname']:
                            while not self.check_barcode():
                                self.signal_state.emit('BARCODE NOT READ')
                            self.signal_state.emit('TESTING')

                        print('TESTING Check', self.testlist[testitem])
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
                except Exception as e:
                    print('comthread TESTING error', e)

                # ? 하나라도 Fail이 발생하면 Fail로 판단
                if self.testresult:
                    self.signal_state.emit('PASSED')
                else:
                    self.signal_state.emit('FAILED')

                self.signal.emit('ALL test was done')
                # 테스트 결과 확인/출력
                self.get_result_oneline()
                self.get_result()
                self.curstate = IDLE

        self.signal.emit('comthread is stopped')
