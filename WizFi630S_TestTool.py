import wx

import myFrame

class ToolFrame(myFrame.MyFrame1):
    def __init__(self, parent):
        myFrame.MyFrame1.__init__(self, parent)


app = wx.App(False)
frame = ToolFrame(None)
frame.Show(True)
app.MainLoop()        