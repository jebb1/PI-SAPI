from fastapi import FastAPI, WebSocket
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

class SerialProtocol(asyncio.Protocol):
    def __init__(self):
        self.buffer = b''
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print("Serial connection established.")

    def data_received(self, data):
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            line = line.decode('utf-8', errors='replace').strip()
            #print(f"Raw Serial Data: {line}")

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
    baud_rate = 115200
    while True:
        try:
            loop = asyncio.get_event_loop()
            await serial_asyncio.create_serial_connection(
                loop,
                SerialProtocol,
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

    try:
        while True:
            data = await serial_queue.get()
            await websocket.send_json(data)
            #print(f"Sent: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
        print("WebSocket connection closed.")
