import asyncio
from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1, QOS_2

class BacPropergator:
    def __init__(self):
        self._loop = asyncio.get_event_loop()
    
    async def _run(self):
        C = MQTTClient()
        await C.connect('mqtt://localhost')
        # Subscribe to '$SYS/broker/uptime' with QOS=1
        # Subscribe to '$SYS/broker/load/#' with QOS=2
        await C.subscribe([
                ('#', QOS_1),
            ])
        try:
            while True:
                message = await C.deliver_message()
                packet = message.publish_packet
                print("%s => %s" % (packet.variable_header.topic_name, str(packet.payload.data)))
            await C.disconnect()
        except ClientException as ce:
            print("Client exception: %s" % ce)
    
    def run(self):
        self._loop.run_until_complete(self._run())

