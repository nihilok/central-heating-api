import time

import uos, machine, gc

gc.collect()

import network

sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    print("\nconnecting to network...")
    sta_if.active(True)
    sta_if.connect("<WIFI SSID>", "<WIFI PASSWORD>")
    while not sta_if.isconnected():
        pass
print("\nnetwork config:", sta_if.ifconfig())

import json
from bme280 import BME280

i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4), freq=10000)
bme = BME280(i2c=i2c)

try:
    import usocket as socket
except:
    import socket


def main():
    s = socket.socket()

    # Binding to all interfaces - server will be accessible to other hosts!
    ai = socket.getaddrinfo("0.0.0.0", 80)
    print("Bind address info:", ai)
    addr = ai[0][-1]

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    print("Listening, connect your browser to http://" + sta_if.ifconfig()[0])

    while True:
        cl, addr = s.accept()
        print("client connected from", addr)
        cl_file = cl.makefile("rwb", 0)
        while True:
            line = cl_file.readline()
            if not line or line == b"\r\n":
                break
        response = json.dumps(
            {
                "temperature": bme.temperature,
                "pressure": bme.pressure,
                "humidity": bme.humidity,
            }
        )
        cl.send("HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n")
        cl.send(response)
        cl.close()


try:
    main()
except KeyboardInterrupt:
    raise KeyboardInterrupt
except Exception as e:
    print(e.__class__.__name__)
    print(e)
    print("RESETTING MICROCONTROLLER")
    time.sleep(2)
    machine.reset()
