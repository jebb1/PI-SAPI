import datetime
import json

class ASSPacket:
    def __init__(self, data) -> None:
        self.data = data
        self.gen_time = data.get('time', datetime.datetime.now().isoformat())
        self.recieve_time = datetime.datetime.now().isoformat()

class ASSPacketAdxl345(ASSPacket):
    def __init__(self, data) -> None:
        super().__init__(data)
        self.x = data.get('x', 0)
        self.y = data.get('y', 0)
        self.z = data.get('z', 0)
        
def connectionPacket():
    return json.loads('{"type":"api","message":"ws_connected","time":-1}')
