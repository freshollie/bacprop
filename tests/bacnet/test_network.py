from bacprop.bacnet.network import VirtualSensorNetwork
from bacpypes.pdu import Address
from bacprop.bacnet.sensor import Sensor

from pytest_mock import MockFixture
import pytest


class TestVirtualSensorNetwork:
    def test_init_address(self, mocker: MockFixture):
        mock_router = mocker.patch("bacprop.bacnet.network._VLANRouter")

        VirtualSensorNetwork("0.0.0.0")
        mock_router.assert_called_once_with(Address("0.0.0.0"), 0)

    def test_init_router(self, mocker: MockFixture):
        mocker.patch("bacprop.bacnet.network._VLANRouer")
        network = VirtualSensorNetwork("0.0.0.0")

        router_node = network.nodes[0]

        # The router node on the network should be address 1
        assert router_node.address == Address(1)

        # pylint: disable=no-member
        network._router.bind.assert_called_once_with(router_node, 1)
        network._router.start.assert_called_once()

    def test_add_sensor(self, mocker: MockFixture):
        mocker.patch("bacprop.bacnet.network._VLANRouter")

        network = VirtualSensorNetwork("0.0.0.0")
        assert len(network.nodes) == 1

        sensor = Sensor(1)
        network.add_sensor(sensor)

        assert len(network.nodes) == 2
        assert network.nodes[-1] == sensor.get_node()
