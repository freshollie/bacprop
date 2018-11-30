import os

from bacprop import service
from bacpypes.debugging import ModuleLogger
from bacpypes.consolelogging import ArgumentParser

_debug = 0
_log = ModuleLogger(globals())

mqtt_port = os.environ.get("MQTT_PORT", 1883)
mqtt_addr = os.environ.get("MQTT_ADDR", "127.0.0.1")

ArgumentParser().parse_args()

_log.info("Starting bacprop")
service.BacPropagator(mqtt_addr, mqtt_port).run()
