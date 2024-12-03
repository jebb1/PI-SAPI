import asyncio
import time
from serial_tools import SerialDevice
from packets import ASSPacketAdxl345  # Assuming this is used for packet processing

class Vehicle:
    def __init__(self, id, port="/dev/cu.usbserial-0001", baud_rate=9600, queue=None):
        self.serial_device = SerialDevice(port=port, baud_rate=baud_rate, queue=queue or asyncio.Queue())  # Pass in a queue
        self.id = id
        self.last_update = None
        self.pitch: float = None
        self.roll: float = None
        self.heading: float = None
        self.lat: float = None
        self.lon: float = None
        self.altitude: float = None
        self.adxl345: ASSPacketAdxl345 = None
        self.stop_signal = False
        self._task = None  # Store the task for later management

    async def start_processing(self):
        """Start the packet processing coroutine."""
        if not self._task:
            self._task = asyncio.create_task(self._process_serial_data())

    async def _process_serial_data(self):
        """Continuously process data from the SerialDevice."""
        while not self.stop_signal:
            try:
                raw_data = await self.serial_device.packetqueue.get()  # Get raw data from the queue
                packet_type = raw_data.get('type')
                if packet_type == 'adxl345':
                    self._update_adxl345(raw_data)
                else:
                    print(f"Unhandled packet type: {packet_type}")
            except Exception as e:
                print(f"Error processing serial data: {e}")

    def _update_adxl345(self, raw_data):
        """Update the vehicle's adxl345 data based on raw serial input."""
        try:
            self.adxl345 = ASSPacketAdxl345(data=raw_data)
            print(f"Updated ADXL345 data: {self.adxl345}")
        except Exception as e:
            print(f"Error processing ADXL345 packet: {e}")

    async def stop_processing(self):
        """Signal the coroutine to stop and wait for it to finish."""
        self.stop_signal = True
        if self._task:
            await self._task  # Wait for the task to complete

