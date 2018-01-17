#!/usr/bin/env python3

################################################################################
#
#   \file
#   \author     <a href="http://www.innomatic.ca">innomatic</a>
#   \brief      Python Proxy of SerialCom.
#
#   Definitions here must match with that of SerialComm.h
# 
#   \verbatim
#   Packet Structure
#
#   (HDR) (LEN) (PLD) (CSM)
#
#   (HDR) header single byte
#   (LEN) size of the payload, single byte
#   (PLD) payload of variable size
#   (CSM) checksum, single byte
#
#   Payload Structure
#
#   (CMD) (DAT)
#
#   (CMD) single byte command code (DAT) data of variable length
#   @endverbatim
#
#   Receiver is expected to respond with either single byte of ACK or NAK
#

MAX_PAYLOAD = 10
MAX_PACKET = MAX_PAYLOAD + 3

# header signature, ACK, NAK, ...
PKT_HEADR  = 0xf5
PKT_ACK    = 0xf6
PKT_NAK    = 0xf7
PKT_IAM    = 0xf8

# System control
SYS_SRESET = 0x00   # perform software reset
SYS_WRESET = 0x01   # perform watchdog reset
SYS_STPMOD = 0x02   # enter stop mode
SYS_DSLMOD = 0x03   # enter deep sleep mode
SYS_SLPMOD = 0x04   # enter sleep mode

# DIO control
DIO_SETVAL = 0x10   # DIO set value
DIO_RSTVAL = 0x11   # DIO reset value
DIO_GETVAL = 0x12   # DIO get value
DIO_TGLVAL = 0x13   # DIO toggle value

# ADC control
ADC_SETMAG = 0x20   # ADC set magnitude
ADC_SETFRQ = 0x21   # ADC set frequency
ADC_CONSTV = 0x23   # ADC dc output
ADC_SINEWV = 0x24   # ADC sine waveform
ADC_SWTHWV = 0x25   # ADC sawtooth wavefrom
ADC_TRNGWV = 0x26   # ADC triangle waveform

# DAC control
DAC_SETFRQ = 0x30   # DAC set sample frequency
DAC_CAPSGL = 0x31   # DAC capture single
DAC_CAPCNT = 0x32   # DAC capture continuous

# Report data
RPT_FINISH = 0x80   # no more data to report
RPT_U08XXX = 0x81   # report with uint8_t data
RPT_S08XXX = 0x82   # report with int8_t data
RPT_U16XXX = 0x83   # report with uint16_t data
RPT_S16XXX = 0x84   # report with int16_t data
RPT_U32XXX = 0x85   # report with uint16_t data
RPT_S32XXX = 0x86   # report with int16_t data

# Command Code dictionary for packet decoding
CommandCodes = {
        SYS_SRESET: 'SYS_SRESET',
        SYS_WRESET: 'SYS_WRESET',
        SYS_STPMOD: 'SYS_STPMOD',
        SYS_DSLMOD: 'SYS_DSLMOD',
        SYS_SLPMOD: 'SYS_SLPMOD',
        DIO_SETVAL: 'DIO_SETVAL',
        DIO_RSTVAL: 'DIO_RSTVAL',
        DIO_GETVAL: 'DIO_GETVAL',
        DIO_TGLVAL: 'DIO_TGLVAL',
        ADC_SETMAG: 'ADC_SETMAG',
        ADC_SETFRQ: 'ADC_SETFRQ',
        ADC_CONSTV: 'ADC_CONSTV',
        ADC_SINEWV: 'ADC_SINEWV',
        ADC_SWTHWV: 'ADC_SWTHWV',
        ADC_TRNGWV: 'ADC_TRNGWV',
        DAC_SETFRQ: 'DAC_SETFRQ',
        DAC_CAPSGL: 'DAC_CAPSGL',
        DAC_CAPCNT: 'DAC_CAPCNT',
        RPT_FINISH: 'RPT_FINISH',
        RPT_U08XXX: 'RPT_U08XXX',
        RPT_S08XXX: 'RPT_S08XXX',
        RPT_U16XXX: 'RPT_U16XXX',
        RPT_S16XXX: 'RPT_S16XXX',
        RPT_U32XXX: 'RPT_U32XXX',
        RPT_S32XXX: 'RPT_S32XXX', 
        }


OutPackets = {
        'System Reset'      :bytes((PKT_HEADR,0x01,SYS_SRESET,
            SYS_SRESET)),
        'Watchdog Reset'    :bytes((PKT_HEADR,0x01,SYS_WRESET,
            SYS_WRESET)),
        'DIO 01 Set'        :bytes((PKT_HEADR,0x02,DIO_SETVAL,0x01,
            DIO_SETVAL ^ 0x01)),
        'DIO 01 Clear'      :bytes((PKT_HEADR,0x02,DIO_RSTVAL,0x01,
            DIO_RSTVAL ^ 0x01)),
        'DIO 01 Get'        :bytes((PKT_HEADR,0x01,DIO_GETVAL,
            DIO_GETVAL)),
        'Arbitrary'         :bytes((PKT_HEADR,0x05,0xFF,0x02,0x03,0x04,0x05,
            0xFF ^ 0x02 ^ 0x03 ^ 0x04 ^ 0x05)),
        }

################################################################################
#   This packet decoder should be called at the arrival of each data byte.
#   When valid packet arrives it returns data whose type is controlled by 
#   SetMode() function. Otherwise it returns None.
#
#   @code
#   # create an instance
#   self.pd = PacketDecoder()
#
#   # set mode
#   self.pd.SetMode('PAYLOAD')
#
#   # COM data event handler
#   def OnUpdateComData(self, evt):
#       # call decoder
#       ret = self.pd.AddByte(evt.byte[0])
#
#       # collect data
#       if ret is not None:
#           self.data.append(data)
#   @endcode
#
class PacketDecoder():

    def __init__(self, mode='FULL'):
        self.packet = bytearray()
        self.state = 'HDR'
        self.mode = mode
        self.len = 0

    ## Define the return data type
    #    
    # * 'FULL' returns full packet
    # * 'PAYLOAD' returns payload only
    # * 'DECODE' returns human readable string
    #
    def SetMode(self, mode):
        if mode.upper() in ('FULL', 'PAYLOAD', 'DECODE'):
            self.mode = mode.upper()

    ##Packet Decoding State Machine
    # Call this method every time new byte has arrived.
    def AddByte(self, byte):

        if self.state == 'HDR':
            # initialize the packet storage
            self.packet = bytearray()
            self.csum = 0

            # valid header received
            if byte == PKT_HEADR:
                self.packet.append(byte)
                # next state is LEN
                self.state = 'LEN'
                return None

            # ACK or NAK
            elif byte == PKT_ACK or byte == PKT_NAK or byte == PKT_IAM:
                # go back to HDR state
                self.state = 'HDR'

                if self.mode == 'FULL':
                    return byte

                elif self.mode == 'DECODE':
                    if byte == PKT_ACK:
                        return 'ACK'
                    elif byte == PKT_NAK:
                        return 'NAK'
                    elif byte == PKT_IAM:
                        return 'IAM'

                else:
                    return None

            # invalid byte
            else:
                # ignore the byte and go back to HDR state
                self.state = 'HDR'
                return None

        elif self.state == 'LEN':
            # invalid payload length
            if byte > MAX_PACKET:
                # return to HDR staet
                self.state = 'HDR'
                return None;

            # collect byte
            self.packet.append(byte)
            # save length
            self.len = byte
            # proceed to PLD state
            self.state = 'PLD'
            return None

        elif self.state == 'PLD':
            # collect byte
            self.packet.append(byte)
            # compute checksum
            self.csum = self.csum ^ byte

            # end of data
            if len(self.packet) >= 2 + self.len:
                # proceed to CSM state
                self.state = 'CSM'
            return None

        elif self.state == 'CSM':
            # checksum error
            if self.csum != byte:
                self.state = 'HDR'
                return None

            self.packet.append(byte)
            # start all over
            self.state = 'HDR'

            if self.mode == 'FULL' or self.mode == 'Full':
                return self.packet

            elif self.mode == 'PAYLOAD' or self.mode == 'Payload':
                return self.packet[2:-1]

            else:
                # command
                try:
                    txt = CommandCodes[self.packet[2]] + ':'
                except:
                    txt = 'Unknown :'

                # data
                txt = txt + self.packet[3:self.packet[1] + 2].hex()

                return txt


#--------1---------2---------3---------4---------5---------6---------7---------8
if __name__=='__main__':
    print('Unit Test for PacketDecoder()')

    # create an instance
    pd = PacketDecoder()

    # retrieve payload of the packet
    pd.SetMode('Payload')

    # feed the legit packets to the decoder
    for key, packet in OutPackets.items():

        for byte in packet:
            # feed byte to the decoder
            ret = pd.AddByte(byte)

            # no packet received
            if ret is None:
                pass
            elif ret == PKT_ACK:
                print('ACK received.')
            elif ret == PKT_NAK:
                print('NAK received.')
            elif ret == PKT_IAM:
                print('IAM received.')
            else:
                # return bytes should match with the payload of the packet
                if ret == packet[2:-1]:
                    print('packet received and match.')
                else:
                    print('packet received but does not match.')

    # set mode to decode
    pd.SetMode('decode')

    # feed the legit packets to the decoder
    for key, packet in OutPackets.items():

        for byte in packet:
            # feed byte to the decoder
            ret = pd.AddByte(byte)

            # no packet received
            if ret is None:
                pass
            else:
                print(ret)
