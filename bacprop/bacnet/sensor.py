import argparse
import random
from typing import Dict, Iterable

from bacpypes.app import Application
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

# some debugging
_debug = 1
_log = ModuleLogger(globals())


@bacpypes_debugging
class _SensorValueObject(AnalogValueObject):
    def __init__(self, **kwargs):
        if _debug:
            _SensorValueObject._debug("__init__ %r", kwargs)
        AnalogValueObject.__init__(self, **kwargs)

        self.set_value(0)

    def set_value(self, value):
        self._values["presentValue"] = value


register_object_type(_SensorValueObject)


@bacpypes_debugging
class _VLANApplication(
    Application,
    WhoIsIAmServices,
    ReadWritePropertyServices,
    ReadWritePropertyMultipleServices,
):
    def __init__(
        self, vlan_device: LocalDeviceObject, vlan_address: Address, aseID=None
    ):
        if _debug:
            _VLANApplication._debug(
                "__init__ %r %r aseID=%r", vlan_device, vlan_address, aseID
            )
        Application.__init__(self, localDevice=vlan_device, aseID=aseID)

        self._localAddress = vlan_address

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

    def request(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]request %r", self._vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]indication %r", self._vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]response %r", self._vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu):
        if _debug:
            _VLANApplication._debug(
                "[%s]confirmation %r", self._vlan_node.address, apdu
            )
        Application.confirmation(self, apdu)

    def get_node(self):
        return self._vlan_node

    def get_address(self):
        return self._localAddress


@bacpypes_debugging
class Sensor(_VLANApplication):
    def __init__(self, sensor_id: int):
        vlan_device = LocalDeviceObject(
            objectName="Sensor %d" % (sensor_id,),
            objectIdentifier=("device", sensor_id),
            maxApduLengthAccepted=1024,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        if _debug:
            Sensor._debug("    - vlan_device: %r", vlan_device)

        vlan_address = Address(sensor_id.to_bytes(4, "big"))
        if _debug:
            Sensor._debug("    - vlan_address: %r", vlan_address)

        # make the application
        _VLANApplication.__init__(self, vlan_device, vlan_address)
        if _debug:
            Sensor._debug("    - vlan_app: %r", self)

        self._num_value_objects = 0
        self._objects: Dict[str, _SensorValueObject] = {}

    def _register_objects(self, keys: Iterable[str]):
        keys_list = list(keys)
        keys_list.sort()

        for key in keys_list:
            new_object = _SensorValueObject(
                objectIdentifier=("analogValue", self._num_value_objects),
                objectName=key,
            )
            self.add_object(new_object)
            self._num_value_objects += 1
            self._objects[key] = new_object

    def _clear_objects(self):
        for attr in self._objects:
            self.delete_object(self._objects[attr])

        self._num_value_objects = 0
        self._objects = {}

    def set_values(self, new_values: Dict[str, float]):
        """
        Set the values of the sensor. If the attributes have changed,
        update the attributes.
        """
        if set(self._objects.keys()) != set(new_values.keys()):
            self._clear_objects()
            self._register_objects(new_values)

        for attr in new_values:
            self._objects[attr].set_value(new_values[attr])
