import asyncio
import logging
import time
import traceback
from threading import Thread
from typing import Dict

from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from hbmqtt.broker import Broker

from bacprop.bacnet.network import VirtualSensorNetwork
from bacprop.defs import Logable
from bacprop.mqtt import SensorStream

_debug = 0
_log = ModuleLogger(globals())


@bacpypes_debugging
class BacPropagator(Logable):
    SENSOR_ID_KEY = "sensorId"
    SENSOR_OUTDATED_TIME = 60 * 10  # 10 Minutes

    def __init__(self) -> None:
        BacPropagator._info(f"Intialising SensorStream and Bacnet")
        self._stream = SensorStream()
        self._sensor_net = VirtualSensorNetwork("0.0.0.0")
        self._running = False

    def _handle_sensor_data(self, data: Dict[str, float]) -> None:
        if BacPropagator.SENSOR_ID_KEY not in data:
            BacPropagator._warning(f"sensorId missing from sensor data: {data}")
            return

        try:
            sensor_id = int(data[BacPropagator.SENSOR_ID_KEY])
        except ValueError:
            BacPropagator._warning(
                f"sensorId {data[BacPropagator.SENSOR_ID_KEY]} could not be decoded"
            )
            return

        del data[BacPropagator.SENSOR_ID_KEY]

        values: Dict[str, float] = {}

        # Only allow through data which are actually floats
        for key in data:
            if type(data[key]) not in (float, int):
                BacPropagator._warning(
                    f"Recieved non-number value ({key}: '{data[key]}') from sensor id: {sensor_id}"
                )
            else:
                values[key] = data[key]

        sensor = self._sensor_net.get_sensor(sensor_id)

        if not sensor:
            sensor = self._sensor_net.create_sensor(sensor_id)

        sensor.set_values(values)

        if sensor.has_fault():
            if _debug:
                BacPropagator._debug(
                    f"Sensor {sensor_id} now has new data, so marking as OK"
                )
            sensor.mark_ok()

    async def _fault_check_loop(self) -> None:
        BacPropagator._info("Starting fault check loop")
        while self._running:
            for sensor_id, sensor in self._sensor_net.get_sensors().items():
                if (
                    not sensor.has_fault()
                    and abs(time.time() - sensor.get_update_time())
                    > BacPropagator.SENSOR_OUTDATED_TIME
                ):
                    if _debug:
                        BacPropagator._debug(
                            f"Sensor {sensor_id} data is outdated, notifying fault"
                        )
                    sensor.mark_fault()

            await asyncio.sleep(1)

    async def _main_loop(self) -> None:
        BacPropagator._info("Starting stream receive loop")
        await self._stream.start()

        async for data in self._stream.read():
            if _debug:
                BacPropagator._debug(f"Received: {data}")

            self._handle_sensor_data(data)

    def _start_bacnet_thread(self) -> Thread:
        BacPropagator._info("Starting bacnet sensor network")

        bacnet_thread = Thread(target=self._sensor_net.run)
        bacnet_thread.daemon = True
        bacnet_thread.start()

        return bacnet_thread

    def start(self) -> None:
        self._running = True

        bacnet_thread = self._start_bacnet_thread()

        asyncio.ensure_future(self._fault_check_loop())

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._main_loop())
        except KeyboardInterrupt:
            pass
        except:
            traceback.print_exc()

        self._running = False

        BacPropagator._info("Stopping stream loop")
        loop.run_until_complete(self._stream.stop())

        BacPropagator._info("Closing bacnet sensor network")
        self._sensor_net.stop()
        bacnet_thread.join()
