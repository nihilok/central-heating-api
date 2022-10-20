# Open Central Heating API

### Pre-requisites
- Python 3.9+

### Installation (main API)
- create a new Python virtual environment using `requirements.txt` e.g.
```sh
python3 -m venv venv
pip install -r requirements.txt
```
- create a new systemd unit file (change the appropriate paths making sure the ExecStart command is using the python executable from inside your virtual environment)
```sh
echo "[Unit]
Description=Open Central Heating API

[Service]
User=<your user>
WorkingDirectory=home/<your user>/project/directory
ExecStart=/home/<your user>/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
" >> central-heating.service && sudo mv central-heating.service /etc/systemd/system/
```
- reload the systemctl daemon & enable/start the new service
```sh
sudo systemctl daemon-reload
sudo systemctl enable central-heating
sudo systemctl start central-heating
```

### Installation (micropython devices)

There are two different micropython controllers in the current setup. A "relay" controller and a "sensor" controller. The code for these is stored in `./relay_node` and `./sensor_node` respectively and must be flashed to a suitable micropython wifi device. I've used a total of 3 NodeMCU ESP8266 controllers: 2 sensor nodes and 1 relay node.

After adjusting the network settings (SSID & WPA key), all of the python modules in each directory must be flashed to the relevant microcontroller. I recommend using the Thonny IDE to connect to your micropython devices.

### Configuration

In `data.models` you can see a comment detailing an example configuration. Essentially each heating system needs an URL to read the temperature, and URLS to switch on/off and get the status of the relay respectively.

`data/persistence.json`
```json
{
  "systems": [
    {
      "relay": {
        "url_on": "http://192.168.1.115/off?pin=2",
        "url_off": "http://192.168.1.115/on?pin=2",
        "url_status": "http://192.168.1.115/status?pin=2"
      },
      "sensor": {
        "url": "http://192.168.1.116"
      },
      "system_id": "upstairs",
      "program": true,
      "periods": "[[3.0, 10.0, 22.0], [18.0, 23.0, 22.0]]"
    },
    {
      "relay": {
        "url_on": "http://192.168.1.115/off?pin=1",
        "url_off": "http://192.168.1.115/on?pin=1",
        "url_status": "http://192.168.1.115/status?pin=1"
      },
      "sensor": {
        "url": "http://192.168.1.109"
      },
      "system_id": "downstairs",
      "program": true,
      "periods": "[[6.0, 22.0, 22.0]]"
    }
  ]
}
```
Here we have two heating systems (upstairs & downstairs) that share the same relay node, but have independent sensor nodes. The periods value can be omitted but consists of an array of arrays, where each inner array represents an individual period, where the first value is the start time, the second is the end time, and the last is the target temperature.
