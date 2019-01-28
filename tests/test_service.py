import asyncio
from typing import Any, AsyncIterable, Dict

import pytest
from pytest import fixture
from pytest_mock import MockFixture

from bacprop import service
from bacprop.bacnet.network import VirtualSensorNetwork
from bacprop.mqtt import SensorStream
from bacprop.service import BacPropagator

from bacprop.bacnet.sensor import Sensor

service._debug = 1


def async_return(result: Any) -> asyncio.Future:
    f: asyncio.Future = asyncio.Future()
    f.set_result(result)
    return f


@fixture
def bacprop_service(mocker: MockFixture) -> BacPropagator:
    mocker.patch("bacprop.service.SensorStream")
    mocker.patch("bacprop.service.VirtualSensorNetwork")

    service = BacPropagator()

    service._sensor_net = mocker.create_autospec(VirtualSensorNetwork)
    service._stream = mocker.create_autospec(SensorStream)

    return service


class TestBacPropagator:
    def test_init(self, mocker: MockFixture) -> None:
        mock_stream = mocker.patch("bacprop.service.SensorStream")
        mock_network = mocker.patch("bacprop.service.VirtualSensorNetwork")

        BacPropagator()

        mock_stream.assert_called_once()
        mock_network.assert_called_with("0.0.0.0")

    def test_start(self, mocker: MockFixture, bacprop_service: BacPropagator) -> None:
        mocker.patch.object(bacprop_service, "_main_loop", autospec=True)
        mocker.patch.object(bacprop_service, "_fault_check_loop", autospec=True)
        mocker.patch.object(bacprop_service, "_start_bacnet_thread", autospec=True)

        bacprop_service._main_loop.return_value = async_return(None)  # type: ignore
        bacprop_service._fault_check_loop.return_value = async_return(  # type: ignore
            None
        )
        bacprop_service._stream.stop.return_value = async_return(None)  # type: ignore

        bacprop_service.start()

        # Make sure all the correct things are called on startup
        bacprop_service._main_loop.assert_called_once()  # type: ignore
        bacprop_service._fault_check_loop.assert_called_once()  # type: ignore
        bacprop_service._start_bacnet_thread.assert_called_once()  # type: ignore

    def test_start_bacnet(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        thread = bacprop_service._start_bacnet_thread()
        assert thread.daemon
        thread.join()

        bacprop_service._sensor_net.run.assert_called_once()  # type: ignore

    @pytest.mark.asyncio
    async def test_receive_data(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        mocker.patch.object(bacprop_service, "_handle_sensor_data", autospec=True)

        async def mock_read() -> AsyncIterable[Dict[str, float]]:
            yield {"something": 0.1, "sensorId": 1}

        bacprop_service._stream.start.return_value = async_return(None)  # type: ignore
        bacprop_service._stream.read.return_value = mock_read()  # type: ignore

        await bacprop_service._main_loop()
        bacprop_service._handle_sensor_data.assert_called_with(  # type: ignore
            {"something": 0.1, "sensorId": 1}
        )

    def test_handle_data_new_sensor(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"somethingElse": 0.2, "sensorId": 1}
        sensor = mocker.create_autospec(Sensor)

        sensor.has_fault.return_value = False  # type: ignore

        bacprop_service._sensor_net.create_sensor.return_value = sensor  # type: ignore
        bacprop_service._sensor_net.get_sensor.return_value = None  # type: ignore

        bacprop_service._handle_sensor_data(data)

        bacprop_service._sensor_net.create_sensor.assert_called_with(1)  # type: ignore
        sensor.has_fault.assert_called_once()
        sensor.set_values.assert_called_with({"somethingElse": 0.2})

