from machine import SPI
from machine import Pin

#spi = SPI(0)
#spi = SPI(0, 100_000)
spi = SPI(0, 10000000, polarity=0, phase=0)

#spi.write('test')
#print(spi.read(5))

nCS = Pin(21, Pin.OUT)
buf = bytearray(9)
nCS.value(0)
spi.write_readinto('Hello SPI', buf)
nCS.value(1)
print(buf)