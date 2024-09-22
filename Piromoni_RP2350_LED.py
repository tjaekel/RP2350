import rp2
from machine import Pin
import time

pin = Pin(25, mode=Pin.OUT)

while True:
    pin.value(0)
    time.sleep(0.1)
    pin.value(1)
    time.sleep(0.1)
    print("Hi!")
