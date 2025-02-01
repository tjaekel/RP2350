from machine import SPI
from machine import Pin
import array

#SPI (regular SPI), works, but SCLK can just set as 23.8 (25) MHz as fastest!

# table to reverse the bits of a nibble
REVNIB = bytearray(b'\x00\x08\x04\x0C\x02\x0A\x06\x0E' +
                   b'\x01\x09\x05\x0D\x03\x0B\x07\x0F')

# procedure to invert the bits of a byte:
# translate and exchange the nibbles
def bitReverse(x):
    return (REVNIB[x & 0x0F] << 4) | (REVNIB[(x & 0xF0) >> 4])

@micropython.asm_thumb
def endianReverse(r0, r1):               # bytearray, len(bytearray)
    add(r4, r0, r1)
    sub(r4, 1) # end address
    label(LOOP)
    ldrb(r5, [r0, 0])
    ldrb(r6, [r4, 0])
    strb(r6, [r0, 0])
    strb(r5, [r4, 0])
    add(r0, 1)
    sub(r4, 1)
    cmp(r4, r0)
    bpl(LOOP)
    
@micropython.asm_thumb
def bitReverseASM(r0, r1):               # bytearray, len(bytearray)
    label(LOOP)
    ldrb(r5, [r0, 0])
    rbit(r6, r5)
    mov(r5, 24)
    ror(r6, r5)
    strb(r6, [r0, 0])
    add(r0, 1)
    sub(r1, 1)
    cmp(r1, 0)
    bpl(LOOP)
    
def bitReverseArray(x):
    for i in range(len(x)):
        x[i] = bitReverse(x[i])
    return x

#10MHz results in 8MHz
#20MHz results in 11.9MHz
#40MHz results in 25MHz - too fast (bit errors on read - MISO sampled with 1bit shifted!)
#30MHz results in 23.81MHz - faster I cannot set!
#fastest working: 23MHz = 12.5 MHz
#print(spi) shows 24 MHz - as the max. speed taken!
spi = SPI(1, 40000000, polarity=0, phase=1, miso=machine.Pin(12), firstbit=machine.SPI.MSB, bits=8)
#bits=16 generates 16bit but still taking bytes to send!
#phase=1 works a bit better, but I can set only up to 23.81 (25 MHz), it samples MISO with falling edge
#which is more reliable due to the "rount trip delay"
#strange is: phase=0 is byte bursts on SCLK, phase=1 is a smooth continuous SCLK!

print(spi)

nCS = Pin(13, Pin.OUT, value=1)
#nCS.value(1)
nCS2 = Pin(14, Pin.OUT, value=1)
#nCS2.value(1)

rxbuf = bytearray(4)
txbuf = bytearray(4)
txbuf[0] = 0x02
txbuf[1] = 0xE0
txbuf[2] = 0x00
txbuf[3] = 0x00
#endianReverse(txbuf, len(txbuf))
#txbuf = bitReverseArray(txbuf)
bitReverseASM(txbuf, len(txbuf))

#xxBuf = array.array('H', [0x4007, 0x0000])
#yyBuf = array.array('H', [0, 0])
#print(xxBuf)

nCS.value(0)
#spi.write_readinto(txbuf, rxbuf)
spi.write_readinto(txbuf, rxbuf)
nCS.value(1)

#rxbuf = bitReverseArray(rxbuf)
bitReverseASM(rxbuf, len(rxbuf))

#print(rxbuf)
print("".join("0x%02x " % i for i in rxbuf))

