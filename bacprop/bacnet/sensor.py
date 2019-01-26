import argparse
import random
import time
from typing import Dict, Iterable, Any

from bacpypes.app import Application
from bacpypes.basetypes import StatusFlags
from bacpypes.appservice import ApplicationServiceAccessPoint, StateMachineAccessPoint
from bacpypes.comm import bind
from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from bacpypes.local.device import LocalDeviceObject
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.object import AnalogValueObject, register_object_type
from bacpypes.pdu import Address, LocalBroadcast
from bacpypes.service.device import WhoIsIAmServices
from bacpypes.service.object import (
    ReadWritePropertyMultipleServices,
    ReadWritePropertyServices,
)
from bacpypes.vlan import Node
from bacprop.defs import Logable

# some debugging
_debug = 0
_log = ModuleLogger(globals())


@bacpypes_debugging
class _SensorValueObject(AnalogValueObject, Logable):
    def __init__(self, index: int, name: str):
        kwargs = dict(
            objectIdentifier=("analogValue", index),
            objectName=name,
            presentValue=0,
            statusFlags=[0, 0, 0, 0],
        )
        if _debug:
            _SensorValueObject._debug("__init__ %r", kwargs)

        AnalogValueObject.__init__(self, **kwargs)

    def set_value(self, value: float) -> None:
        self.presentValue = value

    def set_fault(self, fault: bool) -> None:
        self.statusFlags[StatusFlags.bitNames["fault"]] = int(fault)


register_object_type(_SensorValueObject)


@bacpypes_debugging
class _VLANApplication(
    Application,
    WhoIsIAmServices,
    ReadWritePropertyServices,
    ReadWritePropertyMultipleServices,
    Logable,
):
    def __init__(self, vlan_device: LocalDeviceObject, vlan_address: Address) -> None:
        if _debug:
            _VLANApplication._debug("__init__ %r %r", vlan_device, vlan_address)
        Application.__init__(self, localDevice=vlan_device, aseID=None)

        # include a application decoder
        self._asap = ApplicationServiceAccessPoint()

        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self._smap = StateMachineAccessPoint(vlan_device)

        # the segmentation state machines need access to the same device
        # information cache as the application
        self._smap.deviceInfoCache = self.deviceInfoCache

        # a network service access point will be needed
        self._nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self._nse = NetworkServiceElement()
        bind(self._nse, self._nsap)

        # bind the top layers
        bind(self, self._asap, self._smap, self._nsap)

        # create a vlan node at the assigned address
        self._vlan_node = Node(vlan_address)

        # bind the stack to the node, no network number
        self._nsap.bind(self._vlan_node)

    def request(self, apdu: Any) -> None:
        if _debug:
            _VLANApplication._debug("[%s]request %r", self._vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu: Any) -> None:
        if _debug:
            _VLANApplication._debug("[%s]indication %r", self._vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu: Any) -> None:
        if _debug:
            _VLANApplication._debug("[%s]response %r", self._vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu: Any) -> None:
        if _debug:
            _VLANApplication._debug(
                "[%s]confirmation %r", self._vlan_node.address, apdu
            )
        Application.confirmation(self, apdu)

    def get_node(self) -> Node:
        return self._vlan_node


@bacpypes_debugging
class Sensor(_VLANApplication, Logable):
    """
    Bacnet representation of a sensor
    on the network
    """

    def __init__(self, sensor_id: int, vlan_address: Address) -> None:
        vlan_device = LocalDeviceObject(
            objectName="Sensor %d" % (sensor_id,),
            objectIdentifier=("device", sensor_id),
            maxApduLengthAccepted=1024,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        if _debug:
            Sensor._debug("    - vlan_device: %r", vlan_device)

        if _debug:
            Sensor._debug("    - vlan_address: %r", vlan_address)

        # make the application
        _VLANApplication.__init__(self, vlan_device, vlan_address)
        if _debug:
            Sensor._debug("    - vlan_app: %r", self)

        self._id = sensor_id
        self._vlan_address = vlan_address
        self._object_index = 0
        self._objects: Dict[str, _SensorValueObject] = {}
        self._last_updated: float = 0
        self._fault = False

    def _register_objects(self, keys: Iterable[str]) -> None:
        value_keys = list(keys)
        value_keys.sort()

        for key_name in value_keys:
            new_object = _SensorValueObject(self._object_index, key_name)
            self.add_object(new_object)
            self._object_index += 1
            self._objects[key_name] = new_object

    def _clear_objects(self) -> None:
        for attr in self._objects:
            self.delete_object(self._objects[attr])

        self._object_index = 0
        self._objects = {}

    def set_values(self, new_values: Dict[str, float]) -> None:
        """
        Set the values of the sensor. If the attributes have changed,
        update the attributes.
        """
        self._last_updated = time.time()
        if set(self._objects.keys()) != set(new_values.keys()):
            self._clear_objects()
            self._register_objects(new_values)

        for attr in new_values:
            self._objects[attr].set_value(new_values[attr])

    def mark_fault(self) -> None:
        for _object in self._objects.values():
            _object.set_fault(True)

        self._fault = True

    def mark_ok(self) -> None:
        for _object in self._objects.values():
            _object.set_fault(False)

        self._fault = False

    def has_fault(self) -> bool:
        return self._fault

    def get_update_time(self) -> float:
        return self._last_updated
