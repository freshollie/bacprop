"""
BacProp service. Translates sensor data received
on the sensors MQTT channels into BACnet devices.

Each sensor id becomes a device, which is served 
to the BACnet network as if they are devices within
a VLAN
"""

import json
from typing import Dict, Union

import paho.mqtt.client as mqtt
from bacpypes.debugging import ModuleLogger, bacpypes_debugging

from bacprop.bacnet.sensor import Sensor
from bacprop.bacnet.network import VirtualSensorNetwork

_debug = 0
_log = ModuleLogger(globals())


@bacpypes_debugging
class BacPropagator(mqtt.Client):
    def __init__(self, mqtt_addr: str, mqtt_port: str):
        mqtt.Client.__init__(self)

        self._sensors: Dict[int, Sensor] = {}
        self._bacnet = VirtualSensorNetwork("0.0.0.0")
        self._mqtt_addr = mqtt_addr
        self._mqtt_port = mqtt_port

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        BacPropagator._info("Connected with result code " + str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.

        BacPropagator._info("Subscribing to sensor channel")
        self.subscribe("sensor/#")

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        if _debug:
            BacPropagator._debug(f"Recieved: {msg.payload}")

        # Decode the JSON data
        try:
            data = json.loads(msg.payload)
        except json.JSONDecodeError as e:
            BacPropagator._error(f"Could not decode sensor data: {e}")
            return

        # And then pass the data onto the handler
        try:
            print(data)
            self._handle_sensor_data(data)
        except Exception as e:
            BacPropagator._error(f"Could not handle sensor data: {e}")

    def _handle_sensor_data(self, data: Dict[str, Union[int, float]]):
        """
        Process the received device data. If the data is from a new
        device, create a new sensor on the bacnet network.

        Set the sensor's data to the received data
        """
        sensor_id = int(data["sensorId"])

        if sensor_id not in self._sensors:
            sensor = Sensor(100 + sensor_id)
            self._sensors[sensor_id] = sensor
            self._bacnet.add_sensor(sensor)
        else:
            sensor = self._sensors[sensor_id]

        sensor.set_values(
            float(data["temp"]), float(data["hum"]), float(data["co2"]), int(data["ts"])
        )

    def run(self):
        BacPropagator._info(f"Starting MQTT connection to {self._mqtt_addr}")
        self.connect(self._mqtt_addr, self._mqtt_port, 60)

        # Start the mqtt client in another thread, so
        # that we can start the BACPypes application in the main thread
        self.loop_start()

        BacPropagator._info("Starting virtual BACnet sensor network")
        try:
            self._bacnet.run()
        except KeyboardInterrupt:
            pass

        # The main thread has been shutdown by a keyboard interrupt, so
        # stop the mqtt thread.

        BacPropagator._info("Stopping")
        self.loop_stop()

