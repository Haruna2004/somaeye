from fastapi import FastAPI, WebSocket, Request, Response, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import json
import base64
import time
from typing import List, Dict
from vision_worker import VisionWorker
from reasoning_engine import ReasoningEngine
from audio_output import AudioOutput
from notifier import TelegramNotifier
from contextlib import asynccontextmanager
from logger_utils import logger, time_it
import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Manual .env loader
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip('"').strip("'")

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'")
vision = VisionWorker()
reasoner = ReasoningEngine(GEMINI_API_KEY)
audio = AudioOutput()
notifier = TelegramNotifier()

# Global metrics for Heartbeat and Telemetry
START_TIME = time.time()
ALERT_COUNT = 0
FRAME_COUNT = 0
ACTIVE_WS_CONNECTIONS = 0

# Global state
current_prompt = "Alert if someone is acting suspicious or lingering."
system_paused = False
VISION_INTERVAL = 2
ALERT_COOLDOWN = 5

# Per-camera state dictionary. Format: { "camera_id": {"latest_frame_bytes": ..., "events": [], "last_vision_time": 0} }
active_cameras_state: Dict[str, dict] = {}

# Shared Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.viewers: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_type: str = "camera"):
        global ACTIVE_WS_CONNECTIONS
        await websocket.accept()
        self.active_connections.append(websocket)
        if client_type == "viewer" or client_type == "dashboard":
             self.viewers.append(websocket)
        ACTIVE_WS_CONNECTIONS = len(self.active_connections)
        logger.info(f"WS | {client_type} Connected. Total: {ACTIVE_WS_CONNECTIONS}")

    def disconnect(self, websocket: WebSocket):
        global ACTIVE_WS_CONNECTIONS
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.viewers:
            self.viewers.remove(websocket)
        ACTIVE_WS_CONNECTIONS = len(self.active_connections)
        logger.info(f"WS | Client Disconnected. Remaining: {ACTIVE_WS_CONNECTIONS}")

    async def broadcast_to_viewers(self, message: dict):
        for viewer in self.viewers:
            try:
                await viewer.send_text(json.dumps(message))
            except:
                pass

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

async def heartbeat_loop():
    """System Health Check (every 60s)"""
    logger.debug("HEARTBEAT | Monitor Active.")
    while True:
        try:
            uptime_m = (time.time() - START_TIME) / 60
            status = "PAUSED" if system_paused else "ACTIVE"
            logger.info(
                f"STATUS: {status} | Uptime: {uptime_m:.1f}m | Alerts: {ALERT_COUNT} | Frames: {FRAME_COUNT}"
            )
        except Exception as e:
            logger.error(f"HEARTBEAT | Error: {e}")
        await asyncio.sleep(60)

async def evaluate_camera(cam_id, state, current_time):
    global ALERT_COUNT
    active_people = [e for e in state.get("events", []) if e.get('object') == 'person']
    
    if active_people:
        if state.get("latest_frame_bytes") and (current_time - state.get("last_vision_time", 0)) >= VISION_INTERVAL:
            img_to_send = state["latest_frame_bytes"]
            # Preemptively update time to avoid race condition double-fires
            state["last_vision_time"] = current_time
            
            cam_prompt = f"[Camera: {cam_id}] " + current_prompt
            result = await reasoner.evaluate_behavior(cam_prompt, img_to_send)
            
            if result and result.get("trigger"):
                ALERT_COUNT += 1
                msg = f"[{cam_id}] {result.get('message')}"
                logger.warning(f"ALERT | TRIGGERED: {msg}")
                
                await manager.broadcast_to_viewers({"alert": msg})
                await notifier.send_alert(msg, img_to_send)
                
                # Apply the cooldown to THIS camera, preventing it from spamming, without pausing other cameras
                state["last_vision_time"] = current_time + ALERT_COOLDOWN
    else:
        # Reset vision time if no one is in frame so it evaluates immediately upon entry
        state["last_vision_time"] = 0

async def reasoning_loop():
    global active_cameras_state
    logger.debug("REASONING | Main loop active.")
    while True:
        try:
            if not system_paused:
                current_time = time.time()
                tasks = []
                for cam_id, state in list(active_cameras_state.items()):
                    if "last_vision_time" not in state:
                        state["last_vision_time"] = 0
                    tasks.append(evaluate_camera(cam_id, state, current_time))
                
                if tasks:
                    # Run all camera API calls completely concurrently!
                    await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"REASONING | Error in loop: {e}")
        await asyncio.sleep(0.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    rtc_task = asyncio.create_task(reasoning_loop())
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    yield
    rtc_task.cancel()
    heartbeat_task.cancel()
    logger.info("SYSTEM | Shutdown complete.")

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pause_label": "Resume System" if system_paused else "Pause System",
        "pause_class": "paused" if system_paused else "",
        "status_text": "System Paused" if system_paused else "System Active",
        "status_color": "#ef4444" if system_paused else "#34d399",
        "status_bg": "rgba(239, 68, 68, 0.1)" if system_paused else "rgba(52, 211, 153, 0.1)"
    })

@app.get("/sender", response_class=HTMLResponse)
async def get_sender(request: Request):
    return templates.TemplateResponse("sender.html", {"request": request})

@app.post("/set-prompt")
async def set_prompt(request: Request):
    data = await request.json()
    global current_prompt, active_cameras_state
    current_prompt = data.get("prompt")
    # Clear out buffers on prompt change
    for cam_id in active_cameras_state:
        active_cameras_state[cam_id]["events"] = []
    
    logger.info(f"CONFIG | Prompt updated. Rule: {current_prompt}")
    return {"status": "ok"}

@app.post("/toggle-pause")
async def toggle_pause():
    global system_paused
    system_paused = not system_paused
    status = "PAUSED" if system_paused else "ACTIVE"
    logger.info(f"SYSTEM | Mode changed: {status}")
    return {"status": "ok", "paused": system_paused}

@app.websocket("/ws/{client_type}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_type: str, client_id: str):
    await manager.connect(websocket, client_type)
    global FRAME_COUNT, active_cameras_state
    
    # Initialize state for this camera
    if client_type in ["camera", "dashboard"]:
        if client_id not in active_cameras_state:
            active_cameras_state[client_id] = {
                "latest_frame_bytes": None,
                "events": [],
                "last_vision_time": 0
            }
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if system_paused:
                await asyncio.sleep(0.1)
                continue
                
            json_data = json.loads(data)
            
            # If this is a viewer/dashboard asking for keepalive, just respond ok
            if "ping" in json_data:
                await websocket.send_text(json.dumps({"pong": True}))
                continue

            if "image" in json_data and client_id in active_cameras_state:
                try:
                    image_bytes = base64.b64decode(json_data["image"])
                    active_cameras_state[client_id]["latest_frame_bytes"] = image_bytes
                    
                    # Note: We now instantiate a new VisionWorker or just use the global one.
                    # Since VisionWorker does purely structural CV (YOLO inference), using the global is fine 
                    # as long as we process sequentially, but let's process the frame:
                    processed_bytes, detections = vision.process_frame(image_bytes)
                    FRAME_COUNT += 1
                    
                    if processed_bytes:
                        # Store events for this specific camera
                        active_cameras_state[client_id]["events"] = detections
                        
                        encoded_result = base64.b64encode(processed_bytes).decode('utf-8')
                        response_data = {
                            "type": "camera_frame",
                            "camera_id": client_id,
                            "image": encoded_result,
                            "detections": detections
                        }
                        
                        # Only send processing frame directly if it's the sender itself wanting it (dashboard)
                        if client_type == "dashboard":
                            await websocket.send_text(json.dumps(response_data))
                        else:
                            await websocket.send_text(json.dumps({"status": "ok"}))

                        # Broadcast this frame to ALL viewers so they can see multiple cameras
                        await manager.broadcast_to_viewers(response_data)
                    else:
                        await websocket.send_text(json.dumps({"status": "processing_failed"}))
                except Exception as e:
                    logger.error(f"WS | Frame error: {e}")
                    await websocket.send_text(json.dumps({"status": "error"}))
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if client_type == "camera" and client_id in active_cameras_state:
            active_cameras_state.pop(client_id, None)
            # Broadcast the disconnect event to all viewers asynchronously
            asyncio.create_task(manager.broadcast_to_viewers({
                "type": "camera_disconnected",
                "camera_id": client_id
            }))
    except Exception as e:
        logger.error(f"WS | Global error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    logger.info("SYSTEM | Booting AI Surveillance Platform...")
    print("\n" + "="*50)
    print(f"🚀 WatchTower is running!")
    print(f"🖥️  Local Dashboard:    http://localhost:8000")
    print(f"📱 Network Dashboard:  http://{local_ip}:8000")
    print(f"📷 Network Sender:     http://{local_ip}:8000/sender")
    print("="*50 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
