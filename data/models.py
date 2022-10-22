import json
import os
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Union, Optional

import requests
from pydantic import BaseModel

from application.constants import DEFAULT_MINIMUM_TARGET
from application.logs import log_exceptions

PERSISTENCE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "persistence.json"
file_lock = False

"""
// EXAMPLE:
{
  "systems": [
    {
      "system_id": "downstairs",
      "relay": {
        "url_on":  "http://192.168.1.115/off?pin=1",
        "url_off":  "http://192.168.1.115/on?pin=1",
        "url_status":  "http://192.168.1.115/status?pin=1"
      },
      "sensor": {
        "url": "http://192.168.1.116"
      },
      "program": true,
      "periods": "[[6.0, 22.0, 22.0]]"
    },
    {
      "system_id": "upstairs",
      "relay": {
        "url_on":  "http://192.168.1.115/off?pin=2",
        "url_off":  "http://192.168.1.115/on?pin=2",
        "url_status":  "http://192.168.1.115/status?pin=2"
      },
      "sensor": {
        "url": "http://192.168.1.109"
      },
      "program": true,
      "periods": "[[3.0, 10.0, 22.0], [18.0, 23.0, 22.0]]"
    }
  ]
}
"""


def use_file_lock(f):
    def w(*args, **kwargs):
        global file_lock
        while file_lock:
            pass
        file_lock = True
        result = f(*args, **kwargs)
        file_lock = False
        return result

    return w


class SensorNode(BaseModel):
    url: str
    adjustment: Optional[float] = None

    @log_exceptions
    def temperature(self):
        res = requests.get(self.url, timeout=5).json()
        temp = float(res["temperature"])
        if self.adjustment is not None:
            temp += self.adjustment
        return float(f"{temp:.1f}")


class RelayNode(BaseModel):
    url_on: str
    url_off: str
    url_status: str

    @log_exceptions
    def switch(self, direction="on"):
        if direction == "on":
            requests.get(f"{self.url_on}", timeout=5)
        elif direction == "off":
            requests.get(f"{self.url_off}", timeout=5)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    @log_exceptions
    def status(self):
        try:
            resp = requests.get(f"{self.url_status}", timeout=5)
            return not int(resp.content)
        except ValueError:
            return None


class Period(NamedTuple):
    start: float
    end: float
    target: float


class System(BaseModel):
    sensor: SensorNode
    relay: RelayNode
    system_id: Union[int, str]
    program: bool = False
    periods: list[Period] = []

    @property
    def temperature(self):
        return self.sensor.temperature()

    @property
    def relay_on(self):
        return self.relay.status()

    @property
    def current_target(self):
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute_decimal = current_time.minute / 60
        check_time = current_hour + current_minute_decimal
        try:
            period = next(
                filter(
                    lambda x: x.start <= check_time < x.end,
                    self.periods,
                )
            )
        except StopIteration:
            return DEFAULT_MINIMUM_TARGET
        return period.target

    @log_exceptions
    def switch_on(self):
        self.relay.switch("on")

    @log_exceptions
    def switch_off(self):
        self.relay.switch("off")

    @log_exceptions
    def add_period(self, period: Period):
      uodated = False
        for p in self.periods:
            if p.start == period.start and p.end == period.end:
                p.target = period.target
                updated = True
                break
            if p.start >= period.end:
                continue
            if p.end <= period.start:
                continue
            raise Exception("Periods overlap")
        if not updated:
          self.periods.append(period)
        self.periods.sort(key=lambda x: x.start)
        self.serialize()

    @log_exceptions
    @use_file_lock
    def serialize(self):
        sensor_dict = self.sensor.dict(exclude_unset=True)
        relay_dict = self.relay.dict(exclude_unset=True)
        serialised_data = {
            "relay": relay_dict,
            "sensor": sensor_dict,
            "system_id": self.system_id,
            "program": self.program,
            "periods": json.dumps(self.periods),
        }

        if not os.path.exists(PERSISTENCE_FILE):
            with open(PERSISTENCE_FILE, "w") as f:
                json.dump({"systems": []}, f)

        with open(PERSISTENCE_FILE, "r") as f:
            current = json.load(f)

        updated_systems = list(
            filter(lambda x: x["system_id"] != self.system_id, current["systems"])
        )

        updated_systems.append(serialised_data)

        current["systems"] = updated_systems

        with open(PERSISTENCE_FILE, "w") as f:
            json.dump(current, f, indent=2)

    @classmethod
    @log_exceptions
    @use_file_lock
    def deserialize_systems(cls) -> list["System"]:
        with open(PERSISTENCE_FILE, "r") as f:
            current = json.load(f)
        systems_in_memory = []
        for system in current["systems"]:
            relay = RelayNode(**system["relay"])
            sensor = SensorNode(**system["sensor"])
            system = System(
                relay=relay,
                sensor=sensor,
                system_id=system["system_id"],
                program=system["program"],
                periods=[
                    Period(p[0], p[1], p[2]) for p in json.loads(system["periods"])
                ],
            )
            systems_in_memory.append(system)
        return systems_in_memory

    @classmethod
    @log_exceptions
    def get_by_id(cls, system_id):
        systems = cls.deserialize_systems()
        for system in systems:
            if system.system_id == system_id:
                return system
