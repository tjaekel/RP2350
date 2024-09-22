import time
import rp2
from machine import Pin
import time

#clock generator - free running clock, INTs for rising (read) and falling edge (write)
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW)
def clk():
    #this results in 25MHz clock
    #trim this so that other SM changes bits on falling edge when sending
    #it divides freq by 6
    wrap_target()
    irq(4)			[1]	.side(1)	#1
    irq(clear, 4)		[0]			#2
    irq(5)			[1]	.side(0)	#3
    irq(clear, 5)		[0]			#4
    wrap()
    
@rp2.asm_pio()
def pre():
    wrap_target()
    pull()						#5 : just wait for trigger (any value)
    set(x, 31)						#6
    label("preloop")
    irq(block, 4)					#7
    irq(block, 4)					#8 : why do we need 2x?, otherwise too short!
    jmp(x_dec, "preloop")				#9
    push(x)						#10 : just trigger main() (any value)
    wrap()
    
#generate a 32bit write transaction: 2bit (START) 2bit (CMD) 10bit (ADDR) 2bit (TA) 16bit (DATA write)
@rp2.asm_pio(out_shiftdir=0, pull_thresh=32, out_init=rp2.PIO.OUT_LOW, set_init=rp2.PIO.OUT_LOW, sideset_init=rp2.PIO.OUT_LOW)
def dataWrite():
    wrap_target()
    pull()						#11
    
    set(x, 31)						#12
    label("loop")
    irq(block, 4)					#13
    out(pins, 1)		.side(1)		#14
    jmp(x_dec, "loop")					#15
    
    irq(block, 4)					#16
    set(pins, 1)		.side(1)		#17
    wrap()
    
#generate a 16bit read transaction: 2bit (START) 2bit (CMD) 10bit (ADDR), 2bit (TA), 16bit (DATA read) - read with rising edge!
@rp2.asm_pio(out_shiftdir=0, pull_thresh=14, push_thresh=16, out_init=rp2.PIO.OUT_LOW, set_init=rp2.PIO.OUT_LOW, sideset_init=rp2.PIO.OUT_LOW)
def dataRead():
    wrap_target()
    pull()						#18
    
    set(x, 13)						#19
    label("loop")
    irq(block, 4)					#20
    out(pins, 1)					#21
    jmp(x_dec, "loop")					#22
    
    irq(block, 4)					#23
    
    set(pindirs, 0)		.side(0)		#24
    irq(block, 4)					#25
    set(x, 15)						#26
    irq(block, 5)					#27
    
    label("rx")
    irq(block, 5)					#28
    in_(pins, 1)					#29
    jmp(x_dec, "rx")					#30
    
    push()						#31
    set(pindirs, 1)		.side(1)		#32 - full 32 instructions on PIO0
    wrap()
    
FREQ = 20000000

#CLK generator SM0
sm0 = rp2.StateMachine(0, clk, freq=FREQ * 6, sideset_base=Pin(2))
sm0.active(1)

#read cycle SM2
sm2 = rp2.StateMachine(2, dataRead, out_base=Pin(3), in_base=Pin(3), set_base=Pin(3), sideset_base=Pin(4))
sm2.active(1)

#write cycle SM1
sm1 = rp2.StateMachine(1, dataWrite, out_base=Pin(3), in_base=Pin(3), set_base=Pin(3), sideset_base=Pin(4))
sm1.active(1)

sm3 = rp2.StateMachine(3, pre)
sm3.active(1)
        
prevR = 0
while True:
    #Read:
    sm3.put(0)				#pre: any value is fine
    sm3.get()				#wait for 32bit clock pre cycles done
    sm2.put(0x1A440000)		#generate 13bits of frame start, 2bit TA and read 16bit
    r = sm2.get()		#get the read result
    if prevR != r:
        prevR = r		#print just if changed (otherwise slows down too much)
        print(hex(r))
    #Write
    sm3.put(0)				#pre: any value is fine
    sm3.get()				#wait for 32bit clock pre cycles done
    sm1.put(0x01A44C084)	#generate a write, 2bit (START) + 2bit (CMD) + 10bit (ADDR) + 2bit (TA) + 16bit (DATA write)

