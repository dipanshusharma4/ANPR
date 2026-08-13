from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware 
from ultralytics import YOLO
import cv2
from easyocr import Reader
from datetime import datetime
from database.config import user_collection
# from database.models import vehicle_model
import serial
import serial.tools.list_ports
import time
from routes.users import router
import threading
import asyncio
import json
import io
from contextlib import asynccontextmanager

#   Lifespan Event Handler  
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    print("FastAPI server starting...")
    if initialize_arduino():
        print("Arduino initialized successfully.")
    else:
        print("Proceeding without Arduino hardware.")
    
    loop = asyncio.get_event_loop()
    threading.Thread(
        target=run_anpr, 
        args=(loop, manager), 
        daemon=True
    ).start()
    
    yield
    
    # Shutdown Logic
    if arduino and arduino.is_open:
        arduino.close()
        print("Arduino connection closed")
    print("FastAPI server shutting down.")

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # The origin of your React app
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)



app.include_router(router)

# Global variables for video streaming
output_frame = None
frame_lock = threading.Lock()

#   Model & Reader Initialization  
model = YOLO("yolov8n.pt")  
reader = Reader(['en'])

#   Arduino Serial Connection  
arduino = None
ARD_PORT = 'COM4'
BAUD_RATE = 9600

def find_arduino():
    """Auto-detect Arduino port"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino' in port.description or 'CH340' in port.description or 'USB' in port.description:
            return port.device
    return None

def initialize_arduino():
    """Initialize Arduino connection"""
    global arduino, ARD_PORT
    try:
        ARD_PORT_DETECTED = find_arduino()
        if ARD_PORT_DETECTED:
            ARD_PORT = ARD_PORT_DETECTED
            arduino = serial.Serial(ARD_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            response = arduino.readline().decode('utf-8').strip()
            if response == "READY":
                print(f"Arduino connected on {ARD_PORT}")
                return True
        else:
            print("Arduino not found. Running without hardware.")
            return False
    except Exception as e:
        print(f"Arduino connection error: {e}")
        return False

def send_command(cmd):
    """Send command to Arduino and wait for acknowledgment"""
    if arduino and arduino.is_open:
        try:
            arduino.write(f"{cmd}\n".encode('utf-8'))
            time.sleep(0.1)
            response = arduino.readline().decode('utf-8').strip()
            print(f"Arduino Response: {response}")
            return response
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    return None

def open_barrier():
    response = send_command("OPEN")
    return response and "ACK:OPEN" in response

def close_barrier():
    response = send_command("CLOSE")
    return response and "ACK:CLOSE" in response

def get_barrier_status():
    response = send_command("STATUS")
    return response

#   WebSocket Connection Manager  
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        payload = json.dumps(data, default=str)
        for connection in self.active_connections:
            await connection.send_text(payload)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Dashboard client disconnected")

#   Video Streaming Endpoint  
async def get_video_stream():
    global output_frame, frame_lock
    while True:
        with frame_lock:
            if output_frame is None:
                await asyncio.sleep(0.1)
                continue
            frame_bytes = output_frame
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(0.03)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        get_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

#   Manual barrier control endpoints  
@app.get("/barrier/open")
async def manual_open():
    result = open_barrier()
    return {"status": "success" if result else "failed", "action": "open"}

@app.get("/barrier/close")
async def manual_close():
    result = close_barrier()
    return {"status": "success" if result else "failed", "action": "close"}

@app.get("/barrier/status")
async def barrier_status():
    status = get_barrier_status()
    return {"status": status}

#   ANPR Logic (Thread)  
def run_anpr(loop: asyncio.AbstractEventLoop, manager: ConnectionManager):
    global output_frame, frame_lock
    
    #   MODIFIED: Changed from 1 to 0  
    # Change this to 1 if 0 is your laptop's built-in webcam
    # and you want to use an external USB webcam.
    cap = cv2.VideoCapture(1)  
    
    if not cap.isOpened():
        print("Error: Could not open camera. Check index (0 or 1).")
        return
    
    print("ANPR Thread Started... Press 'q' in CV window to quit (or stop server)")
    
    last_plate = ""
    last_detection_time = 0
    DETECTION_COOLDOWN = 5

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error reading frame")
            break

        results = model(frame)
        
        display_status = "SCANNING"
        display_color = (255, 255, 0)
        detected_text = ""

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cropped_img = frame[y1:y2, x1:x2]

                result = reader.readtext(cropped_img)
                
                if result:
                    text = result[0][-2].replace(" ", "").upper()
                    detected_text = text
                    current_time = time.time()
                    
                    if text != last_plate or (current_time - last_detection_time) > DETECTION_COOLDOWN:
                        last_plate = text
                        last_detection_time = current_time
                        
                        data = user_collection.find_one({"number_plate": text})
                        
                        if data:
                            status = "AUTHORIZED"
                            display_color = (0, 255, 0)
                            open_barrier()
                        else:
                            status = "UNAUTHORIZED"
                            display_color = (0, 0, 255)
                            close_barrier()
                        
                        timestamp = datetime.now()
                        print(f" Plate: {text} |  Time: {timestamp} |  Status: {status}")
                        
                        log_entry = {
                            "number_plate": text, 
                            "timestamp": timestamp, 
                            "status": status,
                            "owner_name": data.get("owner_name", "N/A") if data else "N/A",
                            "vehicle_model": data.get("vehicle_model", "N/A") if data else "N/A"
                        }
                        user_collection.insert_one(log_entry)
                        
                        asyncio.run_coroutine_threadsafe(
                            manager.broadcast(log_entry), 
                            loop
                        )
                        
                        display_status = status
                    
                    cv2.putText(frame, f"Plate: {detected_text}", (x1, y1 - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, display_color, 2)
                    cv2.putText(frame, f"Status: {display_status}", (x1, y2 + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, display_color, 2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), display_color, 2)

        with frame_lock:
            (flag, encoded_image) = cv2.imencode(".jpg", frame)
            if flag:
                output_frame = encoded_image.tobytes()

        cv2.imshow("ANPR Gate System", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("ANPR Thread Stopped.")

