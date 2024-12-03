from fastapi import FastAPI, WebSocket
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from serial_tools import SerialDevice

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a shared queue for communication

serial_device = SerialDevice()

@app.on_event("startup")
async def startup_event():
    await serial_device.initialize_connection()

# @app.websocket("/ws/adxl345")
# async def websocket_endpoint(websocket: WebSocket):
#     print("ACCEPTING")
#     await websocket.accept()
#     print("CLIENT CONNECTED")
#     asyncio.create_task(serial_device.start_packet_process())
#     print("SERIAL TASK STARTED")
#     try:
#         while websocket.client:
#             # Wait for new data from the queue
#             print("Waiting for data...")
#             if serial_device.queue.empty():
#                 print("No Data From Serial...")
#                 await asyncio.sleep(1)
#                 continue
#             data = await serial_device.queue.get()
#             await websocket.send_json(data)
#             print(f"Sent {data}")
#     except Exception as e:
#         print(f"WebSocket connection closed: {e}")
#     finally:
#         print(f"CLOSING WEBSOCKET")
#         await websocket.close()
@app.websocket("/ws/sensors")
async def websocket_endpoint(websocket: WebSocket):
    fail_count = 0
    print("ACCEPTING")
    await websocket.accept()
    print("CLIENT CONNECTED")
    task = asyncio.create_task(serial_device.start_packet_process())  # Start serial processing
    print("SERIAL TASK STARTED")
    try:
        while True:
            print("Waiting for data")
            if not serial_device.packetqueue.empty():
                data = await serial_device.packetqueue.get()  # Wait for data to arrive
                await websocket.send_json(data)  # Send the data to WebSocket client
                print(f"Sent {data}")
                fail_count = 0
            else: #handle a lack of data often caused by a bad connection
                fail_count +=1
                print(f"No Data Yet...{fail_count}")
                await asyncio.sleep(0.1)
                if fail_count > 100:
                    print('100 fails, reseting conection')
                    task.cancel()
                    serial_device.ser.close()
                    await asyncio.sleep(0.5)
                    await serial_device.initialize_connection()
                    await asyncio.sleep(1)
                    task = asyncio.create_task(serial_device.start_packet_process())  # Start serial processing
                    fail_count = 50 #if its still not working, dont wait as long to try again!
            
    except Exception as e:
        task.cancel()
        print(f"WebSocket connection closed: {e}")
    finally:
        print("CLOSING WEBSOCKET")
        task.cancel()  # Cancel the serial process task
        await websocket.close()