from bacpypes.pdu import Address
from bacpypes.apdu import ReadPropertyRequest
from bacpypes.object import get_datatype

from bacprop.bacnet.sensor import Sensor, Application
from bacprop.bacnet import sensor
from bacpypes.basetypes import StatusFlags
from pytest_mock import MockFixture
from typing import Dict

import time

sensor._debug = 1


class TestSensor:
    def test_init_id(self) -> None:
        sensor = Sensor(1, Address(1))
        assert sensor.localDevice.ReadProperty("objectIdentifier") == ("device", 1)

        sensor = Sensor(2, Address(2))
        assert sensor.localDevice.ReadProperty("objectIdentifier") == ("device", 2)

    def test_init_address(self) -> None:
        sensor = Sensor(1, Address(2))
        assert sensor._vlan_address == Address(2)

        sensor = Sensor(65565, Address(5))
        assert sensor._vlan_address == Address(5)

    def test_set_values(self) -> None:
        sensor = Sensor(0, Address(0))

        sensor.set_values({"testProp": 0.2})

        prop = sensor.get_object_name("testProp")
        assert prop.ReadProperty("presentValue") == 0.2

        sensor.set_values({"testProp": 0.6})

        prop = sensor.get_object_name("testProp")
        assert prop.ReadProperty("presentValue") == 0.6

        assert abs(time.time() - sensor.get_update_time()) < 1

    def test_set_values_object_order(self) -> None:
        sensor = Sensor(0, Address(0))

        sensor.set_values({"testProp": 0.2, "anotherProp": 0.7})

        prop = sensor.get_object_name("testProp")
        assert prop.ReadProperty("objectIdentifier") == ("analogValue", 1)

        prop2 = sensor.get_object_name("anotherProp")
        assert prop2.ReadProperty("objectIdentifier") == ("analogValue", 0)

    def test_mark_fault(self) -> None:
        sensor = Sensor(0, Address(0))

        values: Dict[str, float] = {"something": 2, "anotherThing": 5}
        sensor.set_values(values)

        for key in values:
            assert (
                sensor.get_object_name(key).ReadProperty("statusFlags")[
                    StatusFlags.bitNames["fault"]
                ]
                == 0
            )

        sensor.mark_fault()
        assert sensor.has_fault()

        for key in values:
            assert (
                sensor.get_object_name(key).ReadProperty("statusFlags")[
                    StatusFlags.bitNames["fault"]
                ]
                == 1
            )

    def test_mark_ok(self) -> None:
        sensor = Sensor(0, Address(0))

        values: Dict[str, float] = {"something": 2, "anotherThing": 5}
        sensor.set_values(values)

        sensor.mark_fault()
        sensor.mark_ok()

        assert not sensor.has_fault()

        for key in values:
            assert (
                sensor.get_object_name(key).ReadProperty("statusFlags")[
                    StatusFlags.bitNames["fault"]
                ]
                == 0
            )

    def test_change_props(self) -> None:
        sensor = Sensor(0, Address(0))

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
        sensor = Sensor(0, Address(0))
        mocker.patch.object(Application, "request", autospec=True)

        sensor.request("something")
        # pylint: disable=no-member
        Application.request.assert_called_with(sensor, "something")

    def test_response_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0, Address(0))

        mocker.patch.object(Application, "response", autospec=True)

        sensor.response("something")
        # pylint: disable=no-member
        Application.response.assert_called_with(sensor, "something")

    def test_indication_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0, Address(0))

        mocker.patch.object(Application, "indication", autospec=True)

        sensor.indication("something")
        # pylint: disable=no-member
        Application.indication.assert_called_with(sensor, "something")

    def test_confirmation_hook(self, mocker: MockFixture) -> None:
        sensor = Sensor(0, Address(0))

        mocker.patch.object(Application, "confirmation", autospec=True)

        sensor.confirmation("something")
        # pylint: disable=no-member
        Application.confirmation.assert_called_with(sensor, "something")

