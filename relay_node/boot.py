import time

try:
    import usocket as socket
except:
    import socket

from machine import Pin
import network

import esp

esp.osdebug(None)

from tcp_listener import HTTPServer

import gc

gc.collect()

RELAY_OFF_PIN_STATE = 1

led = Pin(2, Pin.OUT)

ssid = "<YOUR_SSID>"
password = "<YOUR_PASSWORD>"

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)

while station.isconnected() is False:
    pass

print("Connection successful")
print(station.ifconfig())

gpio_1 = Pin(14, Pin.OUT)
gpio_2 = Pin(12, Pin.OUT)
PINS = {1: gpio_1, 2: gpio_2}


def pin_value(key, value=None):
    key = int(key)
    pin = PINS[key]
    if value is not None:
        pin.value(value)
    else:
        return pin.value()


for p in PINS.keys():
    pin_value(p, RELAY_OFF_PIN_STATE)


def on(pin) -> str:
    pin_value(pin, 1)
    return "ON"


def off(pin) -> str:
    pin_value(pin, 0)
    return "OFF"


def status(pin) -> int:
    return pin_value(pin)


def feedback():
    led.value(0)
    time.sleep(0.1)
    led.value(1)


listener = HTTPServer("0.0.0.0", 80, 5, feedback)
listener.register_route("on", on)
listener.register_route("off", off)
listener.register_route("status", status)
feedback()
listener.listen()
