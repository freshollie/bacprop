from bacpypes.com import Client

class SensorObject(Client):
    def confirmation(self, pdu):
        print("test")