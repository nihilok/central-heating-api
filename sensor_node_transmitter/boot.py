import machine
import time
import urequests
from lib import bme
from lib import constants
from lib import wifi
import gc

__TESTING__ = True  # set this to false when ready to deploy


def init_sensor() -> bme.BME280:
    i2c = machine.SoftI2C(scl=machine.Pin(constants.SCL_PIN), sda=machine.Pin(constants.SDA_PIN), freq=10000)
    sensor = bme.BME280(i2c=i2c)
    return sensor


def deepsleep(sleep_secs) -> None:
    print(f"Entering deep sleep for {sleep_secs} seconds")
    machine.deepsleep(sleep_secs * 1000)


def get_data() -> dict:
    bme = init_sensor()
    print(bme.temperature)
    if not bme.temperature:
        return {}
    return {
        "temperature": bme.temperature,
        "pressure": bme.pressure,
        "humidity": bme.humidity,
    }


def transmit_data(data: dict, url: str) -> urequests.Response:
    return urequests.post(url, json=data)


def main():
    wifi.connect_to_wifi_network()
    data = get_data()
    transmit_data(data, constants.RECEIVER_ENDPOINT)
    deepsleep(constants.DEEP_SLEEP_SECS)


gc.collect()


if __name__ == "__main__":
    if __TESTING__:
        wifi.connect_to_wifi_network()
        while True:
            print("Reading data:")
            print(get_data())
            print("Making request:")
            r = transmit_data(get_data(), constants.RECEIVER_ENDPOINT)
            print(r.text)
            time.sleep(5)
    else:
        main()
