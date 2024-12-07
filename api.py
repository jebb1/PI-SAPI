from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import serial_asyncio
import json
import packets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared queue for serial data
serial_queue = asyncio.Queue()
serial_send_queue = asyncio.Queue()

class SerialProtocol(asyncio.Protocol):
    def __init__(self, heartbeat_interval=None):
        self.buffer = b''
        self.transport = None
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_task = None
        self.send_data_task = None

    def connection_made(self, transport):
        self.transport = transport
        print("Serial connection established.")
        if self.heartbeat_interval:
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
            self.send_data_task = asyncio.create_task(self.send_data())

    async def send_heartbeat(self):
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                # Replace 'heartbeat_packet' with the actual packet you want to send
                heartbeat_data = packets.HeartbeatPacket()
                self.transport.write(heartbeat_data.encode('utf-8'))
                print("Heartbeat packet sent.")
        except asyncio.CancelledError:
            print("Heartbeat task cancelled.")
            raise

    async def send_data(self):
        """
        Continuously sends data from the serial_send_queue to the serial device.
        Ensures proper rate limiting and error handling.
        """
        try:
            while True:
                # Wait for the next item in the queue (blocking until available)
                data_to_send = await serial_send_queue.get()

                # Ensure transport is available
                if self.transport:
                    try:
                        # Send the data to the serial device
                        self.transport.write(str(data_to_send).encode())
                        print(f"Sent to serial: {data_to_send}")
                    except Exception as e:
                        print(f"Error sending to serial: {e}")
                else:
                    print("Serial transport not available.")

                # Mark the task as done in the queue (optional for `Queue`)
                serial_send_queue.task_done()

                # Add a small delay to limit the sending rate (e.g., 10 Hz)
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            # Handle task cancellation gracefully
            print("send_data task cancelled.")
        except Exception as e:
            # Catch any unexpected errors
            print(f"Unexpected error in send_data: {e}")



    def data_received(self, data):
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            line = line.decode('utf-8', errors='replace').strip()
            print(f"Raw Serial Data: {line}")

            try:
                json_data = json.loads(line)
                asyncio.create_task(serial_queue.put(json_data))
                #print(f"Data added to queue: {json_data}")
            except json.JSONDecodeError:
                print(f"Failed to decode JSON: {line}")

    def connection_lost(self, exc):
        print("Serial connection lost")
        if exc:
            print(f"Error: {exc}")
        # Optionally, attempt to reconnect
        asyncio.create_task(connect_serial())

async def connect_serial():
    port = "/dev/cu.usbserial-0001"  # Replace with your port
    baud_rate = 230400
    heartbeat_interval = 1  # Set your heartbeat interval in seconds

    while True:
        try:
            loop = asyncio.get_event_loop()
            await serial_asyncio.create_serial_connection(
                loop,
                lambda: SerialProtocol(heartbeat_interval=heartbeat_interval),
                port,
                baudrate=baud_rate
            )
            print("Serial connection established.")
            break
        except Exception as e:
            print(f"Failed to connect to serial device: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(connect_serial())

@app.websocket("/ws/sensors")
async def websocket_endpoint(websocket: WebSocket):
    print("WebSocket connection started.")
    await websocket.accept()
    await websocket.send_json(packets.connectionPacket())

    async def handle_incoming_messages():
        try:
            while True:
                message = await websocket.receive_json()  # Or use receive_text() for plain text
                print(f"Received message: {message}")
                # Process the incoming message here
                response = await process_message(message)
                # if response:
                #     await 
        except WebSocketDisconnect:
            print("Client disconnected.")
        except Exception as e:
            print(f"Error receiving message: {e}")

    async def send_sensor_data():
        try:
            while True:
                data = await serial_queue.get()
                await websocket.send_json(data)
                #print(f"Sent: {data}")
        except Exception as e:
            print(f"Error sending data: {e}")

    # Run both sending and receiving in parallel
    await asyncio.gather(
        handle_incoming_messages(),
        send_sensor_data()
    )


async def process_message(message):
    """
    Process the incoming WebSocket message and return a response if needed. This could be changed to have an inner system for 
    fwding packets to esp but acts as a manual filter for now
    """
    # Example: Handle specific commands or actions
    if "t" in message:
        type = message["t"]
        if type == "ui":
            print("recieved packet!")
            # Perform action and optionally return a response
            if  message["uit"] == 'mtest':
                #Make a manual control packet with mctrl and set control type to test ('tst')
                await serial_send_queue.put({"t": "mctrl","ct":"tst"})
        else:
            print(f"Unexpected type!: {type}")
    else:
        print("No type specified in message.")