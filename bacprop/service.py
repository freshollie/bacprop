import asyncio
import json
from typing import Dict
from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1, QOS_2


class BacPropergator:

    TOPIC_START_FORMAT = "sensor-"

    def __init__(self):
        self._loop = asyncio.get_event_loop()

    async def _handle_sensor_data(self, data: Dict[str, str]):
        pass

    async def _run(self):
        C = MQTTClient()
        await C.connect("mqtt://localhost")

        await C.subscribe([(f"{BacPropergator.TOPIC_START_FORMAT}#", QOS_1)])

        print("MQTT listening")
        try:
            while True:
                # Wait for a message to come from any of the topics
                message = await C.deliver_message()
                packet = message.publish_packet

                # We expect the topic to start with "sensor"
                try:
                    data = str(packet.payload.data)
                    data = json.loads(data)
                except json.JSONDecodeError:
                    # Bad data
                    continue

                await self._handle_sensor_data(data)
                print(
                    "%s => %s"
                    % (packet.variable_header.topic_name, str(packet.payload.data))
                )
            await C.disconnect()
        except ClientException as ce:
            print("Client exception: %s" % ce)

    def run(self):
        self._loop.run_until_complete(self._run())
