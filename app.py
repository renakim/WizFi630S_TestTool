import sys
from PyQt5 import QtWidgets, uic
from PyQt5 import uic
from dialog import MyDialog
import serial
import serial.tools.list_ports

class AppWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi('dialog.ui', self)
        self.comboBox = self.findChild(QtWidgets.QComboBox, 'comboBox')
        self.initComboBox(self.comboBox)


        self.rescanbutton = self.findChild(QtWidgets.QPushButton, 'pushButton')
        self.rescanbutton.clicked.connect(self.rescanButtonPressed)
        self.show()

    def initComboBox(self, combobox):
        comportlist = [comport.device for comport in serial.tools.list_ports.comports()]
        for i in range(len(comportlist)):
            combobox.addItem(comportlist[i])

    def rescanButtonPressed(self):
        self.comboBox.clear()
        self.initComboBox(self.comboBox)

app = QtWidgets.QApplication(sys.argv)
w = AppWindow()
w.show()
sys.exit(app.exec_())