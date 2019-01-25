from bacpypes.bvllservice import AnnexJCodec, BIPSimple, UDPMultiplexer
from bacpypes.comm import bind
from bacpypes.core import deferred, run
from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.pdu import Address, LocalBroadcast
from bacpypes.vlan import Network, Node
from bacprop.bacnet.sensor import Sensor

# some debugging
_debug = 1
_log = ModuleLogger(globals())


@bacpypes_debugging
class _VLANRouter:
    def __init__(self, local_address, local_network):
        if _debug:
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


class VirtualSensorNetwork(Network):
    def __init__(self, local_address: str):
        Network.__init__(self, broadcast_address=LocalBroadcast())

        # create the VLAN router, bind it to the local network
        self._router = _VLANRouter(Address(local_address), 0)

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
