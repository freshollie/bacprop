import json
from typing import AsyncIterable, Dict, NoReturn, Union

from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from hbmqtt.broker import Broker
from hbmqtt.client import QOS_2, MQTTClient
import asyncio

_debug = 0
_log = ModuleLogger(globals())


@bacpypes_debugging
class SensorStream(MQTTClient):
    def __init__(self) -> None:
        # pylint: disable=no-member
        SensorStream._info("Initialising broker on 0.0.0.0:1883")
        self._broker = Broker(
            {
                "listeners": {"default": {"type": "tcp", "bind": "0.0.0.0:1883"}},
                "topic-check": {"enabled": False},
            },
            asyncio.get_event_loop(),
        )
        self._running = False
        MQTTClient.__init__(self)

    async def start(self) -> Union[None, NoReturn]:
        if _debug:
            # pylint: disable=no-member
            SensorStream._debug("Starting broker")
        await self._broker.start()

        if _debug:
            # pylint: disable=no-member
            SensorStream._debug("Connecting to broker")
        await self.connect("mqtt://localhost")

        if _debug:
            # pylint: disable=no-member
            SensorStream._debug("Subscribing to sensor stream")
        await self.subscribe([("sensor/#", QOS_2)])

        self._running = True
        return None

    async def stop(self) -> Union[None, NoReturn]:
        if _debug:
            # pylint: disable=no-member
            SensorStream._debug("Stopping")

        if not self._running:
            return None

        if _debug:
            # pylint: disable=no-member
            SensorStream._debug("Shutting down broker")

        await self._broker.shutdown()

        self._running = False

        return None

    async def read(self) -> AsyncIterable[Dict[str, float]]:
        while self._running:
            msg = await self.deliver_message()
            packet = msg.publish_packet

            # Decode the JSON data
            try:
                data = json.loads(packet.payload.data)
                yield data
            except json.JSONDecodeError as e:
                # pylint: disable=no-member
                SensorStream._error(f"Could not decode sensor data: {e}")
