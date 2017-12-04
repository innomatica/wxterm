#!/usr/bin/env python3

################################################################################
#
#   \file
#   \author     <a href="http://www.innomatic.ca">innomatic</a>
#   \brief      UART port sniffer
#
import serial
import sys
import _thread
import wx
import wx.lib.newevent

# import ComThread and TermPanel
from wxterm import *


#--------1---------2---------3---------4---------5---------6---------7---------8
## Main frame window
#
class MyFrame(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title)

        # populate two terminal panels
        self.pnlTerm1 = TermPanel(self, serial.Serial())
        self.pnlTerm2 = TermPanel(self, serial.Serial())

        # set RX only mode
        self.pnlTerm1.SetRxOnly()
        self.pnlTerm2.SetRxOnly()

        # sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.pnlTerm1, 1, wx.EXPAND)
        self.sizer.Add(self.pnlTerm2, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        self.Show()


#--------1---------2---------3---------4---------5---------6---------7---------8
if __name__=="__main__":

    app = wx.App()
    frame = MyFrame(None, "UART Sniffer")
    app.MainLoop()
