import time

import machine
import urequests
import bme280
import constants
import wifi
import gc

DEFAULT_SLEEP_SECS = 60


def init_sensor() -> bme280.BME280:
    i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4), freq=10000)
    bme = bme280.BME280(i2c=i2c)
    return bme


def deepsleep(sleep_secs) -> None:
    print(f"Entering deep sleep for {sleep_secs} seconds")
    machine.deepsleep(sleep_secs * 1000)


def get_data() -> str:
    bme = init_sensor()
    print(bme.temperature)
    if not bme.temperature:
        return {}
    return {
        "temperature": bme.temperature,
        "pressure": bme.pressure,
        "humidity": bme.humidity,
    }


def transmit_data(data: str, host: str) -> None:
    url = f"{host}"
    urequests.post(url, data=data)


def main():
    wifi.connect_to_wifi_network()
    data = get_data()
    transmit_data(data, constants.RECEIVER_ENDPOINT)
    deepsleep(DEFAULT_SLEEP_SECS)


gc.collect()


if __name__ == "__main__":
    time.sleep(1)
    main()
