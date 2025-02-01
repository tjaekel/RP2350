import rp2
from machine import Pin

#PIO SPI - maximum is 25 MHz!

@micropython.asm_thumb
def ReadMem(r0):
    ldr(r0, [r0, 0])

@micropython.asm_thumb
def WriteMem(r0, r1):
    str(r1, [r0, 0])

@rp2.asm_pio(out_shiftdir=1, in_shiftdir=1, autopull=True, pull_thresh=8, autopush=True, push_thresh=8, sideset_init=(rp2.PIO.OUT_LOW), out_init=rp2.PIO.OUT_LOW)
def spi_cpha0():
    global DELAY
    wrap_target()
    
    out(pins, 1)			 [3]	.side(0)		#change all the [4] into [3] - it starts FAILING!
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)		#change all the [4] into [2] - it FAILS completely!
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)
    in_(pins, 1)             [0]	.side(1)
    out(pins, 1)			 [3]	.side(0)
    in_(pins, 1)             [0]	.side(1)

    wrap()

class PIOSPI:

    def __init__(self, sm_id, pin_mosi, pin_miso, pin_sclk, cpha=False, cpol=False, freq=1000000):
        assert(not(cpol or cpha))
        #MISO input must be configured as input!
        MISO = Pin(pin_miso, Pin.IN, Pin.PULL_UP)
        self._sm = rp2.StateMachine(sm_id, spi_cpha0, freq=1*freq, sideset_base=Pin(pin_sclk), out_base=Pin(pin_mosi), in_base=Pin(pin_miso))
        self._sm.active(1)

    def write_read_blocking(self, wdata):
        rdata = []
        nCS.value(0)
        for b in wdata:
            #dependent on shift_dir: LSB or MSB first
            #--shift_dir=0 = MSB
            #self._sm.put(b << 24)
            #rdata.append(self._sm.get() & 0xff)
            #--shift_dir=1 = LSB
            self._sm.put(b)
            rdata.append((self._sm.get() >> 24) & 0xff)
        nCS.value(1)
        return rdata
    
print("PIO SPI")
machine.freq(150000000)
print(machine.freq())

#read GPIO12 register config - before:
v = ReadMem(0x40038034)
print("".join("1:\\ x%02x" % v))

nCS = Pin(13, Pin.OUT, value=1)
#            ID MOSI MISO SCLK
#max. PIO clock is 125MHz - why not 150? 125 MHz is the old RP2040 SYSCLK speed!
spi = PIOSPI(0, 11, 12, 10, freq=125000000)
    
#GPIO12 - MOSI:
#read GPIO12 register config - after:
v = ReadMem(0x40038030)
print("".join("2:\\ x%02x" % v))
v = WriteMem(0x40038030, 0x60)		#drive strength, slew rate
v = ReadMem(0x40038030)
print("".join("3:\\ x%02x" % v))

#read GPIO12 register config - after: set other config - but it does not improve really!
v = ReadMem(0x40038034)
print("".join("4:\\ x%02x" % v))
v = WriteMem(0x40038034, 0x48)		#pull-up, Schmitt-trigger
v = ReadMem(0x40038034)
print("".join("5:\\ x%02x" % v))

#while True:
#athe max. working SCLK is below 25 MHz: faster generates bit errors on MISO
nCS.value(0)
wdata = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
rdata = spi.write_read_blocking(wdata)
nCS.value(1)

print("".join("\\x%02x" % i for i in rdata))
