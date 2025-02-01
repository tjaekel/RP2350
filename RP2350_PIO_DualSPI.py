import rp2
from machine import Pin

#PIO SPI as DualSPI: on Master for SCLK, MOSI plus a Slave with SCLKin and MISO:
#SCLKin on slave state machine is input and needs an external feedback, at best from the far end on external SPI device.
#maximum is 50 MHz! possible - or with further optimization maximum 75 MHz (1/2 SYSCLK)
#it needs two PIOs (too many instructions)
#GPIOs:
#GPIO10 : SCLK
#GPIO11 : MOSI
#GPIO12 : MISO
#GPIO13 : nCS - handled via SW (not by PIO)
#GPIO15 : SCLKin - external wire from SCLK to SCLKin!

@rp2.asm_pio(out_shiftdir=1, autopull=True, pull_thresh=8, sideset_init=(rp2.PIO.OUT_LOW), out_init=rp2.PIO.OUT_LOW)
def spim_cpha0():
    wrap_target()
    
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)
    out(pins, 1)             [0] .side(0)
    nop()                    [0] .side(1)

    wrap()
    
@rp2.asm_pio(in_shiftdir=1, autopush=True, push_thresh=8)
def spis_cpha0():
    wrap_target()
    
    #this is the maximim: 150MHz PIO clock resulting in 75 MHz SCLK
    #in this case: "no need" to use wait(0, gpio, 15) but just above 100MHz PIO clock!
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)
    wait(1, gpio, 15)
    in_(pins, 1)
    #wait(0, gpio, 15)

    wrap()

class PIOSPI:

    def __init__(self, sm_id, pin_mosi, pin_miso, pin_sclk, cpha=False, cpol=False, freq=1000000):
        assert(not(cpol or cpha))
        #SCLKin and MISO input must be configured as input!
        MISO   = Pin(pin_miso, Pin.IN)
        SCLKin = Pin(15, Pin.IN)
        self._smm = rp2.StateMachine(sm_id, spim_cpha0, freq=1*freq, sideset_base=Pin(pin_sclk), out_base=Pin(pin_mosi))
        self._smm.active(1)
        #SPI slave runs always with fastest possible PIO clock!
        self._sms = rp2.StateMachine(sm_id+4, spis_cpha0, freq=machine.freq(), in_base=Pin(pin_miso))
        self._sms.active(1)

    def write_read_blocking(self, wdata):
        rdata = []
        nCS.value(0)
        for b in wdata:
            #LSB is not supported by MicroPython!
            #dependent on shift_dir: LSB or MSB first
            #--shift_dir=0 = MSB
            #self._smm.put(b << 24)
            #rdata.append(self._sm.get() & 0xff)
            #--shift_dir=1 = LSB
            self._smm.put(b)
            rdata.append((self._sms.get() >> 24) & 0xff)
        nCS.value(1)
        return rdata
    
print("PIO DualSPI")
machine.freq(150000000)            #change from 125MHz (RP2040) to 150MHz (RP2350)
print(machine.freq())

nCS = Pin(13, Pin.OUT, value=1)    #nCS pin
#            ID MOSI MISO SCLK
spi = PIOSPI(0, 11, 12, 10, freq=150000000)		#max. 100MHz = 50 MHz SCLK, not faster possible!
#except: we tweak the SPI slave PIO receiver (done here)

nCS.value(0)
wdata = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
rdata = spi.write_read_blocking(wdata)
nCS.value(1)

print("".join("\\x%02x" % i for i in rdata))
    