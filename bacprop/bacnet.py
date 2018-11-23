import random
import argparse

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run, deferred
from bacpypes.comm import bind

from bacpypes.pdu import Address, LocalBroadcast
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import BIPSimple, AnnexJCodec, UDPMultiplexer

from bacpypes.app import Application
from bacpypes.appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from bacpypes.local.device import LocalDeviceObject
from bacpypes.service.device import WhoIsIAmServices
from bacpypes.service.object import (
    ReadWritePropertyMultipleServices,
    ReadWritePropertyServices,
)

from bacpypes.primitivedata import Real
from bacpypes.object import AnalogValueObject, Property, register_object_type

from bacpypes.vlan import Network, Node
from bacpypes.errors import ExecutionError

# some debugging
_debug = 1
_log = ModuleLogger(globals())


@bacpypes_debugging
class SensorValueObject(AnalogValueObject):
    def __init__(self, **kwargs):
        if _debug:
            SensorValueObject._debug("__init__ %r", kwargs)
        AnalogValueObject.__init__(self, **kwargs)

        self.set_value(5)

    def set_value(self, value):
        self._values["presentValue"] = value


register_object_type(SensorValueObject)

#
#   VLANApplication
#


@bacpypes_debugging
class VLANApplication(
    Application,
    WhoIsIAmServices,
    ReadWritePropertyServices,
    ReadWritePropertyMultipleServices,
):
    def __init__(self, vlan_device, vlan_address, aseID=None):
        if _debug:
            VLANApplication._debug(
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
            VLANApplication._debug("[%s]request %r", self.vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu):
        if _debug:
            VLANApplication._debug("[%s]indication %r", self.vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu):
        if _debug:
            VLANApplication._debug("[%s]response %r", self.vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu):
        if _debug:
            VLANApplication._debug("[%s]confirmation %r", self.vlan_node.address, apdu)
        Application.confirmation(self, apdu)


#
#   VLANRouter
#


@bacpypes_debugging
class VLANRouter:
    def __init__(self, local_address, local_network):
        if _debug:
            VLANRouter._debug("__init__ %r %r", local_address, local_network)

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # create a BIPSimple, bound to the Annex J server
        # on the UDP multiplexer
        self.bip = BIPSimple(local_address)
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(local_address)

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to the local network
        self.nsap.bind(self.bip, local_network, local_address)


class Sensor(VLANApplication):
    def __init__(self, sensor_id):
        vlan_device = LocalDeviceObject(
            objectName="Sensor %d" % (sensor_id,),
            objectIdentifier=("device", sensor_id),
            maxApduLengthAccepted=1024,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        _log.debug("    - vlan_device: %r", vlan_device)

        vlan_address = Address(sensor_id)
        _log.debug("    - vlan_address: %r", vlan_address)

        # make the application, add it to the network
        VLANApplication.__init__(self, vlan_device, vlan_address)
        _log.debug("    - vlan_app: %r", self)

        self._num_value_objects = 0

        self._temp = self._add_value_object("analogValue", "temperature")
        self._humidity = self._add_value_object("analogValue", "humidity")
        self._co2 = self._add_value_object("analogValue", "co2")
        self._timestamp = self._add_value_object("analogValue", "timestamp")

    def _add_value_object(self, _type, name) -> SensorValueObject:
        new_object = SensorValueObject(
            objectIdentifier=(_type, self._num_value_objects), objectName=name
        )
        self.add_object(new_object)
        self._num_value_objects += 1

        return new_object

    def set_values(self, temp, humidity, co2, timestamp):
        if _debug:
            _log.debug(
                f"Setting values: temp={temp}, hum={humidity}, co2={co2}, ts={timestamp}"
            )

        self._temp.set_value(temp)
        self._humidity.set_value(humidity)
        self._co2.set_value(co2)
        self._timestamp.set_value(timestamp)


class VirtualSensorNetwork(Network):
    def __init__(self, local_address):
        Network.__init__(self, broadcast_address=LocalBroadcast())

        # create the VLAN router, bind it to the local network
        self._router = VLANRouter(Address(local_address), 0)

        # create a node for the router, address 1 on the VLAN
        router_node = Node(Address(1))
        self.add_node(router_node)

        # bind the router stack to the vlan network through this node
        self._router.nsap.bind(router_node, 1)

        # send network topology
        deferred(self._router.nse.i_am_router_to_network)

    def add_sensor(self, device: Sensor):
        self.add_node(device.vlan_node)

    def run(self):
        run()


if __name__ == "__main__":
    # parse the command line arguments
    parser = ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    args = parser.parse_args()

    if _debug:
        _log.debug("initialization")
    if _debug:
        _log.debug("    - args: %r", args)
    network = VirtualSensorNetwork("0.0.0.0")
    for i in range(2):
        network.add_sensor(Sensor(i))

    network.run()
