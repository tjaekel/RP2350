import rp2
from machine import Pin

@rp2.asm_pio(out_shiftdir=1, in_shiftdir=1, autopull=True, pull_thresh=8, autopush=True, push_thresh=8, sideset_init=(rp2.PIO.OUT_LOW), out_init=rp2.PIO.OUT_LOW)
def spi_cpha0():
    set(x, 7)
    # Actual program body follows
    wrap_target()
    pull(ifempty)            .side(0)
    out(pins, 1)			 			[0]
    label("bitloop")
    nop()					 .side(1)	[2]
    in_(pins, 1)             .side(0)
    out(pins, 1)
    jmp(x_dec, "bitloop")    .side(0)
    jmp(not_osre, "bitloop") .side(0) # Fallthru if TXF empties

    #nop()                    .side(0x0)   [1] # CSn back porch - we drive nCS as GPIO
    set(x, 7)
    wrap()


class PIOSPI:

    def __init__(self, sm_id, pin_mosi, pin_miso, pin_sclk, cpha=False, cpol=False, freq=1000000):
        assert(not(cpol or cpha))
        #MISO input must be configured as input!
        MISO = Pin(pin_miso, Pin.IN)
        self._sm = rp2.StateMachine(sm_id, spi_cpha0, freq=4*freq, sideset_base=Pin(pin_sclk), out_base=Pin(pin_mosi), in_base=Pin(pin_miso))
        self._sm.active(1)

    # Note this code will die spectacularly cause a hang: we're not draining the RX FIFO
    def write_blocking(self, wdata):
        #this creates Python error message, but hard to see!
        nCS.value(0)
        for b in wdata:
            self._sm.put(b << 24)
        nCS.value(1)

    def read_blocking(self, n):
        #how can this work without to shift out anything on MOSI?
        data = []
        for i in range(n):
            data.append(self._sm.get() & 0xff)
        return data

    def write_read_blocking(self, wdata):
        rdata = []
        nCS.value(0)
        for b in wdata:
            #dependent on shift_dir: LSB or MSB first
            #shift_dir=0 = MSB
            #self._sm.put(b << 24)
            #rdata.append(self._sm.get() & 0xff)
            #shift_dir=1 = LSB
            self._sm.put(b)
            rdata.append((self._sm.get() >> 24) & 0xff)
        nCS.value(1)
        return rdata
    
print("PIO SPI")
nCS = Pin(13, Pin.OUT, value=1)
#nCS.value(1)
#            ID MOSI MISO SCLK
spi = PIOSPI(0, 11, 12, 10, freq=20000000)
    
#while True:
#athe max. working SCLK is 10 MHz: faster generates bit errors on MISO
nCS.value(0)
wdata = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
rdata = spi.write_read_blocking(wdata)
nCS.value(1)
print(rdata)
    