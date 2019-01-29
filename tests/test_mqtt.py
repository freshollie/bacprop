import asyncio

import pytest
from hbmqtt.broker import Broker
from hbmqtt.client import MQTTClient, QOS_2
from pytest import fixture
from pytest_mock import MockFixture

from typing import AsyncIterator

from bacprop import mqtt
from bacprop.mqtt import SensorStream

mqtt._debug = 1


class TestSensorStream:
    def test_init(self) -> None:
        sensor_stream = SensorStream()

        assert isinstance(sensor_stream, MQTTClient)
        assert type(sensor_stream._broker) == Broker
        assert not sensor_stream._running

    @pytest.mark.asyncio
    async def test_receive_data(self) -> None:
        test_stream = SensorStream()
        mqtt_sensor = MQTTClient()

        await test_stream.start()
        await mqtt_sensor.connect("mqtt://localhost")

        received = []

        async def receive() -> None:
            try:
                async for message in test_stream.read():
                    received.append(message)
                    break
            except:
                pass

        asyncio.ensure_future(receive())
        await mqtt_sensor.publish("sensor/1", b'{"test": 6.0, "sensorId": 1}', QOS_2)
        await asyncio.sleep(0.1)

        assert received[0] == {"test": 6.0, "sensorId": 1}

        await mqtt_sensor.disconnect()
        await test_stream.stop()

    @pytest.mark.asyncio
    async def test_receive_bad_data(self) -> None:
        test_stream = SensorStream()
        mqtt_sensor = MQTTClient()

        await test_stream.start()
        await mqtt_sensor.connect("mqtt://localhost")

        received = []

        async def receive() -> None:
            try:
                async for message in test_stream.read():
                    received.append(message)
                    break
            except:
                pass

        asyncio.ensure_future(receive())
        await mqtt_sensor.publish("sensor/1", b"lol", QOS_2)
        await asyncio.sleep(0.1)

        assert not received

        await mqtt_sensor.disconnect()
        await test_stream.stop()

    @pytest.mark.asyncio
    async def test_stop_not_running(self) -> None:
        stream = SensorStream()
        await stream.stop()
