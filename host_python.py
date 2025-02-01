#!/usr/bin/env python3

import struct
import logging
### from .hcc import ResponseChecksumError, ChecksumError, PayloadChecksumError, HccStatusError, HeaderChecksumError, decode_status, payload_checksum
import re
__date__ = "01/31/2025 7:27 PM"
__copyright__ = "Torsten Jaekel, 01/31/2025"

logger = logging.getLogger(__name__)

HCC_LANE_CFG_QUAD = 0x7

# HCC_HALF_DUP_TYPE
HST_TX = 0       # Host to Device
DEV_TX = 1       # Device to Host
HST_TX_AHDR = 4  # Host to Device with abbreviated header
DEV_TX_AHDR = 5  # Device to Host with abbreviated header

# Commands
# HCC_CMD_NOOP = 0x00
HCC_CMD_WBLK = 0x01
HCC_CMD_RBLK = 0x02
HCC_CMD_DMAX = 0x80

# Predefine HCC_CFG byte packets
# HCC_CFG is an 8-bit value and is clocked out ONLY on IO0, so clock the bits out as the lsb of 32bits QSPI
HCC_CFG_QSPI_H2D  = b'\x00\x00\x10\x11'  # e0 1110_0000
HCC_CFG_QSPI_D2H  = b'\x01\x00\x10\x11'  # e1 1110_0001
HCC_CFG_QSPI_H2DA = b'\x00\x01\x10\x11'  # e4 1110_0100
HCC_CFG_QSPI_D2HA = b'\x01\x01\x10\x11'  # e5 1110_0101

#--------------------------------------------
#from PySide import QtCore, QtGui
from datetime import datetime
#import time
import sys
import glob
import serial
#import re

ser = serial.Serial()
debug = False

def select_port():
    global ser
    #get_ipython().magic(u'gui qt')
    #ports = serial_ports()
    #port, ok = QtGui.QInputDialog.getItem(None,
    #                 "Select a serial port", "PORT", ports,
    #                 current=(len(ports)-1),
    #                 flags=QtCore.Qt.WindowStaysOnTopHint)
    #get_ipython().magic(u'pylab inline')
    #if ok:
    ser = serial.Serial()
    #ser.baudrate = 1843200
    ser.baudrate = 3686400
    ser.timeout = 1 # sec
    ser.rtscts = 0
    #ser.port = port
    ser.port = 'COM14'


def serial_ports():
    """Lists serial ports
    :raises EnvironmentError:
        On unsupported or unknown platforms
    :returns:
        A list of available serial ports
    """
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this is to exclude your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


class SerialPortError(Exception):
    pass


def send_to_uart(command):
    if not ser.isOpen():
        ser.open()
    ser.read(ser.inWaiting())
    ser.flushOutput()
    if debug:
        print('Sending UART command: ' + command)
    command += '\r'
    ser.write(command.encode('utf-8'))
    resp = get_resp()
    return resp


def get_resp():
    resp = ''
    t1 = datetime.now()
    #wait until EOT received
    while chr(0x03) not in resp:
        rdata = ser.read(ser.inWaiting())
        if rdata:
            resp = resp + rdata.decode('utf-8')
            t1 = datetime.now()
            tlapsed = datetime.now() -t1
            if debug:
                print(rdata)
        else:
            tlapsed = datetime.now() -t1
            if tlapsed.total_seconds() > 10: break
    #check if we got the prompt
    if '> ' not in resp:
        raise SerialPortError('UART command not successful')
    x = resp.replace('\r\n> \003', '')
    return x
    #return resp


def send_to_uart_bin(bincommand):
    if not ser.isOpen():
        ser.open()
    ser.read(ser.inWaiting())
    ser.flushOutput()
    if debug:
        print('Sending UART command:')
        print([hex(n) for n in bincommand])
    ser.write(bincommand)
    resp = get_resp_bin()
    return resp


def get_resp_bin():
    resp = ''
    rlen = 0
    xlen = 4096         #start length - >= max. possible length
    t1 = datetime.now()
    while xlen > 0 :
        rdata = ser.read(ser.inWaiting())
        if rdata:
            resp = resp + rdata
            t1 = datetime.now()
            if debug: 
                print([hex(ord(n)) for n in resp])
            if len(resp) >= 3 :
                if rlen == 0 :
                    #byte 1 and 2 are length of follwing response
                    rlen = int(ord(resp[1]))
                    rlen = rlen + int(ord(resp[2])) * 256
                    xlen = rlen

            if rlen > 0 :
                #w/o the first three bytes as RESP, LEN_l, LEN_h
                xlen = rlen + 3 - len(resp)
        else:
            tlapsed = datetime.now() -t1
            if tlapsed.total_seconds() > 10: break
    return resp

DEBUG = False

def payload_checksum(data):
    #it must be byte array
    l = len(data) // 4
    chs = 0;
    for x in range(l):
        w =      data[x*4 + 0]
        w = w | (data[x*4 + 1] <<  8)
        w = w | (data[x*4 + 2] << 16)
        w = w | (data[x*4 + 3] << 24)
        chs = chs + w
    return ~chs & 0xFFFFFFFF

class ResponseChecksumError(Exception):
        pass

class ChecksumError(Exception):
        pass

class PayloadChecksumError(Exception):
        pass

class HccStatusError(Exception):
        pass

class HeaderChecksumError(Exception):
        pass

def SendTransaction(tr, numRd):
    if DEBUG:
        print("Bytes:")
        hstr = "".join("%02x " % b for b in tr)
        print(hstr)

    cmd, addr, alt0, alt = struct.unpack('<BIHB', tr[0:8])
    if numRd == 0:
        uartStr = format("qspi ")
    else:
        uartStr = format("qspi -%d " % numRd)
    uartStr = uartStr + format("0x%02x 0x%08x 0x%04x%02x" % (cmd, addr, alt0, alt))
    l = (len(tr) - 8) // 4
    for x in range(l):
        w = struct.unpack('<I', tr[8+x*4:8+(x+1)*4])
        uartStr = uartStr + format(" 0x%08x" % (w))
    
    #print(uartStr)

    resp = send_to_uart(uartStr)
    print(resp)

##-----------------------------------------------------------

hccSPI = None

class HccQSpiInterface(object):
    def __init__(self, qspi_interface=None, **kwargs):
        if isinstance(qspi_interface, str):
            ###from msappy.spi_factory import SpiFactory
            args = {'protocol': 'HCC', 'auto_open': True}
            args.update(kwargs)
            ###self.qspi = SpiFactory.create_new_spi_instance(qspi_interface, **args)
        else:
            self.qspi = qspi_interface

        self._last_status = None
        self._ignore_status = False
        self._ignore_checksum_rsp = False
        self._ignore_checksum_hdr = False
        self._ignore_checksum_pld = False
        self._procdly = 4  #  4 bytes
        self._procdly_bytes = b'\x00\x00\x00\x00'
        ###self._turnaround = 1  # 8 bits, 2 SCLK cycles
        self._turnaround = 0
        self._turnaround_bytes = b'\x00'  # 8 bits

    #
    # Physical configuration
    #
    def open(self):
        ###self.qspi.open()
        pass

    def close(self):
        ###self.qspi.close()
        pass

    def set_clk_speed(self, clockrate_kHz):
        """
        Set the clock speed of the SPI interface in kiloHertz.

        :param clockrate_kHz: The SPI clock speed in kiloHertz.
        """
        ###self.qspi.spi_config_clock(clockrate_kHz)
        pass

    def get_clk_speed(self):
        """Get the clock rate of the spi interface in kilohertz."""
        ###return self.qspi.spi_get_clock()
        return 0

    # def get_hintx_l_status(self):
    #     """Get logical value of HINT0_L, HINT1_L, and HINT2_L.
    #
    #     :return: int with bit0=HINT0_L, bit1=HINT1_L, and bit=2HINT2_L.
    #     """
    #     # Check the type of the spi without needing actual knowledge
    #     spi_type_name = type(self.qspi).__name__
    #     if 'Promira' in spi_type_name:
    #         return self.qspi.gpio_get() & 0x1
    #     else:
    #         raise NotImplementedError('get_hintx_l_status not implemented for {}'.format(spi_type_name))

    #
    # HCC QSPI Transaction Sequences
    #
    def hcc_qspi_wblk(self, end_point, bytes_out, transNo, ts=1):
        """Write bytes to the specified end point using TS1

        :param end_point:
        :param bytes_out: Bytes to write out. Max length is 64kB
        :param ts: Transaction sequence, 1 is optimal
        """
        if ts != 1:
            raise NotImplementedError("WBLK operation currently only implemented via Transaction Sequence 1")

        # Transaction 1: CFG=0xE4, COUNT, EP, CMD, HDR_CHK, CFG_CHK=0x1B, WPLD, WPLD_CHK
        hcc_count = len(bytes_out)
        hcc_hdr_chk_h = 0xFFFF & ~(HCC_CMD_WBLK + (end_point << 8) + hcc_count)
        hcc_wpld_chk_h = payload_checksum(bytes_out)
        transaction_1 = struct.pack('<BBBBBHB', 0xe4, HCC_CMD_WBLK, end_point, hcc_count & 0xff, hcc_count >> 8, hcc_hdr_chk_h, 0x1b)
        ###transaction_1 += self._turnaround_bytes + bytes_out + struct.pack('<I', hcc_wpld_chk_h)
        transaction_1 += struct.pack('<I', 0) + bytes_out + struct.pack('<I', hcc_wpld_chk_h)
        # Transaction 2: CFG=0xE1, 32'h0, 16'h0, CFG_CHK, TURN_AROUND, [Read 12 bytes: RSP, RSP_CHK, HDR_CHK, WPLD_CHK]
        # transaction_2 = struct.pack('<BIHB', 0xe1, 0, 0, 0xE1^0xFF)
        transaction_2 = b'\xe1\x00\x00\x00\x00\x00\x00\x1e'


        # Clock out/in the data
        # self.qspi.qspi_transaction(transaction_1, single_write_count=1)
        # bytes_in = self.qspi.qspi_transaction(transaction_2, single_write_count=1, multiread_count=self._procdly + 12)
        ###bytes_in = self.qspi.qspi_dual_transaction(transaction_1,
        ###                                           transaction_2,
        ###                                           multiread_count=self._turnaround+12,
        ###                                           first_single_bytes_count=1,
        ###                                           second_single_bytes_count=1)

        if transNo == 0:
            SendTransaction(transaction_1, 0)
            SendTransaction(transaction_2, (12)//4)
        if transNo == 1:
            SendTransaction(transaction_1, 0)
        if transNo == 2:
            SendTransaction(transaction_2, (12)//4)

        return

    def hcc_qspi_rblk(self, end_point, byte_count, ts=2):
        """Read bytes to the specified end point using TS2

        :param end_point: hcc end point.
        :param byte_count: Number of bytes to read
        :param ts: Transaction sequence id number (2 is optimal)
        :return: The read payload as a list of 32-bit ints
        """
        # hcc_hdr = 0xFFFF & ~((HCC_CMD | HCC_EP<<8) + HCC_COUNT) =
        hcc_hdr_chk_h = 0xFFFF & ~(HCC_CMD_RBLK + (end_point << 8) + byte_count)

        if ts == 2:  # (optimal)
            # cfg=E5, count, ep, cmd, hdr_chk, cfg_chk=1A, procdly, rsp, hdr_chk, rpld, pld_chk
            bytes_out = struct.pack('<BBBBBHB', 0xe5, HCC_CMD_RBLK, end_point, byte_count & 0xFF, byte_count >> 8, hcc_hdr_chk_h, 0x1A)
            ###bytes_in = self.qspi.qspi_transaction(bytes_out, single_write_count=1, multiread_count=self._turnaround+self._procdly + byte_count + 4)
            SendTransaction(bytes_out, (self._procdly + byte_count + 12)//4)
        elif ts == 1:
            raise NotImplementedError("HCC Read Block via TS1 not yet implemented.")
        elif ts == 0:
            raise NotImplementedError("HCC Read Block via TS0 not yet implemented.")
        else:
            raise ValueError("Invalid transaction sequence.")

        return

    def hcc_qspi_dmax_rreg(self, address, byte_count, transNo, unpack=True):
        """QSPI HCC DMAX RREG Operation via TS0

        The unpack parameter will unpack the raw bytes into a native python int depending on byte_count and dmax_incr.
        A byte_count set to a multiple of 4 with a dmax_incr of one byte (value 0 or 3) will be unpacked into 32-bit
        words. Otherwise it will be unpacked according to the payload incriment size.

        :param address: 4 byte HCC_DMAX_ADDR
        :param byte_count: Number of bytes to read (maximum 64kiB)
        :param unpack: Unpack data from bytes into 32bit ints
        :return: A list of 32bit int
        """
        USE_SWC = True
        turnaround = self._turnaround
        procdly = self._procdly
        hcc_hdr_chk_h = 0xFFFF & ~(HCC_CMD_DMAX + (0x05 << 8) + byte_count + (address & 0xFFFF) + (address >> 16))

        # Transaction 1: CFG=0xE0, 32'h0, 16'h0, cfg_chk=0x1F, cmd=0x80, d_args=05, count, dmax_addr, 16'h0, hdr_chk
        transaction_1 = struct.pack('<BIHBBBHIHH', 0xe0, 0, 0, 0x1F, HCC_CMD_DMAX, 0x05, byte_count, address, 0, hcc_hdr_chk_h)
        # Transaction 2: CFG=0xE1, 32'h0, 16'h0, cfg_chk=0x1E, turnaround, [Read 12+bytes: RSP, RSP_CHK, HDR_CHK, RPLD, RPLD_CHK]
        # transaction_2 = struct.pack('<BIHB', 0xe1, 0, 0, 0x1e)
        transaction_2 = b'\xe1\x00\x00\x00\x00\x00\x00\x1e'

        if not USE_SWC:  # debug to force hcc_cfg using quad
            transaction_1 = b'\x11\x10\x00\x00' + transaction_1[1:]
            transaction_2 = b'\x11\x10\x00\x01' + transaction_2[1:]

        # Clock data
        # self.qspi.qspi_transaction(transaction_1, single_write_count=USE_SWC)
        # bytes_in = self.qspi.qspi_transaction(transaction_2, single_write_count=USE_SWC, multiread_count=procdly + 12 + byte_count)
        ###bytes_in = self.qspi.qspi_dual_transaction(transaction_1,
        ###                                           transaction_2,
        ###                                           multiread_count=turnaround + procdly + 12 + byte_count,
        ###                                           first_single_bytes_count=USE_SWC,
        ###                                           second_single_bytes_count=USE_SWC)

        if transNo == 0:
            SendTransaction(transaction_1, 0)
            SendTransaction(transaction_2, (procdly + 12 + byte_count)//4)
        if transNo == 1:
            SendTransaction(transaction_1, 0)
        if transNo == 2:
            SendTransaction(transaction_2, (procdly + 12 + byte_count)//4)

        return

    def hcc_qspi_dmax_wreg(self, address, bytes_out, transNo):
        """QSPI HCC DMAX WREG Operation via TS0

        :param address: 4 byte HCC_DMAX_ADDR
        :param bytes_out: Bytes to write out (up to 64kiB)
        """
        # If the list of bytes is actually a list of ints, assume it's 32-bit ints and pack into bytes
        if isinstance(bytes_out, int) and bytes_out <= 0xFFFFFFFF:
            hcc_count = len(bytes_out) * 4
            hcc_wpld_chk_h = ~sum(bytes_out) & 0xFFFFFFFF
            bytes_out = struct.pack('<I', bytes_out)
        else:
            hcc_count = len(bytes_out)
            hcc_wpld_chk_h = payload_checksum(bytes_out)

        USE_SWC = True

        hcc_hdr_chk_h = 0xFFFF & ~(HCC_CMD_DMAX + (0x01 << 8) + hcc_count + (address & 0xFFFF) + (address >> 16))
        # Transaction 1: CFG=0xE0, 32'h0, 16'h0, cfg_chk=0x1F, cmd=0x80, d_args=01, count, dmax_addr, 16'h0, hdr_chk,
        # procdly, wpld, wpld_chk
        transaction_1 = struct.pack('<BIHBBBHIHH', 0xe0, 0, 0, 0x1F, HCC_CMD_DMAX, 0x01, hcc_count, address, 0, hcc_hdr_chk_h)
        transaction_1 += self._procdly_bytes + bytes_out + struct.pack('<I', hcc_wpld_chk_h)
        # Transaction 2: CFG=0xE1, 32'h0, 16'h0, cfg_chk=0x1E, turnaround, [Read 12 bytes: RSP, RSP_CHK, HDR_CHK, WRPLD_CHK]
        # transaction_2 = struct.pack('<BIHB', 0xe1, 0, 0, 0x1e)
        transaction_2 = b'\xe1\x00\x00\x00\x00\x00\x00\x1e'

        if not USE_SWC:  # debug to force D[1:3] to 0 during hcc_cfg
            transaction_1 = b'\x11\x10\x00\x00' + transaction_1[1:]
            transaction_2 = b'\x11\x10\x00\x01' + transaction_2[1:]

        # Clock data

        ###bytes_in = self.qspi.qspi_dual_transaction(transaction_1,
        ###                                           transaction_2,
        ###                                           multiread_count=self._turnaround + 12,
        ###                                           first_single_bytes_count=USE_SWC,
        ###                                           second_single_bytes_count=USE_SWC,
        ###                                           delay=5e-6)

        if transNo == 0:
            SendTransaction(transaction_1, 0)
            SendTransaction(transaction_2, 12//4)
        if transNo == 1:
            SendTransaction(transaction_1, 0)
        if transNo == 2:
            SendTransaction(transaction_2, 12//4)

        return      #skip checksum for now

    def hcc_qspi_noop(self, ts=2):
        """Perform QSPI HCC NOOP command and return the HCC STATUS

        :param ts: Transaction Sequence (2 is optimal)
        :return: Contents of HCC_STATUS as an int
        """
        if ts == 2:  # (optimal)
            # CFG=E5, 24'h0, CMD=0, HDR_CHK_H=FFFF, CFG_CHK=1A, procdly, [Read 8 bytes: RSP, RSP_CHK, HDR_CHK]
            # NOOP_TS2_PACKET = struct.pack('<BIHB', 0xe5, 0, 0xFFFF, 0x1A)
            # NOOP_TS2_PACKET = b'\xe5\x00\x00\x00\x00\xff\xff\x1a'
            # Clock the data and unpack
            # data_in = self.qspi.qspi_transaction(NOOP_TS2_PACKET, single_write_count=1, multiread_count=self._procdly + 8)
            # hcc_status, rsp_chk_d, hdr_chk_d = struct.unpack('<IHH', data_in[self._procdly:])

            NOOP_TS2_PACKET = b'\x11\x10\x01\x01\x00\x00\x00\x00\xff\xff\x1a'
            # NOOP_TS2_PACKET = b'\xe5\x00\x00\x00\x00\xff\xff\x1a'
            # Clock the data and unpack
            ###data_in = self.qspi.qspi_transaction(NOOP_TS2_PACKET, single_write_count=0, multiread_count=self._turnaround + 8)
            SendTransaction(NOOP_TS2_PACKET, (8)//4)

            return

            hcc_status, rsp_chk_d, hdr_chk_d = struct.unpack('<IHH', data_in[self._turnaround:])
        elif ts == 1:
            # Transaction 1: CFG=E4, HDR=32'h0, ADDR+CMD=32'h0,HDR_CHK_H=FFFF, CFG_CHK=0x1B, DATA=8'h0
            # NOOP_TS1_PART1OF2 = struct.pack('<BIIHBB', 0xe4, 0, 0, 0xffff, 0x1b, 0)
            NOOP_TS1_PART1OF2 = b'\xe4\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x1b\x00'
            # Transaction 2: CFG=E1, ADDR=32'h0, ALT=16h'0, CFG_CHK=0x1E, turnaround, [Read 8 bytes: RSP, RSP_CHK, HDR_CHK]
            # NOOP_TS1_PART2OF2 = struct.pack('<BIHB', 0xe1, 0, 0, 0x1e)
            NOOP_TS1_PART2OF2 = b'\xe1\x00\x00\x00\x00\x00\x00\x1e'
            # Clock the data and unpack
            ###self.qspi.qspi_transaction(NOOP_TS1_PART1OF2)
            ###data_in = self.qspi.qspi_transaction(NOOP_TS1_PART2OF2, single_write_count=1, multiread_count=self._turnaround + 8)
            SendTransaction(NOOP_TS1_PART2OF2, (8)//4)

            return

            hcc_status, rsp_chk_d, hdr_chk_d = struct.unpack('<IHH', data_in[self._turnaround:])
        elif ts == 0:
            # Transaction 1: CFG=E0, 32'h0, 16'h0, CFG_CHK=0x1F, CMD=8'h0, 64'h0m HDR_CHK_H=0xFFFF
            # NOOP_TS0_PART1OF2 = struct.pack('<BHIBBLH', 0xe0, 0, 0, 0x1f, 0, 0, 0xffff)
            NOOP_TS0_PART1OF2 = b'\xe0\x00\x00\x00\x00\x00\x00\x1f\x00\x00\x00\x00\x00\xff\xff'
            # Transaction 2: CFG=E1, 32'h0, 16h'0, CFG_CHK=0x1E, turnaround, [Read 8 bytes: RSP, RSP_CHK, HDR_CHK]
            # NOOP_TS0_PART2OF2 = struct.pack('<BIHB', 0xe1, 0, 0, 0x1e)
            NOOP_TS0_PART2OF2 = b'\xe1\x00\x00\x00\x00\x00\x00\x1e'
            # Clock the data and unpack
            ###self.qspi.qspi_transaction(NOOP_TS0_PART1OF2)
            ###data_in = self.qspi.qspi_transaction(NOOP_TS0_PART2OF2, single_write_count=1, multiread_count=self._turnaround + 8)
            SendTransaction(NOOP_TS0_PART1OF2, 0)
            SendTransaction(NOOP_TS0_PART2OF2, (8)//4)

            return

def CMD_WREG(transNo, addr, words) :
    global hccSPI
    bytes_out = bytes()
    for x in range(len(words)):
        bytes_out = bytes_out + struct.pack('<I', words[x])
    hccSPI.hcc_qspi_dmax_wreg(addr, bytes_out, transNo)

def CMD_RREG(transNo, addr, numWords) :
    global hccSPI
    hccSPI.hcc_qspi_dmax_rreg(addr, numWords * 4, transNo)

def CMD_WBLK(transNo, ep, words):
    global hccSPI
    bytes_out = bytes()
    for x in range(len(words)):
        bytes_out = bytes_out + struct.pack('<I', words[x])
    hccSPI.hcc_qspi_wblk(ep, bytes_out, transNo)

def CMD_RBLK(ep, numWords):
    global hccSPI
    hccSPI.hcc_qspi_rblk(ep, numWords * 4)

def broadcast_test(flavor):
    # we use WREG, WBLK, RBLK to enable EP and do broadcast test (except for RBLK)
    if flavor == 0 :
        #regular, no broadcast
        #use it to write a different pattern into EP, for following test
        CMD_WREG(0, 0x400000EC, [0x41e000])
        CMD_WREG(0, 0x400000F0, [1])
        CMD_WREG(0, 0x400000E8, [0x3e80001])
        CMD_WBLK(0, 0, [0xAAAAAAAA, 0xBBBBBBBB])
        CMD_WREG(0, 0x400000F0, [1])
        #RBLK is a single transaction!
        CMD_RBLK(0, 2)

    if flavor == 1 :
        #with broadcast - every command as BC, but clean afterwards each one
        send_to_uart("sqspi 3")
        CMD_WREG(1, 0x400000EC, [0x41e000])
        send_to_uart("sqspi 1")
        CMD_WREG(2, 0x400000EC, [0x41e000])
        send_to_uart("sqspi 2")
        CMD_WREG(2, 0x400000EC, [0x41e000])

        send_to_uart("sqspi 3")
        CMD_WREG(1, 0x400000F0, [1])
        send_to_uart("sqspi 1")
        CMD_WREG(2, 0x400000F0, [1])
        send_to_uart("sqspi 2")
        CMD_WREG(2, 0x400000F0, [1])

        send_to_uart("sqspi 3")
        CMD_WREG(1, 0x400000E8, [0x3e80001])
        send_to_uart("sqspi 1")
        CMD_WREG(2, 0x400000E8, [0x3e80001])
        send_to_uart("sqspi 2")
        CMD_WREG(2, 0x400000E8, [0x3e80001])

        send_to_uart("sqspi 3")
        CMD_WBLK(1, 0, [0x11223344, 0x55667788])
        send_to_uart("sqspi 1")
        CMD_WBLK(2, 0, [0x11223344, 0x55667788])
        send_to_uart("sqspi 2")
        CMD_WBLK(2, 0, [0x11223344, 0x55667788])

        send_to_uart("sqspi 3")
        CMD_WREG(1, 0x400000F0, [1])
        send_to_uart("sqspi 1")
        CMD_WREG(2, 0x400000F0, [1])
        send_to_uart("sqspi 2")
        CMD_WREG(2, 0x400000F0, [1])

        #RBLK cannot be done with a broadcast, just one transaction
        send_to_uart("sqspi 1")
        CMD_RBLK(0, 2)
        send_to_uart("sqspi 2")
        CMD_RBLK(0, 2)

    if flavor == 2 :
        #broadcast but now different sequence (clean FPGA1 and keep going)
        send_to_uart("sqspi 3")         #broadcast
        CMD_WREG(1, 0x400000EC, [0x41e000])
        send_to_uart("sqspi 1")
        CMD_WREG(2, 0x400000EC, [0x41e000]) #clean 1
        #keep going on 1, clean 2 later
        CMD_WREG(0, 0x400000F0, [1])
        CMD_WREG(0, 0x400000E8, [0x3e80001])
        CMD_WBLK(0, 0, [0x01020304, 0x50607080])

        #now clean pending 2
        send_to_uart("sqspi 2")
        CMD_WREG(2, 0x400000EC, [0x41e000])
        #keep going on 2
        CMD_WREG(0, 0x400000F0, [1])
        CMD_WREG(0, 0x400000E8, [0x3e80001])
        CMD_WBLK(0, 0, [0x44332211, 0x88776655])

        send_to_uart("sqspi 3")         #broadcast
        CMD_WREG(1, 0x400000F0, [1])
        send_to_uart("sqspi 1")
        CMD_WREG(2, 0x400000F0, [1])    #clean 1
        #do not clean yet 2

        #RBLK cannot be done with a broadcast, just one transaction
        send_to_uart("sqspi 1")
        CMD_RBLK(0, 2)
        send_to_uart("sqspi 2")
        #now clean pending 2
        CMD_WREG(2, 0x400000F0, [1])    #clean 2
        CMD_RBLK(0, 2)

#---------------------------------------------------------------------------------

def Main():
    global hccSPI

    instr = ""
        
    select_port()

    hccSPI = HccQSpiInterface()

    while instr != 'q':
        instr = input("-> ")
        if instr == 'q':
            break;

        r = re.compile('[ \t]+')
        cmd = r.split(instr, 512)

        if cmd[0] == 'wreg':
            l = len(cmd)
            if l < 3:
                print("*E: provide regAddr and regVal")
            else:
                l = l - 2
                bytes_out = bytes()
                for x in range(l):
                    bytes_out = bytes_out + struct.pack('<I', int(cmd[2 + x], 16))
                hccSPI.hcc_qspi_dmax_wreg(int(cmd[1], 16), bytes_out, 0)

        elif cmd[0] == 'rreg':
            l = len(cmd)
            if l < 3:
                print("*E: provide regAddr and numWords")
            else:
                hccSPI.hcc_qspi_dmax_rreg(int(cmd[1], 16), int(cmd[2], 16) * 4, 0)

        elif cmd[0] == 'noop':
            hccSPI.hcc_qspi_noop()

        elif cmd[0] == 'wblk':
            l = len(cmd)
            if l < 3:
                print("*E: provide EP and wrVal")
            else:
                l = l - 2
                bytes_out = bytes()
                for x in range(l):
                    bytes_out = bytes_out + struct.pack('<I', int(cmd[2 + x], 16))
                hccSPI.hcc_qspi_wblk(int(cmd[1], 16), bytes_out, 0)

        elif cmd[0] == 'rblk':
            l = len(cmd)
            if l < 3:
                print("*E: provide EP and numWords")
            else:
                hccSPI.hcc_qspi_rblk(int(cmd[1], 16), int(cmd[2], 16) * 4)

        elif cmd[0] == 'bctest':
            l = len(cmd)
            if l < 2:
                print("*E: provide flavor number")
            else:
                broadcast_test(int(cmd[1], 16))
            
        else:
            #send to UART
            resp = send_to_uart(instr)
            if resp.endswith('\r\n'):
                print(resp, end = '')
            else:
                if len(resp):
                    print(resp)

    print('Good bye')

if __name__ == '__main__':
    Main()

