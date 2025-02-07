import rp2
from machine import Pin
import time
import array

#+++++++++++++++++++++++++++++++++++++++++++++++++
# QSPI implementation with PIO:
# QSPI mode: 3
# Read uses a feedback clock QCLKin, sampling at rising edge
# pins:
# GP7: nCS - SW control
# GP8: nCS2 - SW control
# GP9: QDIR signal (for external level shifter with DIR signal)
# GP10: SCLK
# GP11: DIO0
# GP12: DIO1
# GP13: DIO2
# GP14: DIO3
# GP15: QCLKin - feedback clock - directly used as pin
# Remark:
# the order of the 32bit words written or read are in the wrong "endian":
# we have to flip the bytes before sending or after reading! - see function for it
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
PIO_INPUT_SYNC_BYPASS = const(14)

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
    elif sm < 8:  # PIO 1
        pio = ptr32(uint(PIO1_BASE))
        initial_pc = uint(program[2])
    else:         # PIO 2
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
def sm_input_sync_set(sm: int, gpio: int):
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO 1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    pio[PIO_INPUT_SYNC_BYPASS] = gpio
    
@micropython.viper
def sm_input_sync_get(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO 1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    return (pio[PIO_INPUT_SYNC_BYPASS])

@micropython.viper
def sm_rx_fifo_level(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO 1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    return (pio[PIO_FLEVEL] >> (8 * sm + 4)) & 0x0f

@micropython.viper
def sm_tx_fifo_level(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO 1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    return (pio[PIO_FLEVEL] >> (8 * sm)) & 0x0f

@micropython.viper
def sm_fifo_status(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO 1
        pio = ptr32(uint(PIO1_BASE))
    else:
        pio = ptr32(uint(PIO2_BASE))
    sm %= 4
    return (pio[PIO_FSTAT] >> sm) & 0x01010101

@micropython.viper
def sm_fifo_join(sm: int, action: int):
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    elif sm < 8: # PIO 1
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
    DATA_SIZE = (pio[smx] >> 20) & 0x1f                # to determine the transfer size
    smx = DATA_SIZE
    if DATA_SIZE > 16 or DATA_SIZE == 0:
        DATA_SIZE = 2  # 32 bit transfer
    elif DATA_SIZE > 8:
        DATA_SIZE = 1  # 16 bit transfer
    else:
        DATA_SIZE = 0  # 8 bit transfer

    INCR_WRITE = 1   # 1 for increment while writing
    INCR_READ  = 0   # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 9) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
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
    INCR_READ  = 1  # 0 for no increment while reading
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
        
#RP2350 PIO QSPI example:
#=======================

#GPIO pin offsets:     no speed increase                                                              bit0 = QDIR,      bit1 = QCLK,                bit0..3 = DATA (out, 4 data lanes)
@rp2.asm_pio(fifo_join=rp2.PIO.JOIN_TX, out_shiftdir=0, pull_thresh=32, autopull=False, sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH), out_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def cmdAddr():
    wrap_target()
    set(y, 1)                   .side(2)  #1: we send 2x 32bit words (CMD + ADDR), QCLK=1, QDIR=1 
    label("CMD_ADDR_LOOP")
    set(x, 7)                             #2
    pull()                                #3: get CMD and ADDR words (each 32bit) to send, QDIR = low, QCLK = high
    label("WORD_LOOP")
    out(pins, 4)                .side(0)  #4: it shifts a 32bit on all four lanes! set accordingly the pattern
    jmp(x_dec, "WORD_LOOP")     .side(2)  #5
    jmp(y_dec, "CMD_ADDR_LOOP") .side(2)  #6
    set(x, 5)                             #7: we send just 24bit ALT (6x 4bit)
    pull()                                #8
    label("ALT_LOOP")
    out(pins, 4)                .side(0)  #9
    jmp(x_dec, "ALT_LOOP")      .side(2)  #10
    wrap()
    
#                      no speed increase                               True fails on Read!
@rp2.asm_pio(fifo_join=rp2.PIO.JOIN_TX, out_shiftdir=0, pull_thresh=32, autopull=False, sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH), out_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def dataWrite():
    wrap_target()
    set(x, 7)                   .side(2)  #11: 8x 4bit words = 32bit (NUM here is always -1 for the loop, like a do-while() )
    pull()                                #12: get 32bit data word to send
    label("WORD_OUT")                     #    loop over 32bit word (8x4bit = 32): ATT: it is BIG ENDIAN here (MSB out first)
    out(pins, 4)                .side(0)  #13: shift now 4 bits on 4 parallel data lanes
    jmp(x_dec, "WORD_OUT")      .side(2)  #14:
    wrap()
    #Remark: this generates a gap between the 32bit words sent - but why?

#                                                                                                         bit0: QCLK
@rp2.asm_pio(in_shiftdir=0, pull_thresh=32, push_thresh=32, autopull=False, autopush=False, sideset_init=(rp2.PIO.OUT_HIGH))
def readClk():
    wrap_target()
    set(x, 7)                             #15: generate 8 clocks for reading QSPI 32bit word
    wait(1, irq, 4)                       #16: it waits and clears automatically - wait for TurnAround generated
    label("clkloop")
    nop()                   [1] .side(0)  #17: QCLK starts one instruction cycle after release
    jmp(x_dec, "clkloop")   [1] .side(1)  #18: 50% duty cycle, needs 4x PIO clock
    wrap()
    
#                                                             True fails!                                bit0: QDIR, bit1: QCLK
@rp2.asm_pio(in_shiftdir=0, pull_thresh=32, push_thresh=32, autopull=False, autopush=True, sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH), set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def dataRead():
    wrap_target()
    pull()                                #19: get number of words to read: ATT: NUM-1 is needed here!
    mov(y, osr)             [1] .side(1)  #20: keep number of words to read, QCLK=0, QDIR=1 already - here as earliest as possible
    set(pindirs, 0x0)       [1] .side(3)  #21: change direction, QCLK=1, QDIR=1
    nop()                   [1] .side(1)  #22: QCLK=0, QDIR=1
    nop()                   [0] .side(3)  #23: two turnaround clocks generated
    label("ALL_READ_LOOP")
    set(x, 7)                             #24: we have 8x 4bit = 32bit (4 lanes)
    irq(4)                                #25: two turnaround clocks generated - release the Read clock generator = one instruction later
    label("WORD_READ_LOOP")               #    wait for rising QCLKfb
    wait(0, pin, 4)                       #26:
    wait(1, pin, 4)                       #27: GPIO11.14 = QD0..QD3, GPIO15 = QCLKin - the same as above - assume QCLK was 0 in between!
    in_(pins, 4)            [0]           #28: get 4 bits from 4 pallel data lanes - it samples one instruction cycle after falling edge!
                                          #    one instruction cycle plus delay: QCLK still 1
                                          #    make sure QCLK is 0 in between so that "wait(1, pin, 4)" waits for raising edge!!!
    jmp(x_dec, "WORD_READ_LOOP")          #29: one instruction cycle QCLK - it should go 0 now
    #push()                               #  : we use autopush to save nmumber of instructions
    jmp(y_dec, "ALL_READ_LOOP")           #30: keep going until all words read
    set(pindirs, 0xf)           .side(2)  #31: set nCS high, de-assert QDIR signal = end of transfer - takes a while to see - WHY???
                                          #  : are we out of the 32 instrcutions? MAX. 32!
    wrap()
    
machine.freq(150000000)                   #change from 125MHz (RP2040) to 150MHz (RP2350)

FREQ = 10000000                           #our frequency to generate (SCLK) - max. is 25MHz - 10MHz works OK
SM_NO = 0                                 #PIO2 does not work (yet)!

#GPIO 7, 8 for nCS, nCS2
nCS  = Pin(7, Pin.OUT, value=1)
nCS2 = Pin(8, Pin.OUT, value=1)

#QCLK feedback input - we use it directly as pin, out_base 11 + 4 = 15
SCLKin = Pin(15, Pin.IN)

#RE signal:
RE = Pin(16, Pin.OUT, value=0)            #default: a WRITE

#the SM for sending the pre-fix: CMD (single-lane), ADDR (32bit, 4-lane), ALT (24bit, 4-lane)
#                                                                   QDIR, QCLK          DIO0..DIO3
sm0 = rp2.StateMachine(SM_NO + 0, cmdAddr, freq=2*FREQ, sideset_base=Pin(9), out_base=Pin(11))
sm0.active(1)

#the SM to continue to append a WRITE transaction (no Turn Around)
#                                                                   QDIR, QCLK          DIO0..DIO3
sm1 = rp2.StateMachine(SM_NO + 1, dataWrite, freq=2*FREQ, sideset_base=Pin(9), out_base=Pin(11))
sm1.active(1)

#the SM for the Read QCLK generation (8 pulses per 32bit word)     the QCLK pin
sm2 = rp2.StateMachine(SM_NO + 2, readClk, freq=4*FREQ, sideset_base=Pin(10))
sm2.active(1)

#the SM to continue to append a READ transaction (with 2bit Turn Around) - generates turnaround clocks - same clock reference!
sm3 = rp2.StateMachine(SM_NO + 3, dataRead, freq=4*FREQ, sideset_base=Pin(9), in_base=Pin(11), set_base=Pin(11))
sm3.active(1)

#disable clock synchronizer for QD0..QD3, QCLKfb (GPIO11..GPIO15) - no effect
#sm_input_sync_set(SM_NO, 0x0000F800)

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

def cid():
    #-- WRITE --:
    RE.value(0)                  #announce a WRITE cycle

    CmdAddrAlt = array.array('i', [0x11100000, 0x00000000, 0x00001F00])
    WrData = array.array('i', [0x00040580, 0x400B0FD0, 0xAAA00000])
    endianReverse(WrData, 3*4)
    nCS.value(0)                 #direct before data transfer
    #for i in range(3):
    #    sm0.put(CmdAddrAlt[i])
    #while sm_tx_fifo_level(SM_NO + 0) > 0:
    #    pass

    #with DMA: way faster burst              
    sm_dma_put(0, 0, CmdAddrAlt, 3)
    while sm_tx_fifo_level(SM_NO + 0) > 0:
        pass
            
    Num2Wr = 3
    #for i in range(Num2Wr):
    #    sm1.put(WrData[i])                 #the byte order is "inversed"! flip before to BIG_ENDIAN
    #    #why do we have such large gaps between words?
    #    while sm_tx_fifo_level(SM_NO + 1) > 3:
    #        pass
     
    #with DMA: way faster burst - just a gap between 1st and 2nd DMA!
    sm_dma_put(0, 1, WrData, Num2Wr)
    while sm_tx_fifo_level(SM_NO + 0) > 0:
        pass
    
    nCS.value(1)
    
    #-- READ --:
    CmdAddrAlt = array.array('i', [0x11100001, 0x00000000, 0x00001E00])
    RdData = array.array('i', [0, 0, 0, 0, 0])
    RE.value(1)                  #announce a READ cycle
    nCS.value(0)                 #direct before data transfer
    #RE.value(1)                  #announce a READ cycle - short after nCS going low - before 1st QCLK
        
    #for i in range(3):
    #    sm0.put(CmdAddrAlt[i])
    #while sm_tx_fifo_level(SM_NO + 0) > 0:
    #    pass

    #with DMA: way faster burst                 
    sm_dma_put(0, 0, CmdAddrAlt, 3)
    #while sm_tx_fifo_level(SM_NO + 0) > 0:
    #    pass

    Num2Rd = 5                                #up to 5 words are read in a single burst, later with gaps
    sm3.put(Num2Rd - 1)                       #ATT: inside SM it is NUM-1 for NUM loops!
                                              #this is slow and when printing - a large gap
    for i in range(Num2Rd):                   #after 5 words we get gaps
        r = sm3.get()                         #the same issue here: the byte order is "inversed"! flip it back to LITTLE ENDIAN
        #print(hex(r))
        RdData[i] = r
    nCS.value(1)                              #WHY does it take so much time to de-assert nCS????
          
    #The Get DMA does not work!!! - loop stalls and it reads just the first word into buffer!
    #sm3.put(Num2Rd - 1)                      #write the number of words -1
    #sm_dma_get(0, 3, RdData, Num2Rd)         #can we see any DMA error code
    #time.sleep_ms(1000)
    #print(sm_fifo_status(SM_NO + 3))
    #while sm_rx_fifo_level(SM_NO + 3) > 0:   #DOES NOT WORK, always 0
    #    print(sm_rx_fifo_level(SM_NO + 3))
    #    pass
    #nCS.value(1)                             #why so much time until nCS goes high? On Write much faster!

    endianReverse(RdData, 4*4)
    for value in RdData:
        #print(f"{value:08X}")
        print(hex(value & 0xFFFFFFFF))
        
cid()

    