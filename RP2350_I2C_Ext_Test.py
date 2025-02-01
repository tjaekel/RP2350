from machine import I2C
from machine import Pin

#I2C GPIO extender test

I2CADDR = 0x74		#0x74..0x76

i2c = I2C(0, scl=5, sda=4, freq=100000)

readVal = i2c.readfrom_mem(I2CADDR, 6, 2)
print("".join("\\x%02x" % i for i in readVal))

i2c.writeto_mem(I2CADDR, 6, b'\x00')
i2c.writeto_mem(I2CADDR, 7, b'\x00')

readVal = i2c.readfrom_mem(I2CADDR, 6, 2)
print("".join("\\x%02x" % i for i in readVal))

while True:
    i2c.writeto_mem(I2CADDR, 2, b'\x01')
    i2c.writeto_mem(I2CADDR, 2, b'\x02')
    i2c.writeto_mem(I2CADDR, 2, b'\x04')
    i2c.writeto_mem(I2CADDR, 2, b'\x08')
    i2c.writeto_mem(I2CADDR, 2, b'\x10')
    i2c.writeto_mem(I2CADDR, 2, b'\x20')
    i2c.writeto_mem(I2CADDR, 2, b'\x40')
    i2c.writeto_mem(I2CADDR, 2, b'\x80')
    i2c.writeto_mem(I2CADDR, 2, b'\x00')
    
    i2c.writeto_mem(I2CADDR, 3, b'\x01')
    i2c.writeto_mem(I2CADDR, 3, b'\x02')
    i2c.writeto_mem(I2CADDR, 3, b'\x04')
    i2c.writeto_mem(I2CADDR, 3, b'\x08')
    i2c.writeto_mem(I2CADDR, 3, b'\x10')
    i2c.writeto_mem(I2CADDR, 3, b'\x20')
    i2c.writeto_mem(I2CADDR, 3, b'\x40')
    i2c.writeto_mem(I2CADDR, 3, b'\x80')
    i2c.writeto_mem(I2CADDR, 3, b'\x00')
    