import machine
import time
import urequests
import bme280
import constants
import wifi
import gc

__TESTING__ = True  # set this to false when ready to deploy
DEFAULT_SLEEP_SECS = 60


def init_sensor() -> bme280.BME280:
    i2c = machine.SoftI2C(scl=machine.Pin(39), sda=machine.Pin(42), freq=10000)
    bme = bme280.BME280(i2c=i2c)
    return bme


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
    deepsleep(DEFAULT_SLEEP_SECS)


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
