import rp2
from machine import Pin

@rp2.asm_pio(out_shiftdir=0, autopull=True, pull_thresh=8, autopush=True, push_thresh=8, sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW), out_init=rp2.PIO.OUT_LOW)
def spi_cpha0():
    # Note X must be preinitialised by setup code before first byte, we reload after sending each byte
    # Would normally do this via exec() but in this case it's in the instruction memory and is only run once
    set(x, 6)
    # Actual program body follows
    wrap_target()
    pull(ifempty)            .side(0x1)   [1]
    label("bitloop")
    out(pins, 1)             .side(0x0)   [1]
    in_(pins, 1)             .side(0x2)
    jmp(x_dec, "bitloop")    .side(0x2)

    out(pins, 1)             .side(0x0)
    set(x, 6)                .side(0x0) # Note this could be replaced with mov x, y for programmable frame size
    in_(pins, 1)             .side(0x2)
    jmp(not_osre, "bitloop") .side(0x2) # Fallthru if TXF empties

    nop()                    .side(0x0)   [1] # CSn back porch
    wrap()


class PIOSPI:

    def __init__(self, sm_id, pin_mosi, pin_miso, pin_ncs, cpha=False, cpol=False, freq=1000000):
        assert(not(cpol or cpha))
        self._sm = rp2.StateMachine(sm_id, spi_cpha0, freq=4*freq, sideset_base=Pin(pin_ncs), out_base=Pin(pin_mosi), in_base=Pin(pin_miso))
        self._sm.active(1)

    # Note this code will die spectacularly cause we're not draining the RX FIFO
    def write_blocking(self, wdata):
        for b in wdata:
            self._sm.put(b << 24)

    def read_blocking(self, n):
        data = []
        for i in range(n):
            data.append(self._sm.get() & 0xff)
        return data

    def write_read_blocking(self, wdata):
        rdata = []
        for b in wdata:
            self._sm.put(b << 24)
            rdata.append(self._sm.get() & 0xff)
        return rdata
    
    def write_read_blocking2(self, wdata):
        rdata = []
        i = 0
        for b in wdata:
            self._sm.put(b << 24)
            i = i + 1
        for j in range(i):
            rdata.append(self._sm.get() & 0xff)
        return rdata
    
print("PIO SPI")
#ATT: sideset uses 21 as nCS and 22 as SCLK - pin-compatible with regular SPI
spi = PIOSPI(0, 23, 20, 21, freq=100000)
wdata = [1,2,3,4,5,6,7,8,9,10]
rdata = spi.write_read_blocking(wdata)
print(rdata)