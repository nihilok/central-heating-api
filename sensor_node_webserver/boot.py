import machine
import gc
import json
import network
from lib import constants
from lib.bme import BME280

try:
    import usocket as socket
except ImportError:
    import socket


gc.collect()


sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    print("\nConnecting to network...")
    sta_if.active(True)
    sta_if.connect(constants.WIFI_SSID, constants.WIFI_PASSWORD)
    while not sta_if.isconnected():
        pass
print("\nNetwork config:", sta_if.ifconfig())


i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4), freq=10000)
bme = BME280(i2c=i2c)


rtc = machine.RTC()
rtc.datetime((1971, 1, 1, 0, 0, 0, 0, 0))
initial_time = rtc.datetime()


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
        current_time = rtc.datetime()
        if current_time[3] > initial_time[3] + 1:
            # reset every 2 hours
            print("Resetting after time interval (2 hours)")
            machine.reset()
        cl, addr = s.accept()
        print("Client connected from", addr)
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
except Exception:
    machine.reset()
