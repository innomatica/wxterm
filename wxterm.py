#!/usr/bin/env python3

################################################################################
#
#   \file
#   \author     <a href="http://www.innomatic.ca">innomatic</a>
#   \brief      wxPython Terminal Window
#

import os
import pickle
import serial
import _thread
import wx
import wx.lib.newevent
from SerialCom import *

# new event class for the COM thread
(UpdateComData, EVT_UPDATE_COMDATA) = wx.lib.newevent.NewEvent()


# default data file name
data_file = 'wxpyterm.dat'

## Return (default) monospace font face name depending on the OS.
#
def GetMonoFont():
    # do not consider the case of osx
    if os.name == 'posix':
        # fc-match will give default monospace font name
        a = os.popen('fc-match "Monospace"').read()
        # face name is burried in the middle
        l = a.find('"')
        r = a.find('"',l+1)
        return a[l+1:r]

    # Windows has only a couple of monospace fonts
    elif os.name == 'nt':
        return 'Consolas'

    # unknown OS
    else:
        return None

#--------1---------2---------3---------4---------5---------6---------7---------8
##
# \brief    COM port listening thread.
# \details  Make sure that this thead starts after the port is open and
#           stops before the port is closed. Also the timeout value of
#           the port should be set preferably with small value.
#
class ComThread:

    def __init__(self, win, ser):
        # window to which the receiving data is sent
        self.win = win
        # serial port
        self.ser = ser
        # initial state
        self.running = False

    ## call this method to start the thread.
    def Start(self):
        self.keepGoing = True
        self.running = True
        _thread.start_new_thread(self.Run, ())

    ## signal the thread to suicide
    def Stop(self):
        # flag for nice termination
        self.keepGoing = False

    ## main routine: upon arrival of new data, it generates an event.
    def Run(self):
        # keep running as far as the flag is set
        while self.keepGoing:
            # read a byte until timeout
            data = self.ser.read(100)
            # valid byte received
            if len(data):
                # create an event with the byte
                evt = UpdateComData(data = data)
                # post the event
                wx.PostEvent(self.win, evt)

        # end of loop
        self.running = False

    ## return True if the thread is running
    def IsRunning(self):
        return self.running

    ## change the target window for the event
    def SetEventTarget(self, win):
        self.win = win

#--------1---------2---------3---------4---------5---------6---------7---------8
##
# \brief    COM terminal window panel
#
class TermPanel(wx.Panel):

    def __init__(self, parent, ser, **kwgs):
        wx.Panel.__init__(self, parent, **kwgs)

        # serial port
        self.ser = ser

        # packet decoder
        self.pd = PacketDecoder()
        self.pd.SetMode('decode')

        # terminal
        self.txtTerm = wx.TextCtrl(self, wx.ID_ANY, "", size=(700,250),
                style = wx.TE_MULTILINE|wx.TE_READONLY);
        self.txtTerm.SetForegroundColour('yellow')
        self.txtTerm.SetBackgroundColour('black')

        # monospace font is desirable
        fname = GetMonoFont()
        if fname:
            self.txtTerm.SetFont(wx.Font(11,75,90,90,faceName=fname))

        # panel for controls
        self.pnlControl = wx.Panel(self, wx.ID_ANY)

        # list of available COM ports
        from serial.tools import list_ports
        portlist = [port for port,desc,hwin in list_ports.comports()]

        # baudrate selection
        self.sttSpeed = wx.StaticText(self.pnlControl, -1, "Baudrate")
        self.cboSpeed = wx.Choice(self.pnlControl, -1,
                choices=['9600','19200','38400','57800','115200','230400'])
        self.cboSpeed.SetStringSelection('115200')

        # port selection
        self.sttCPort = wx.StaticText(self.pnlControl, -1, "COM Port")
        self.cboCPort = wx.Choice(self.pnlControl, -1, choices=portlist)

        # terminal mode selection
        self.sttTMode = wx.StaticText(self.pnlControl, -1, "Terminal Mode")
        self.cboTMode = wx.Choice(self.pnlControl, -1,
                choices=['ASCII','Hex','Protocol'])
        self.cboTMode.SetStringSelection('ASCII')

        # newline character
        self.sttNLine = wx.StaticText(self.pnlControl, -1, "Newline Char")
        self.cboNLine = wx.Choice(self.pnlControl, -1,
                choices=['LF(0x0A)','CR(0x0D)'])
        self.cboNLine.SetStringSelection('LF(0x0A)')

        # local echo
        self.sttLEcho = wx.StaticText(self.pnlControl, -1, "Local Echo")
        self.choLEcho = wx.Choice(self.pnlControl, -1,
                choices=['Yes','No'])
        self.choLEcho.SetStringSelection('No')

        # clear terminal
        self.sttClear = wx.StaticText(self.pnlControl, -1, "Clear Terminal")
        self.btnClear = wx.Button(self.pnlControl, -1, "Clear")

        # reset data
        self.sttReset = wx.StaticText(self.pnlControl, -1, "Reset Data")
        self.btnReset = wx.Button(self.pnlControl, -1, "Reset")

        # save raw data
        self.sttSave = wx.StaticText(self.pnlControl, -1, "Save Data")
        self.btnSave = wx.Button(self.pnlControl, -1, "Save")

        # outbound packet
        self.sttSndPkt = wx.StaticText(self.pnlControl, -1, "Send Packet")
        self.choSndPkt = wx.Choice(self.pnlControl, -1,
                choices=[key for key in OutPackets.keys()])

        # COM thread object
        self.thread = ComThread(self, self.ser)

        # sizer
        sizer_g = wx.FlexGridSizer(10,2,4,4)
        sizer_g.Add(self.sttSpeed, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.cboSpeed, 1, wx.EXPAND)
        sizer_g.Add(self.sttCPort, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.cboCPort, 1, wx.EXPAND)
        sizer_g.Add(self.sttTMode, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.cboTMode, 1, wx.EXPAND)
        sizer_g.Add(self.sttNLine, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.cboNLine, 1, wx.EXPAND)
        sizer_g.Add(self.sttLEcho, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.choLEcho, 1, wx.EXPAND)
        sizer_g.Add(self.sttClear, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.btnClear, 1, wx.EXPAND)
        sizer_g.Add(self.sttReset, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.btnReset, 1, wx.EXPAND)
        sizer_g.Add(self.sttSave, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.btnSave, 1, wx.EXPAND)
        sizer_g.Add((20,20))
        sizer_g.Add((20,20))
        sizer_g.Add(self.sttSndPkt, 1, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        sizer_g.Add(self.choSndPkt, 1, wx.EXPAND)
        self.pnlControl.SetSizer(sizer_g)

        # alignment
        sizer_h = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h.Add(self.txtTerm, 1, wx.ALL|wx.EXPAND, 4)
        sizer_h.Add(self.pnlControl, 0, wx.ALL|wx.EXPAND, 4)
        self.SetSizer(sizer_h)
        sizer_h.Fit(self)

        # message bindings
        self.Bind(wx.EVT_CHOICE, self.OnPortOpen, self.cboSpeed)
        self.Bind(wx.EVT_CHOICE, self.OnPortOpen, self.cboCPort)
        self.Bind(wx.EVT_CHOICE, self.OnTermType, self.cboTMode)
        self.Bind(wx.EVT_CHOICE, self.OnNewLine, self.cboNLine)
        self.Bind(wx.EVT_CHOICE, self.OnLocalEcho, self.choLEcho)
        self.Bind(wx.EVT_BUTTON, self.OnTermClear, self.btnClear)
        self.Bind(wx.EVT_BUTTON, self.OnDataReset, self.btnReset)
        self.Bind(wx.EVT_BUTTON, self.OnFileSave, self.btnSave)
        self.Bind(wx.EVT_CHOICE, self.OnSendPacket, self.choSndPkt)
        self.txtTerm.Bind(wx.EVT_CHAR, self.OnTermChar)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_UPDATE_COMDATA, self.OnUpdateComData)


        # raw data storage
        self.rawdata = bytearray()

        # event list
        self.lstEvent = None

        # terminal type
        self.termType = self.cboTMode.GetStringSelection()

        # rx only setting
        self.rxOnly = False

        # newline character
        if 'CR' in self.cboNLine.GetStringSelection():
            self.newLine = 0x0D
        else:
            self.newLine = 0x0A

        # local echo
        self.localEcho = False

        # counter for alignment of hex display
        self.binCounter = 0

    ## Clear terminal. Note that the raw data is not affected.
    def ClearTerminal(self):
        self.txtTerm.Clear()

    ## Put your checksum algorithm here
    def ComputeChecksum(self, data):
        return 0x00

    ## Put your packet decoding algorithm here
    def DecodePacket(self, data):
        pass

    ## Reset raw data. Terminal will be cleared as well.
    def ResetData(self):
        self.rawdata = bytearray()
        self.ClearTerminal()

    ## Open COM port
    def OpenPort(self, port, speed):

        if self.ser.is_open:
            # terminate thread first
            if self.thread.IsRunning():
                self.thread.Stop()
            # join the thread
            while self.thread.IsRunning():
                wx.MilliSleep(100)
            # then close the port
            self.ser.close()

        # set port number and speed
        self.ser.port = port
        self.ser.baudrate = int(speed)
        # setting read timeout is crucial for the safe termination of thread
        self.ser.timeout = 1

        # open the serial port
        try:
            self.ser.open()
        except:
            return False
        else:
            pass

        if self.ser.is_open:
            # start thread
            self.thread.Start()
            return True
        else:
            return False

    ## Save received data
    def SaveRawData(self, fname):
        f = open(fname, 'wb')
        f.write(self.rawdata)
        f.close()

    ## Send data via COM port
    def SendData(self, data):
        if self.ser.is_open:
            self.ser.write(data)

    ## Set new line character
    def SetNewLine(self, nl):
        if nl == 0x0D or nl == 0x0A:
            self.newLine = nl

    ## Enable/disable local echo
    def SetLocalEcho(self, flag):
        self.localEcho = flag

    def SetRxOnly(self, flag = True):
        self.rxOnly = flag

    ## Set terminal type
    def SetTermType(self, termtype):
        if termtype != '':
            self.termType = termtype

        if self.termType == 'Hex':
            self.txtTerm.AppendText('\n')
            self.binCounter = 0

    ## Show/hide controls
    def ShowControls(self, flag):
        self.pnlControl.Show(flag)
        self.Layout()

    ## Save file button handler
    def OnFileSave(self, evt):
        self.SaveRawData(data_file)

    ## Clear terminal button handler
    def OnTermClear(self, evt):
        self.ClearTerminal()

    ## Reset data button handler
    def OnDataReset(self, evt):
        self.ResetData()

    ## Terminal type choice contrl handler
    def OnTermType(self, evt):
        # terminal type
        self.SetTermType(self.cboTMode.GetStringSelection())

    ## Newline character choice control handler
    def OnNewLine(self, evt):
        if 'CR' in self.cboNLine.GetStringSelection():
            self.SetNewLine(0x0d)
        else:
            self.SetNewLine(0x0a)

    ## Local echo mode selection handler
    def OnLocalEcho(self, evt):
        if 'Yes' in self.choLEcho.GetStringSelection():
            self.SetLocalEcho(True)
        else:
            self.SetLocalEcho(False)

    ## Port selection choice handler
    def OnPortOpen(self, evt):
        port = self.cboCPort.GetStringSelection()
        speed = self.cboSpeed.GetStringSelection()

        # device is not selected
        if port == '':
            return

        # open the com port
        if self.OpenPort(port,speed):
            wx.MessageBox(port + ' is (re)open')
        else:
            wx.MessageBox('Failed to open: ' + port)

    ## Terminal input handler
    def OnTermChar(self, evt):
        # no tx data if rxOnly
        if self.rxOnly:
            return

        if self.ser.is_open:
            # key code can be multiple bytes
            try:
                self.ser.write([evt.GetKeyCode()])
            except:
                pass

        if self.localEcho:
            if self.termType == 'ASCII':
                self.txtTerm.AppendText(chr(evt.GetKeyCode()))
            else:
                self.txtTerm.AppendText('0x{:02X}.'.format(evt.GetKeyCode()))

    ## Local echo mode selection handler
    def OnSendPacket(self, evt):
        if self.ser.is_open:
            self.ser.write(OutPackets[self.choSndPkt.GetStringSelection()])


    ## COM data input handler
    def OnUpdateComData(self, evt):

        for byte in evt.data:
            # append incoming byte to the rawdata
            self.rawdata.append(byte)

            if self.termType == 'Protocol':
                # pass byte to the packet decoder
                ret = self.pd.AddByte(byte)
                # display packet decode result
                if ret is None:
                    pass
                else:
                    self.txtTerm.AppendText(ret + '\n')

            elif self.termType == 'Hex':
                # display formatted hex
                self.txtTerm.AppendText('0x{:02X}'.format(byte))
                # counter for alignment of the hex display
                self.binCounter = self.binCounter + 1

                if self.binCounter == 8:
                    self.txtTerm.AppendText(' - ')

                elif self.binCounter == 16:
                    self.txtTerm.AppendText('\n')
                    self.binCounter = 0

                else:
                    self.txtTerm.AppendText('.')

            else:
                if self.newLine == 0x0A:
                    if byte == 0x0D:
                        pass
                    elif byte == 0x0A:
                        self.txtTerm.AppendText('\n')
                    else:
                        self.txtTerm.AppendText(chr(byte))
                elif self.newLine == 0x0D:
                    if byte == 0x0A:
                        pass
                    elif byte == 0x0D:
                        self.txtTerm.AppendText('\n')
                    else:
                        self.txtTerm.AppendText(chr(byte))


    ## wx.EVT_CLOSE handler
    def OnClose(self, evt):
        # terminate the thread
        if self.thread.IsRunning():
            self.thread.Stop()

        # join the thread
        while self.thread.IsRunning():
            wx.MilliSleep(100)

        # close the port
        if self.ser.is_open:
            self.ser.close()

        # destroy self
        self.Destroy()


#--------1---------2---------3---------4---------5---------6---------7---------8
if __name__=="__main__":

    class MyFrame(wx.Frame):

        def __init__(self, parent, title):
            wx.Frame.__init__(self, parent, title=title)

            # serial terminal panel
            self.pnlTerm = TermPanel(self, serial.Serial(), size=(900,400))

            # sizer
            self.sizer = wx.BoxSizer(wx.VERTICAL)
            self.sizer.Add(self.pnlTerm,1, wx.EXPAND)

            self.SetSizer(self.sizer)
            self.SetAutoLayout(1)
            self.sizer.Fit(self)
            self.Show()
    
    # app loop
    app = wx.App()
    frame = MyFrame(None, "Serial Terminal Demo")
    app.MainLoop()
