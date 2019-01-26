"""
Provide some abstraction layers to the bacpypes
API
"""

from bacpypes.bvllservice import AnnexJCodec, BIPSimple, UDPMultiplexer
from bacpypes.comm import bind
from bacpypes.core import deferred, run, stop
from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.pdu import Address, LocalBroadcast
from bacpypes.vlan import Network, Node
from bacprop.bacnet.sensor import Sensor

from typing import Dict, Union, NoReturn, List
from bacprop.defs import Logable

_debug = 0
_log = ModuleLogger(globals())


@bacpypes_debugging
class _VLANRouter(Logable):
    def __init__(self, local_address: Address, local_network: int):
        if _debug:
            # pylint: disable=no-member
            # type: ignore
            _VLANRouter._debug("__init__ %r %r", local_address, local_network)

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

    def bind(self, node: Node, address: int) -> None:
        self.nsap.bind(node, address)

    def start(self) -> None:
        # send network topology
        deferred(self.nse.i_am_router_to_network)


class VirtualSensorNetwork(Network):
    def __init__(self, local_address: str):
        Network.__init__(self, broadcast_address=LocalBroadcast())

        # create the VLAN router, bind it to the local network
        self._router = _VLANRouter(Address(local_address), 0)

        self._address_index = 1
        # create a node for the router, address 1 on the VLAN
        router_node = Node(Address(self._address_index.to_bytes(4, "big")))
        self._address_index += 1

        self.add_node(router_node)

        # bind the router stack to the vlan network through this node
        self._router.bind(router_node, 1)
        self._router.start()

        self._sensors: Dict[int, Sensor] = {}

    def get_sensor(self, _id: int) -> Union[Sensor, None]:
        return self._sensors.get(_id)

    def get_sensors(self) -> Dict[int, Sensor]:
        return self._sensors.copy()

    def create_sensor(self, _id: int) -> Sensor:
        if self.get_sensor(_id):
            raise ValueError(f"Sensor {_id} already exists on network")

        sensor = Sensor(_id, Address(self._address_index.to_bytes(4, "big")))
        self._sensors[_id] = sensor

        self.add_node(sensor.get_node())
        self._address_index += 1

        return sensor

    def run(self) -> None:
        run(sigterm=None, sigusr1=None)

    def stop(self) -> None:
        stop()
