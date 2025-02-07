import rp2
from machine import Pin
import time

#+++++++++++++++++++++++++++++++++++++++++++++++++
# QSPI implementation with PIO:
# QSPI mode: 3
# pins:

# GP7 (pin 10): nCS - SW control
# GP8 (pin 11): nCS2 - SW control
# GP9 (pin 12): QDIR signal (for external level shifter with DIR signal)
#               QDIR = 0 --> WRITE, QDIR = 1 --> READ
# GP10 (pin 14): SCLK
# GP11 (pin 15): DIO0
# GP12 (pin 16): DIO1
# GP13 (pin 17): DIO2
# GP14 (pin 19): DIO3
# Remark:
# the order of the 32bit words written or read are in the wrong "endian":
# we have to flip the bytes before sending or after reading!
#+++++++++++++++++++++++++++++++++++++++++++++++++

#-------------------------------------------------
# rp_util.py:
#
# set set of small functions supporting the use of the PIO
# we use this in order to free instructions on PIO:
# example: instead to wait for PIO state machine has completed, e.g. via "push()"
# and "sm.get()" - we check the FIFO level (or PIO SM status), which saves PIO instructions
#

PIO0_BASE = const(0x50200000)
PIO1_BASE = const(0x50300000)
PIO2_BASE = const(0x50400000)

# register indices into the array of 32 bit registers
PIO_CTRL = const(0)
PIO_FSTAT = const(1)
PIO_FLEVEL = const(3)
SM_REG_BASE = const(0x32)  # start of the SM state tables
# register offsets into the per-SM state table
SMx_CLKDIV = const(0)
SMx_EXECCTRL = const(1)
SMx_SHIFTCTRL = const(2)
SMx_ADDR = const(3)
SMx_INSTR = const(4)
SMx_PINCTRL = const(5)

SMx_SIZE = const(6)  # SM state table size

SM_FIFO_RXFULL  = const(0x00000001)
SM_FIFO_RXEMPTY = const(0x00000100)
SM_FIFO_TXFULL  = const(0x00010000)
SM_FIFO_TXEMPTY = const(0x01000000)

@micropython.viper
def sm_restart(sm: int, program) -> uint:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
        initial_pc = uint(program[1])
    elif sm < 8:  # PIO1
        pio = ptr32(uint(PIO1_BASE))
        initial_pc = uint(program[2])
    else:        # PIO2
        pio = ptr32(uint(PIO2_BASE))
        initial_pc = uint(program[3])
    sm %= 4
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_INSTR
    pio[PIO_CTRL] = 1 << (sm + 4)  # reset the registers
    # now execute a jmp instruction to the initial PC
    # Since the code for the unconditional jump is
    # 0 + binary address, this is effectively the address
    # to be written in the INSTR register.
    pio[smx] = initial_pc  # set the actual PC to the start adress
    return initial_pc

@micropython.viper
def sm_rx_fifo_level(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    return (pio[PIO_FLEVEL] >> (8 * sm + 4)) & 0x0f

@micropython.viper
def sm_tx_fifo_level(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    return (pio[PIO_FLEVEL] >> (8 * sm)) & 0x0f

@micropython.viper
def sm_fifo_status(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    return (pio[PIO_FSTAT] >> sm) & 0x01010101

@micropython.viper
def sm_fifo_join(sm: int, action: int):
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_SHIFTCTRL

    if action == 0:  # disable join
        pio[smx] = ((pio[smx] >> 16) & 0x3fff) << 16
    elif action == 1:  # join RX
        pio[smx] = (((pio[smx] >> 16) & 0x3fff) | (1 << 15)) << 16
    elif action == 2:  # join TX
        pio[smx] = (((pio[smx] >> 16) & 0x3fff) | (1 << 14)) << 16

#
# PIO register byte address offsets
#
PIO_TXF0 = const(0x10)
PIO_TXF1 = const(0x14)
PIO_TXF2 = const(0x18)
PIO_TXF3 = const(0x1c)
PIO_RXF0 = const(0x20)
PIO_RXF1 = const(0x24)
PIO_RXF2 = const(0x28)
PIO_RXF3 = const(0x2c)

#
# DMA registers
#
DMA_BASE = const(0x50000000)
# Register indices into the DMA register table
READ_ADDR = const(0)
WRITE_ADDR = const(1)
TRANS_COUNT = const(2)
CTRL_TRIG = const(3)
CTRL_ALIAS = const(4)
TRANS_COUNT_ALIAS = const(9)
CHAN_ABORT = const(0x111)  # Address offset / 4
BUSY = const(1 << 24)
#
# Template for assembling the DMA control word
#
IRQ_QUIET = const(1)  # do not generate an interrupt
CHAIN_TO = const(0)  # do not chain
RING_SEL = const(0)
RING_SIZE = const(0)  # no wrapping
HIGH_PRIORITY = const(1)
EN = const(1)
#
# Read from the State machine using DMA:
# DMA channel, State machine number, buffer, buffer length
#
@micropython.viper
def sm_dma_get(chan:int, sm:int, dst:ptr32, nword:int) -> int:

    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
        TREQ_SEL = sm + 4  # range 4-7
    else:  # PIO1
        sm %= 4
        pio = ptr32(int(PIO1_BASE))
        TREQ_SEL = sm + 12  # range 12 - 13
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_SHIFTCTRL  # get the push threshold
    DATA_SIZE = (pio[smx] >> 20) & 0x1f  # to determine the transfer size
    smx = DATA_SIZE
    if DATA_SIZE > 16 or DATA_SIZE == 0:
        DATA_SIZE = 2  # 32 bit transfer
    elif DATA_SIZE > 8:
        DATA_SIZE = 1  # 16 bit transfer
    else:
        DATA_SIZE = 0  # 8 bit transfer

    INCR_WRITE = 1  # 1 for increment while writing
    INCR_READ = 0  # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 6) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                        (HIGH_PRIORITY << 1) | (EN << 0))
    dma[READ_ADDR] = uint(pio) + PIO_RXF0 + sm * 4
    dma[WRITE_ADDR] = uint(dst)
    dma[TRANS_COUNT] = nword
    dma[CTRL_TRIG] = DMA_control_word  # and this starts the transfer
    return DMA_control_word

#
# Write to the State machine using DMA:
# DMA channel, State machine number, buffer, buffer length
#
@micropython.viper
def sm_dma_put(chan:int, sm:int, src:ptr32, nword:int) -> int:

    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
        TREQ_SEL = sm  # range 0-3
    else:  # PIO1
        sm %= 4
        pio = ptr32(uint(PIO1_BASE))
        TREQ_SEL = sm + 8  # range 8-11
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_SHIFTCTRL  # get the pull threshold
    DATA_SIZE = (pio[smx] >> 25) & 0x1f  # to determine the transfer size
    if DATA_SIZE > 16 or DATA_SIZE == 0:
        DATA_SIZE = 2  # 32 bit transfer
    elif DATA_SIZE > 8:
        DATA_SIZE = 1  # 16 bit transfer
    else:
        DATA_SIZE = 0  # 8 bit transfer

    INCR_WRITE = 0  # 1 for increment while writing
    INCR_READ = 1  # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 9) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                        (HIGH_PRIORITY << 1) | (EN << 0))
    dma[READ_ADDR] = uint(src)
    dma[WRITE_ADDR] = uint(pio) + PIO_TXF0 + sm * 4
    dma[TRANS_COUNT] = nword
    dma[CTRL_TRIG] = DMA_control_word  # and this starts the transfer
    return DMA_control_word

#
# UART registers
#
UART0_BASE = const(0x40034000)
UART1_BASE = const(0x40038000)

#
# Read from UART using DMA:
# DMA channel, UART number, buffer, buffer length
#
@micropython.viper
def uart_dma_read(chan:int, uart_nr:int, data:ptr32, nword:int) -> int:

    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    if uart_nr == 0:   # UART0
        uart_dr = uint(UART0_BASE)
        TREQ_SEL = 21
    else:  # UART1
        uart_dr = uint(UART1_BASE)
        TREQ_SEL = 23
    DATA_SIZE = 0  # byte transfer
    INCR_WRITE = 1  # 1 for increment while writing
    INCR_READ = 0  # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 9) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                        (HIGH_PRIORITY << 1) | (EN << 0))
    dma[READ_ADDR] = uart_dr
    dma[WRITE_ADDR] = uint(data)
    dma[TRANS_COUNT] = nword
    dma[CTRL_TRIG] = DMA_control_word  # and this starts the transfer
    return DMA_control_word
#
# Get the current transfer count
#
@micropython.viper
def dma_transfer_count(chan:uint) -> int:
    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    return dma[TRANS_COUNT]
#
# Get the current write register value
#
@micropython.viper
def dma_write_addr(chan:uint) -> int:
    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    return dma[WRITE_ADDR]

#
# Get the current read register value
#
@micropython.viper
def dma_read_addr(chan:uint) -> int:
    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    return dma[READ_ADDR]
#
# Abort an transfer
#
@micropython.viper
def dma_abort(chan:uint):
    dma=ptr32(uint(DMA_BASE))
    dma[CHAN_ABORT] = 1 << chan
    while dma[CHAN_ABORT]:
        time.sleep_us(10)

#-------------------------------------------------
        
#-----------------------------------------------------------------------------------
#Utility functions: swap the endian in a 32bit word (needed for QSPI data part)

@micropython.asm_thumb
def endianReverse(r0, r1):               # bytearray pointer, len(bytearray)
    label(LOOP)
    ldrb(r2, [r0, 0])
    ldrb(r3, [r0, 3])
    strb(r3, [r0, 0])
    strb(r2, [r0, 3])
    ldrb(r2, [r0, 2])
    ldrb(r3, [r0, 1])
    strb(r3, [r0, 2])
    strb(r2, [r0, 1])
    add(r0, 4)
    sub(r1, 4)
    bpl(LOOP)
    
#RP2350 PIO QSPI example:
#=======================

#GPIO pin offsets:                                                           bit0 = QDIR,      bit1 = QCLK,                bit0..3 = DATA (out, 4 data lanes)
@rp2.asm_pio(out_shiftdir=0, pull_thresh=32, autopull=False, sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH), out_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def pio():
    wrap_target()
    set(y, 1)                   .side(2)  #1: we send 2x 32bit words (CMD + ADDR), QCLK=0, QDIR=0 
    label("CMD_ADDR_LOOP")
    set(x, 7)                             #2
    pull()                                #3: get CMD and ADDR words (each 32bit) to send, QDIR = low, SCLK = low
    label("WORD_LOOP")
    out(pins, 4)                .side(0)  #4: it shifts a 32bit on all four lanes! set accordingly the pattern
    jmp(x_dec, "WORD_LOOP")     .side(2)  #5
    jmp(y_dec, "CMD_ADDR_LOOP") .side(2)  #6
    set(x, 5)                             #7: we send just 24bit ALT (6x 4bit)
    pull()                                #8
    label("ALT_LOOP")
    out(pins, 4)                .side(0)  #9
    jmp(x_dec, "ALT_LOOP")      .side(2)  #10
    
    #push()                     .side(2)  #  : keep nCS low, push() just here to sync with main() until done
    wrap()
#                                                                             bit0 = QDIR,      bit1 = QCLK,
@rp2.asm_pio(out_shiftdir=0, pull_thresh=32, autopull=False, sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH), out_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def dataWrite():
    wrap_target()
    pull()                                #11: get number of 32bit words to send: ATT: NUM-1 is needed here!
    mov(y, osr)                           #12: keep number of words to send
    label("ALL_DATA_OUT")                 #  : loop over all words to send
    set(x, 7)                             #13: 8x 4bit words = 32bit (NUM here is always -1 for the loop, like a do-while() )
    pull()                                #14: get 32bit data word to send
    label("WORD_OUT")                     #    loop over 32bit word (8x4bit = 32): ATT: it is BIG ENDIAN here (MSB out first)
    out(pins, 4)                .side(0)  #15: shift now 4 bits on 4 parallel data lanes
    jmp(x_dec, "WORD_OUT")      .side(2)  #16:
    #push()                               #  : wait for done of one 32bit word- otherwise a clock glitch!
    jmp(y_dec, "ALL_DATA_OUT")            #17:
    #nop()                       .side(2) #  : set nCS high = end of transfer, there is a gap after last SCLK
    wrap()
    #Remark: this generates a gap between the 32bit words sent - but why?
    
#                                                                                                                bit0: QDIR, bit1: QCLK
@rp2.asm_pio(in_shiftdir=0, pull_thresh=32, push_thresh=32, autopull=False, autopush=False, sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH), set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def dataRead():
    wrap_target()
    pull()                                #18: get number of words to read: ATT: NUM-1 is needed here!
    set(pindirs, 0x0)       [2] .side(2)  #19: change direction, QCLK=1, QDIR still 0
    mov(y, osr)             [2] .side(1)  #20: keep number of words to read, QCLK=0, QDIR=1
    nop()                   [2] .side(3)  #21: generate 2 TurnAround cycles, QCLK=1, generate DIR signal (high)
    nop()                   [2] .side(1)
    nop()                   [2] .side(3)  #22: [1]...[3] is gap after turnaround
    label("ALL_READ_LOOP")
    set(x, 7)                             #23: we have 8x 4bit = 32bit (4 lanes)
    label("WORD_READ_LOOP")
    nop()                   [2] .side(1)  #24:
    nop()                   [0] .side(3)  #25: delay sampling with raising edge a bit - ATT: it lowers the QCLK!
    in_(pins, 4)                          #26: get 4 bits from 4 pallel data lanes
    #here: autopush delays! we get the CLK staying high for a wile
    jmp(x_dec, "WORD_READ_LOOP")          #27:
    push()                                #28: push a 32bit word to main()
    jmp(y_dec, "ALL_READ_LOOP")           #29: keep going until all words read
    set(pindirs, 0xf)           .side(2)  #30: set nCS high, de-assert QDIR signal = end of transfer
                                          #  : are we out of the 32 instrcutions?!
    wrap()

machine.freq(150000000)                   #change from 125MHz (RP2040) to 150MHz (RP2350)

FREQ = 1000000                           #our frequency to generate (SCLK) - max. is 25MHz - 10MHz works OK
SM_NO = 0                                 #PIO2 does not work (yet)!

#GPIO 7, 8 for nCS, nCS2
nCS  = Pin(7, Pin.OUT, value=1)
nCS2 = Pin(8, Pin.OUT, value=1)

#the SM for sending the pre-fix: CMD (single-lane), ADDR (32bit, 4-lane), ALT (24bit, 4-lane)
sm0 = rp2.StateMachine(SM_NO + 0, pio, freq=2*FREQ, sideset_base=Pin(9), out_base=Pin(11))
sm0.active(1)

#the SM to continue to append a WRITE transaction (no Turn Around)
sm1 = rp2.StateMachine(SM_NO + 1, dataWrite, freq=2*FREQ, sideset_base=Pin(9), out_base=Pin(11))
sm1.active(1)

#the SM to continue to append a READ transaction (with 2bit Turn Around) - we double the speed to delay sampling
#with the falling edge
sm2 = rp2.StateMachine(SM_NO + 2, dataRead, freq=6*FREQ, sideset_base=Pin(9), in_base=Pin(11), set_base=Pin(11))
sm2.active(1)

oldR = 0x12345678   #just print changes

numCycles = 1

while numCycles > 0:
    numCycles = numCycles - 1
    
    #WRITE 0x400B0FA0 0xE0120005:
    #WRITE:
    nCS.value(0)
    sm0.put(0x11100000)         #bit 28,24,20,16,12,8,4,0 = 0xE0
    sm0.put(0x00000000)         #32bit
    sm0.put(0x00001F00)         #shift <<8 = 0x00001F <<8
    while sm_tx_fifo_level(SM_NO + 0) > 0:
        pass
    #sm0.get()
    
    Num2Wr = 6
    sm1.put(Num2Wr -1)                  #ATT: inside SM it is NUM-1 for NUM loops!
    sm1.put(0x80010400)                 #the byte order is "inversed"! flip before to LITTLE_ENDIAN = 0x00040580
    while sm_tx_fifo_level(SM_NO + 1) > 3:
        pass
    sm1.put(0xA00F0B40)                 #0x400B0FD0
    while sm_tx_fifo_level(SM_NO + 1) > 3:
        pass
    sm1.put(0x0000D0AE)                 #0x400B0FD0
    while sm_tx_fifo_level(SM_NO + 1) > 3:
        pass
    sm1.put(0x00000000)                 #0x400B0FD0
    while sm_tx_fifo_level(SM_NO + 1) > 3:
        pass
    sm1.put(0x050012E0)                 #0xAAA00000
    #why do we have such large gaps between words?
    while sm_tx_fifo_level(SM_NO + 1) > 3:
        pass
    sm1.put(0xFAFFED1F)                 #0x400B0FD0
    while sm_tx_fifo_level(SM_NO + 1) > 3:
        pass
    #sm1.get()
    nCS.value(1)

    #READ:
    nCS.value(0)
    sm0.put(0x11100001)                 #0xE1
    sm0.put(0x00000000)                 #32bit
    sm0.put(0x00001E00)                 #shift <<8 = 0x00001E <<8
    while sm_tx_fifo_level(SM_NO + 0) > 0:
        pass
    #sm0.get()
    
    Num2Rd = 3                          #read 5 words
    sm2.put(Num2Rd - 1)                 #ATT: inside SM it is NUM-1 for NUM loops!
    for i in range(Num2Rd):
        r = sm2.get()                   #the same issue here: the byte order is "inversed"! flip it back to LITTLE ENDIAN
        print(hex(r))
    nCS.value(1)
