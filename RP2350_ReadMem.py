#memory read via MircoPython

import rp2

@micropython.asm_thumb
def ReadMem(r0):
    ldr(r0, [r0, 0])
   
def tohex(val, nbits):
  return hex((val + (1 << nbits)) % (1 << nbits))

print("bootrom:")
v = ReadMem(0x0)	#SP top
print(tohex(v, 32))
v = ReadMem(0x4)	#ResetHandler
print(tohex(v, 32))
v = ReadMem(0x8)	#NMI - enabled always
print(tohex(v, 32))
v = ReadMem(0xc)	#HardFault - enabled always
print(tohex(v, 32))
v = ReadMem(0x10)	#memory fault!
print(tohex(v, 32))
v = ReadMem(0x14)	#bus fault!
print(tohex(v, 32))

v = ReadMem(0x18)
print(tohex(v, 32))
v = ReadMem(0x1C)
print(tohex(v, 32))
v = ReadMem(0x20)
print(tohex(v, 32))
v = ReadMem(0x24)
print(tohex(v, 32))
v = ReadMem(0x28)
print(tohex(v, 32))
v = ReadMem(0x2C)
print(tohex(v, 32))
v = ReadMem(0x30)
print(tohex(v, 32))
v = ReadMem(0x34)
print(tohex(v, 32))
v = ReadMem(0x38)
print(tohex(v, 32))
v = ReadMem(0x3C)
print(tohex(v, 32))
v = ReadMem(0x40)
print(tohex(v, 32))
v = ReadMem(0x44)
print(tohex(v, 32))
v = ReadMem(0x48)
print(tohex(v, 32))

print("chip ID:")
v = ReadMem(0x40000000)
print(tohex(v, 32))
v = ReadMem(0x40000004)
print(tohex(v, 32))
v = ReadMem(0x40000008)
print(tohex(v, 32))
v = ReadMem(0x40000014)
print(tohex(v, 32))

v = ReadMem(0x2f8)
print(tohex(v, 32))
