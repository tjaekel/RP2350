import rp2
from machine import Pin

#BSTI interface with RP2350:
#===========================
#sending (write): change with falling edge = irq(block, 4): there seems to be a delay internally - trim code
#sampling (read): sample with falling edge
#we use a DIR signal for debug (or level shifters): after 1.5 cycles Turn Around - change direction on read
#GPIO pins:
#GPIO2: MCLK  - output signal
#GPIO3: MDOUT - output signal
#GPIO4: DIR   - output signal (for debug and level shifter, see where the read phase is)
#GPIO5: MDIN  - input signal: ATT: it needs a config to be an input

#clock generator - free running clock, INTs for rising (IRQ 4) and falling edge (IRQ 5)
#we have to tweak code so that out level changing happens on falling edge, too fast does not work anymore
#IRQ() seems to have an internal latency, not running with full speed! Assume to get just 1/4 of SYSCLK properly working with IRQs
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW)
def clk():
    #this results in 18.75MHz clock
    #trim this so that other SM changes bits on falling edge when sending
    #it divides freq by 8
    wrap_target()
    irq(4)			[0]	.side(1)			#1
    irq(clear, 4)		[0]	        			#2
    nop()			[1]	.side(0)			#3: needed just to create a 50% duty cycle, without it looks wrong
    irq(5)			[0]	        			#4
    irq(clear, 5)		[0]	        			#5
    nop()			[1]     .side(1)			#6: just for the duty cycle as approx. 50%
    wrap()
    
#preamble generator: at least 32bit with MCLK and MDOUT high
@rp2.asm_pio(set_init=rp2.PIO.OUT_HIGH)
def pre():
    wrap_target()
    pull()								#7: just wait for trigger (any value)
    set(x, 31)								#8: 32bit preamble
    set(pins, 1)							#8:
    label("preloop")
    irq(block, 4)							#10: wait for clock edge
    jmp(x_dec, "preloop")						#11:
    push(x)								#12: just trigger main() (any value) to keep going
    wrap()
    
#generate a 32bit write transaction: 2bit (START) 2bit (CMD) 10bit (ADDR) 2bit (TA) 16bit (DATA write)
@rp2.asm_pio(out_shiftdir=0, pull_thresh=32, out_init=rp2.PIO.OUT_LOW, set_init=rp2.PIO.OUT_LOW, sideset_init=rp2.PIO.OUT_LOW)
def dataWrite():
    wrap_target()
    pull()								#13: get 32bit to send out, START (2bit), CMD (2bit), PHY+ADDR (10bit),
                                                                        #    with TA (2bit) plus 16bit data to write
    set(x, 31)								#14: 32bit
    label("loop")
    irq(block, 4)							#15: wait for clock edge
    out(pins, 1)		.side(1)				#16: shift out now one bit, keep DIR high
    jmp(x_dec, "loop")							#17: keep going until all 32bits out
    irq(block, 4)							#18: last bit cycle
    set(pins, 1)							#19: keep MDOUT high afterwards
    wrap()
    
#generate a 16bit read transaction: 2bit (START) 2bit (CMD) 10bit (ADDR), 2bit (TA), 16bit (DATA read) - read with falling edge!
@rp2.asm_pio(out_shiftdir=0, pull_thresh=14, push_thresh=16, out_init=rp2.PIO.OUT_LOW, set_init=rp2.PIO.OUT_LOW, sideset_init=rp2.PIO.OUT_LOW)
def dataRead():
    wrap_target()
    pull()								#20: wait for CMD prefix to write
    set(x, 15)								#21: START (2bit), CMD (2bit), PHY+ADDR (8bit), TA (2bit, 1.5 used)
    label("loop")
    irq(block, 4)							#22: wait for clock egdge
    out(pins, 1)							#23: shift one bit out
    jmp(x_dec, "loop")							#24: keep going
    
    set(x, 15)								#25: now 16bit data to read - sampling with falling edge
    irq(block, 5)							#26: wait a half cycle, other edge, for TA
    set(pins, 1)		.side(0)				#27: set DIR signal to low (now we read)
    
    label("rx")
    irq(block, 4)							#28: wait for clock edge (falling, to sample)
    in_(pins, 1)							#29: get 1 read bit
    jmp(x_dec, "rx")							#30: keep going
    
    push()								#31: send to main program (the 16bit read)
    nop()				.side(1)			#32: set DIR signal high
    wrap()								# ! we are out of instuctions, all used !
    
FREQ = 10000000								#max: 18750000MHz, best is <= 10000000, faster gets more wrong

#this is needed to do, otherwise "in(pins,1)" does not work!
pin_5 = Pin(5, mode=Pin.IN, pull=Pin.PULL_UP)

SM = 4

#CLK generator: SM0
sm0 = rp2.StateMachine(SM + 0, clk, freq=FREQ * 8, sideset_base=Pin(2)) #times 8 is because of code in clk SM (8 cycles)
sm0.active(1)

#write cycle: SM1
sm1 = rp2.StateMachine(SM + 1, dataWrite, out_base=Pin(3), set_base=Pin(3), sideset_base=Pin(4))
sm1.active(1)
 
#read cycle: SM2
sm2 = rp2.StateMachine(SM + 2, dataRead, out_base=Pin(3), in_base=Pin(5), set_base=Pin(3), sideset_base=Pin(4))
sm2.active(1)

#prefix 32bit high: SM3 - we use all four SMs
sm3 = rp2.StateMachine(SM + 3, pre, set_base=Pin(3))
sm3.active(1)
        
prevR = 0					    #just to print when changed
#for testing with scope:
while True:
    #Read:
    sm3.put(0)					    #pre: any value is fine to trigger
    sm3.get()					    #wait for 32bit clock preamble cycles done
    sm2.put(0x5A440000)				    #generate 14bits of CMD, 2bit TA (1.5bits) and read 16bit as input - CMD prefix
    r = sm2.get()				    #get the read result from the READ
    if prevR != r:
        prevR = r				    #print just if changed (otherwise slows down too much for scope and IDE)
        print(hex(r))
    #Write:
    sm3.put(0)					    #pre: any value is fine to trigger
    sm3.get()					    #wait for 32bit clock preamble cycles done
    sm1.put(0x6A46C082)				    #generate a write, 2bit (START) + 2bit (CMD) + 10bit (ADDR) + 2bit (TA) + 16bit (DATA write)

#Remark:
#the 32bit word we write as CMD prefix (for READ and WRITE) has to be encoded properly:
#bits:
# 31, 30 : the START bits: clause 22: b01
# 29, 28 : the CMD bits: here b10 for WRITE, b01 for READ (might be wrong, or if clause 45 - modify!)
# 27..23 : PHY address
# 22..18 : REG address (clause 22)
# 17, 16 : Turn Around bits (2bits on write, 1.5bits on read)
# 15.. 0 : the 16bit value to write, 16bit value to read

