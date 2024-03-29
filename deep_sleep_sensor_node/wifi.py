import network
import constants


def connect_to_wifi_network():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("Connecting to network...")
        sta_if.active(True)
        sta_if.connect(constants.WIFI_SSID, constants.WIFI_PASSWORD)
        while not sta_if.isconnected():
            pass
    print("Network config:", sta_if.ifconfig())
