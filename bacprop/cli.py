import os

from bacprop.service import BacPropagator
from bacpypes.debugging import ModuleLogger
from bacpypes.consolelogging import ArgumentParser

_debug = 0
_log = ModuleLogger(globals())


def main() -> None:
    mqtt_port = os.environ.get("MQTT_PORT", 1883)
    mqtt_addr = os.environ.get("MQTT_ADDR", "127.0.0.1")

    ArgumentParser().parse_args()

    _log.info("Starting bacprop")
    BacPropagator().start()
