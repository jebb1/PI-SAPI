import serial
import json
import asyncio

class SerialDevice:
    def __init__(self, port="/dev/cu.usbserial-0001", baud_rate=9600):
        self.port = port
        self.baud_rate = baud_rate
        self.packetqueue: asyncio.Queue = asyncio.Queue()  # Queue to communicate with the WebSocket


    async def initialize_connection(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            await asyncio.sleep(2)  # Allow time for the connection to initialize
            print("Connection to serial device established.")
            await asyncio.sleep(2)
        except serial.SerialException as e:
            print(f"Error initializing serial port: {e}")
            self.ser = None

    # async def start_packet_process(self):
    #     if not self.ser:
    #         print("Serial device is not initialized.")
    #         return
        
    #     self.ser.reset_input_buffer()
    #     while True:
    #         if self.ser.in_waiting > 0:
    #             data = self.ser.readline().decode("utf-8").strip()
    #             try:
    #                 json_data = json.loads(data)
    #                 if self.queue:
    #                     print(f'Recieved: {json_data}')
    #                     if self.queue.full():
    #                         print("CLEARING QUEUE")
    #                         self.queue = asyncio.Queue()
    #                     print(f'Queue length {self.queue.qsize()}')
    #                     await self.queue.put(json_data)  # Place new data in the queue
    #             except json.JSONDecodeError:
    #                 print(f"Failed to decode data: {data}")
    async def start_packet_process(self):
        if not self.ser:
            print("Serial device is not initialized.")
            return

        self.ser.reset_input_buffer()
        while True:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode("utf-8").strip()
                    try:
                        json_data = json.loads(data)
                        if not self.packetqueue.full():
                            await self.packetqueue.put(json_data)
                            print(f"Queue size: {self.packetqueue.qsize()} | Data added: {json_data}")
                        else:
                            print("Queue is full; discarding data")
                    except json.JSONDecodeError:
                        print(f"Failed to decode data: {data}")
                else:
                    print("NO SERIAL DATA TO BE COLLECTED")
            except Exception as e:
                print(f"Error reading from serial: {e}")
            await asyncio.sleep(0.2)  # Allow asyncio loop to process other tasks

