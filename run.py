import os

from bacprop import service
from bacpypes.consolelogging import ArgumentParser

mqtt_port = os.environ.get("MQTT_PORT", 1883)
mqtt_addr = os.environ("MQTT_ADDR", "127.0.0.1")

service.BacPropagator(mqtt_addr, mqtt_port).run()
