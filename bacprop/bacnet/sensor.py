import argparse
import random

from bacpypes.app import Application
from bacpypes.appservice import ApplicationServiceAccessPoint, StateMachineAccessPoint
from bacpypes.comm import bind
from bacpypes.consolelogging import ArgumentParser
from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from bacpypes.errors import ExecutionError
from bacpypes.local.device import LocalDeviceObject
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.object import AnalogValueObject, Property, register_object_type
from bacpypes.pdu import Address, LocalBroadcast
from bacpypes.primitivedata import Real
from bacpypes.service.device import WhoIsIAmServices
from bacpypes.service.object import (
    ReadWritePropertyMultipleServices,
    ReadWritePropertyServices,
)
from bacpypes.vlan import Network, Node

# some debugging
_debug = 1
_log = ModuleLogger(globals())


@bacpypes_debugging
class _SensorValueObject(AnalogValueObject):
    def __init__(self, **kwargs):
        if _debug:
            _SensorValueObject._debug("__init__ %r", kwargs)
        AnalogValueObject.__init__(self, **kwargs)

        self.set_value(5)

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
    def __init__(self, vlan_device, vlan_address, aseID=None):
        if _debug:
            _VLANApplication._debug(
                "__init__ %r %r aseID=%r", vlan_device, vlan_address, aseID
            )
        Application.__init__(self, vlan_device, vlan_address, aseID)

        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()

        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(vlan_device)

        # the segmentation state machines need access to the same device
        # information cache as the application
        self.smap.deviceInfoCache = self.deviceInfoCache

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)

        # create a vlan node at the assigned address
        self.vlan_node = Node(vlan_address)

        # bind the stack to the node, no network number
        self.nsap.bind(self.vlan_node)

    def request(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]request %r", self.vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]indication %r", self.vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]response %r", self.vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu):
        if _debug:
            _VLANApplication._debug("[%s]confirmation %r", self.vlan_node.address, apdu)
        Application.confirmation(self, apdu)


@bacpypes_debugging
class Sensor(_VLANApplication):
    def __init__(self, sensor_id):
        vlan_device = LocalDeviceObject(
            objectName="Sensor %d" % (sensor_id,),
            objectIdentifier=("device", sensor_id),
            maxApduLengthAccepted=1024,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        if _debug:
            Sensor._debug("    - vlan_device: %r", vlan_device)

        vlan_address = Address(sensor_id)
        if _debug:
            Sensor._debug("    - vlan_address: %r", vlan_address)

        # make the application, add it to the network
        _VLANApplication.__init__(self, vlan_device, vlan_address)
        if _debug:
            Sensor._debug("    - vlan_app: %r", self)

        self._num_value_objects = 0

        self._temp = self._add_value_object("analogValue", "temperature")
        self._humidity = self._add_value_object("analogValue", "humidity")
        self._co2 = self._add_value_object("analogValue", "co2")
        self._timestamp = self._add_value_object("analogValue", "timestamp")

    def _add_value_object(self, _type, name) -> _SensorValueObject:
        new_object = _SensorValueObject(
            objectIdentifier=(_type, self._num_value_objects), objectName=name
        )
        self.add_object(new_object)
        self._num_value_objects += 1

        return new_object

    def set_values(self, temp, humidity, co2, timestamp):
        if _debug:
            Sensor._debug(
                f"Setting values: temp={temp}, hum={humidity}, co2={co2}, ts={timestamp}"
            )

        self._temp.set_value(temp)
        self._humidity.set_value(humidity)
        self._co2.set_value(co2)
        self._timestamp.set_value(timestamp)
