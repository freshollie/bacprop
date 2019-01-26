from bacprop.bacnet.network import VirtualSensorNetwork
from bacprop.bacnet import network
from bacpypes.pdu import Address
from bacpypes.comm import service_map
from bacprop.bacnet.sensor import Sensor

from pytest_mock import MockFixture

# Required for full coverage
network._debug = 1


class TestVirtualSensorNetwork:
    def test_init_address(self, mocker: MockFixture) -> None:
        mock_router = mocker.patch("bacprop.bacnet.network._VLANRouter")

        VirtualSensorNetwork("0.0.0.0")
        mock_router.assert_called_once_with(Address("0.0.0.0"), 0)

    def test_init_router(self, mocker: MockFixture) -> None:
        mocker.patch("bacprop.bacnet.network._VLANRouter")
        network = VirtualSensorNetwork("0.0.0.0")

        router_node = network.nodes[0]

        # The router node on the network should be address 1
        assert router_node.address == Address((1).to_bytes(4, "big"))

        # pylint: disable=no-member
        network._router.bind.assert_called_once_with(router_node, 1)  # type: ignore
        network._router.start.assert_called_once()  # type: ignore

    def test_create_sensor(self, mocker: MockFixture) -> None:
        mocker.patch("bacprop.bacnet.network._VLANRouter")
        network = VirtualSensorNetwork("0.0.0.0")

        sensor = network.create_sensor(7)
        sensor2 = network.create_sensor(8)

        assert len(network.nodes) == 3
        assert network.nodes[-1] == sensor2.get_node()
        assert network.nodes[-2] == sensor.get_node()

        assert sensor._vlan_address == Address((2).to_bytes(4, "big"))
        assert sensor2._vlan_address == Address((3).to_bytes(4, "big"))

    def test_create_sensor_exists(self, mocker: MockFixture) -> None:
        mocker.patch("bacprop.bacnet.network._VLANRouter")
        network = VirtualSensorNetwork("0.0.0.0")

        sensor = network.create_sensor(7)

        try:
            network.create_sensor(7)
            assert False, "Should throw error as sensor already exists"
        except ValueError:
            pass

    def test_get_sensor(self, mocker: MockFixture) -> None:
        mocker.patch("bacprop.bacnet.network._VLANRouter")
        network = VirtualSensorNetwork("0.0.0.0")

        sensor_created = network.create_sensor(7)
        sensor_found = network.get_sensor(7)

        assert sensor_created == sensor_found

    def test_get_sensors(self, mocker: MockFixture) -> None:
        mocker.patch("bacprop.bacnet.network._VLANRouter")
        network = VirtualSensorNetwork("0.0.0.0")

        for i in range(10):
            network.create_sensor(i)

        sensors = network.get_sensors()

        for i in range(10):
            assert type(sensors[i]) == Sensor

    def test_run(self, mocker: MockFixture) -> None:
        mock_run = mocker.patch("bacprop.bacnet.network.run")

        network = VirtualSensorNetwork("0.0.0.0")
        # Teardown
        network._router.mux.close_socket()
        service_map.clear()

        network.run()
        mock_run.assert_called_once()

    def test_stop(self, mocker: MockFixture) -> None:
        mock_stop = mocker.patch("bacprop.bacnet.network.stop")

        network = VirtualSensorNetwork("0.0.0.0")
        # Teardown
        network._router.mux.close_socket()
        service_map.clear()

        network.stop()
        mock_stop.assert_called_once()
