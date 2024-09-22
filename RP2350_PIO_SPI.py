import rp2
from machine import Pin

@rp2.asm_pio(out_shiftdir=0, autopull=True, pull_thresh=8, autopush=True, push_thresh=8, sideset_init=(rp2.PIO.OUT_LOW), out_init=rp2.PIO.OUT_LOW)
def spi_cpha0():
    # Note X must be preinitialised by setup code before first byte, we reload after sending each byte
    # Would normally do this via exec() but in this case it's in the instruction memory and is only run once
    set(x, 6)
    # Actual program body follows
    wrap_target()
    pull(ifempty)            .side(0x0)   [1]
    label("bitloop")
    out(pins, 1)             .side(0x0)   [1]
    in_(pins, 1)             .side(0x1)
    jmp(x_dec, "bitloop")    .side(0x1)

    out(pins, 1)             .side(0x0) # last bit (of 8) and prepare next byte shift
    set(x, 6)                .side(0x0) # Note this could be replaced with mov x, y for programmable frame size
    in_(pins, 1)             .side(0x1)
    jmp(not_osre, "bitloop") .side(0x1) # Fallthru if TXF empties

    #nop()                    .side(0x0)   [1] # CSn back porch - we drive nCS as GPIO
    wrap()


class PIOSPI:

    def __init__(self, sm_id, pin_mosi, pin_miso, pin_sclk, cpha=False, cpol=False, freq=1000000):
        assert(not(cpol or cpha))
        #MISO input must be configured as input!
        MISO = Pin(pin_miso, Pin.IN)
        self._sm = rp2.StateMachine(sm_id, spi_cpha0, freq=4*freq, sideset_base=Pin(pin_sclk), out_base=Pin(pin_mosi), in_base=Pin(pin_miso))
        self._sm.active(1)

    # Note this code will die spectacularly cause we're not draining the RX FIFO
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
            self._sm.put(b << 24)
            rdata.append(self._sm.get() & 0xff)
        nCS.value(1)
        return rdata
    
print("PIO SPI")
nCS = Pin(0, Pin.OUT)
nCS.value(1)
spi = PIOSPI(0, 3, 4, 2, freq=15000000)
    
while True:
    #after 1 MHz SCLK - the clock becomes not 50% duty cycle and slower,
    #the max. SCLK is 37,500,000 Hz, but beyond 15.1 MHz we get bit errors on MISO!
    #just 1MHz seems to be OK for 50% duty cycle
    nCS.value(0)
    wdata = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
    rdata = spi.write_read_blocking(wdata)
    nCS.value(1)
    print(rdata)