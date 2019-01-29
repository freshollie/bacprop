import asyncio
import time
from threading import Thread
from typing import Any, AsyncIterable, Dict, NoReturn
from unittest.mock import call

import pytest
from pytest import fixture
from pytest_mock import MockFixture

from bacprop import service
from bacprop.bacnet.network import VirtualSensorNetwork
from bacprop.bacnet.sensor import Sensor
from bacprop.mqtt import SensorStream
from bacprop.service import BacPropagator

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

        class MainLoopCheck:
            ran = False

        async def run_main_loop() -> None:
            MainLoopCheck.ran = True  # type: ignore

        bacprop_service._main_loop.return_value = run_main_loop()  # type: ignore
        bacprop_service._fault_check_loop.return_value = async_return(  # type: ignore
            None
        )
        bacprop_service._stream.stop.return_value = async_return(None)  # type: ignore

        bacprop_service.start()

        # Make sure all the correct things are called on startup
        assert MainLoopCheck.ran
        bacprop_service._fault_check_loop.assert_called_once()  # type: ignore
        bacprop_service._start_bacnet_thread.assert_called_once()  # type: ignore

    def test_main_interrupt(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        mocker.patch.object(bacprop_service, "_main_loop", autospec=True)
        mocker.patch.object(bacprop_service, "_fault_check_loop", autospec=True)
        mocker.patch.object(bacprop_service, "_start_bacnet_thread", autospec=True)

        backnet_thread = mocker.create_autospec(Thread)

        bacprop_service._start_bacnet_thread.return_value = (  # type: ignore
            backnet_thread
        )

        def throw() -> NoReturn:
            raise KeyboardInterrupt()

        bacprop_service._main_loop = lambda *args: throw()  # type: ignore
        bacprop_service._fault_check_loop.return_value = async_return(  # type: ignore
            None
        )
        bacprop_service._stream.stop.return_value = async_return(None)  # type: ignore

        bacprop_service.start()
        bacprop_service._sensor_net.stop.assert_called_once()  # type: ignore
        backnet_thread.join.assert_called_once()

    def test_main_error(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        mocker.patch.object(bacprop_service, "_main_loop", autospec=True)
        mocker.patch.object(bacprop_service, "_fault_check_loop", autospec=True)
        mocker.patch.object(bacprop_service, "_start_bacnet_thread", autospec=True)

        backnet_thread = mocker.create_autospec(Thread)

        bacprop_service._start_bacnet_thread.return_value = (  # type: ignore
            backnet_thread
        )

        # Throw any error here
        def throw() -> NoReturn:
            raise ValueError()

        bacprop_service._main_loop = lambda *args: throw()  # type: ignore
        bacprop_service._fault_check_loop.return_value = async_return(  # type: ignore
            None
        )
        bacprop_service._stream.stop.return_value = async_return(None)  # type: ignore

        bacprop_service.start()
        bacprop_service._sensor_net.stop.assert_called_once()  # type: ignore
        backnet_thread.join.assert_called_once()

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
            yield {"somethingElse": 6, "sensorId": 5}

        bacprop_service._stream.start.return_value = async_return(None)  # type: ignore
        bacprop_service._stream.read.return_value = mock_read()  # type: ignore

        await bacprop_service._main_loop()
        bacprop_service._handle_sensor_data.assert_has_calls(  # type: ignore
            [
                call({"something": 0.1, "sensorId": 1}),
                call({"somethingElse": 6, "sensorId": 5}),
            ]
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

    def test_handle_bad_data(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"noId": 2}
        bacprop_service._handle_sensor_data(data)

        bacprop_service._sensor_net.get_sensor.assert_not_called()  # type: ignore

    def test_handle_bad_sensor_id(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"sensorId": "Hello"}
        bacprop_service._handle_sensor_data(data)

        bacprop_service._sensor_net.get_sensor.assert_not_called()  # type: ignore

    def test_handle_negative_sensor_id(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"sensorId": "-2"}
        bacprop_service._handle_sensor_data(data)

        bacprop_service._sensor_net.get_sensor.assert_not_called()  # type: ignore

    def test_handle_new_data(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"sensorId": 5, "somethingNew": 2}

        sensor = mocker.create_autospec(Sensor)
        sensor.has_fault.return_value = False  # type: ignore

        bacprop_service._sensor_net.get_sensor.return_value = sensor  # type: ignore

        bacprop_service._handle_sensor_data(data)

        sensor.set_values.assert_called_with({"somethingNew": 2})
        sensor.mark_ok.assert_not_called()

    def test_handle_new_data_faulty_sensor(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"sensorId": 5, "somethingNew": 2}

        sensor = mocker.create_autospec(Sensor)
        sensor.has_fault.return_value = True  # type: ignore

        bacprop_service._sensor_net.get_sensor.return_value = sensor  # type: ignore

        bacprop_service._handle_sensor_data(data)

        sensor.set_values.assert_called_with({"somethingNew": 2})
        sensor.mark_ok.assert_called_once()

    def test_handle_weird_data(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        data = {"sensorId": 5, "something": 2, "badUnit": "2"}

        sensor = mocker.create_autospec(Sensor)
        sensor.has_fault.return_value = False  # type: ignore

        bacprop_service._sensor_net.get_sensor.return_value = sensor  # type: ignore

        bacprop_service._handle_sensor_data(data)

        sensor.set_values.assert_called_with({"something": 2})

    @pytest.mark.asyncio
    async def test_fault_checking(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        sensors = {1: mocker.create_autospec(Sensor), 2: mocker.create_autospec(Sensor)}
        bacprop_service._sensor_net.get_sensors.return_value = sensors  # type: ignore

        bacprop_service._running = True
        asyncio.ensure_future(bacprop_service._fault_check_loop())
        await asyncio.sleep(0)

        bacprop_service._sensor_net.get_sensors.assert_called_once()  # type: ignore

        sensors[1].has_fault.assert_called_once()
        sensors[2].has_fault.assert_called_once()

        # Finish the loop
        bacprop_service._running = False
        await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_faulty_sensor(
        self, mocker: MockFixture, bacprop_service: BacPropagator
    ) -> None:
        sensors = {1: mocker.create_autospec(Sensor), 2: mocker.create_autospec(Sensor)}
        sensors[1].has_fault.return_value = False
        sensors[2].has_fault.return_value = False

        sensors[1].get_update_time.return_value = (
            time.time() - BacPropagator.SENSOR_OUTDATED_TIME - 1
        )
        sensors[2].get_update_time.return_value = time.time()

        bacprop_service._sensor_net.get_sensors.return_value = sensors  # type: ignore

        bacprop_service._running = True
        asyncio.ensure_future(bacprop_service._fault_check_loop())
        await asyncio.sleep(0)

        # Sensor 2 should not be marked as faulty, as it's update time is in range
        sensors[1].mark_fault.assert_called_once()
        sensors[2].mark_fault.assert_not_called()

        bacprop_service._running = False
        await asyncio.sleep(0)
