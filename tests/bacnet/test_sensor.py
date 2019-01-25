from bacpypes.pdu import Address
from bacpypes.apdu import ReadPropertyRequest
from bacpypes.object import get_datatype

from bacprop.bacnet.sensor import Sensor, Application
from pytest_mock import MockFixture


class TestSensor:
    def test_init_id(self) -> None:
        sensor = Sensor(1)
        assert sensor.localDevice.ReadProperty("objectIdentifier") == ("device", 1)

        sensor = Sensor(65565)
        assert sensor.localDevice.ReadProperty("objectIdentifier") == ("device", 65565)

    def test_init_address(self) -> None:
        sensor = Sensor(1)
        assert sensor.get_address() == Address((1).to_bytes(4, "big"))

        sensor = Sensor(65565)
        assert sensor.get_address() == Address((65565).to_bytes(4, "big"))

    def test_set_values(self) -> None:
        sensor = Sensor(0)

        sensor.set_values({"testProp": 0.2})

        prop = sensor.get_object_name("testProp")
        assert prop.ReadProperty("presentValue") == 0.2

        sensor.set_values({"testProp": 0.6})

        prop = sensor.get_object_name("testProp")
        assert prop.ReadProperty("presentValue") == 0.6

    def test_change_props(self) -> None:
        sensor = Sensor(0)

        sensor.set_values({"testProp": 0.2})

        prop = sensor.get_object_name("testProp")
        assert prop.ReadProperty("presentValue") == 0.2

        # Replace all props
        sensor.set_values({"otherProp": 50, "prop2": -20})

        # Make sure the old one is gone
        assert not sensor.get_object_name("testProp")

        # Do we have the new ones?
        assert sensor.get_object_name("otherProp").ReadProperty("presentValue") == 50
        assert sensor.get_object_name("prop2").ReadProperty("presentValue") == -20

    def test_request_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0)
        mocker.patch.object(Application, "request", autospec=True)

        sensor.request("something")
        Application.request.assert_called_with(sensor, "something")

    def test_response_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0)

        mocker.patch.object(Application, "response", autospec=True)

        sensor.response("something")
        Application.response.assert_called_with(sensor, "something")

    def test_indication_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0)

        mocker.patch.object(Application, "indication", autospec=True)

        sensor.indication("something")
        Application.indication.assert_called_with(sensor, "something")

    def test_confirmation_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0)

        mocker.patch.object(Application, "confirmation", autospec=True)

        sensor.confirmation("something")
        Application.confirmation.assert_called_with(sensor, "something")

