from fastapi import FastAPI, WebSocket, Request, Response, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import json
import base64
import time
from typing import List
from vision_worker import VisionWorker
from reasoning_engine import ReasoningEngine
from audio_output import AudioOutput
from notifier import TelegramNotifier
from contextlib import asynccontextmanager
from logger_utils import logger, time_it

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
latest_frame_bytes = None
last_gemini_vision_time = 0
VISION_INTERVAL = 2
ALERT_COOLDOWN = 5

# Shared Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        global ACTIVE_WS_CONNECTIONS
        await websocket.accept()
        self.active_connections.append(websocket)
        ACTIVE_WS_CONNECTIONS = len(self.active_connections)
        logger.info(f"WS | Client Connected. Total: {ACTIVE_WS_CONNECTIONS}")

    def disconnect(self, websocket: WebSocket):
        global ACTIVE_WS_CONNECTIONS
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        ACTIVE_WS_CONNECTIONS = len(self.active_connections)
        logger.info(f"WS | Client Disconnected. Remaining: {ACTIVE_WS_CONNECTIONS}")

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

async def reasoning_loop():
    global last_gemini_vision_time, ALERT_COUNT
    logger.debug("REASONING | Main loop active.")
    while True:
        try:
            if not system_paused:
                current_time = time.time()
                include_image = False
                
                # Only wake up Gemini if YOLO sees a person
                active_people = [e for e in reasoner.event_buffer if e.get('object') == 'person']
                
                if active_people:
                    if latest_frame_bytes and (current_time - last_gemini_vision_time) >= VISION_INTERVAL:
                        include_image = True
                        last_gemini_vision_time = current_time
                    
                    img_to_send = latest_frame_bytes if include_image else None
                    result = await reasoner.evaluate_behavior(current_prompt, img_to_send)
                    
                    if result and result.get("trigger"):
                        ALERT_COUNT += 1
                        msg = result.get("message")
                        logger.warning(f"ALERT | TRIGGERED: {msg}")
                        
                        # Send notifications
                        await manager.broadcast({"alert": msg})
                        # audio.speak(msg)
                        await notifier.send_alert(msg, img_to_send)
                        
                        await asyncio.sleep(ALERT_COOLDOWN)
                else:
                    last_gemini_vision_time = 0
                    
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

@app.post("/set-prompt")
async def set_prompt(request: Request):
    data = await request.json()
    global current_prompt, latest_frame_bytes
    current_prompt = data.get("prompt")
    reasoner.event_buffer = [] 
    latest_frame_bytes = None
    logger.info(f"CONFIG | Prompt updated. Rule: {current_prompt}")
    return {"status": "ok"}

@app.post("/toggle-pause")
async def toggle_pause():
    global system_paused
    system_paused = not system_paused
    status = "PAUSED" if system_paused else "ACTIVE"
    logger.info(f"SYSTEM | Mode changed: {status}")
    return {"status": "ok", "paused": system_paused}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    global latest_frame_bytes, FRAME_COUNT
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if system_paused:
                await asyncio.sleep(0.1)
                continue
                
            json_data = json.loads(data)
            if "image" in json_data:
                try:
                    image_bytes = base64.b64decode(json_data["image"])
                    latest_frame_bytes = image_bytes
                    
                    processed_bytes, detections = vision.process_frame(image_bytes)
                    FRAME_COUNT += 1
                    
                    if processed_bytes:
                        for d in detections:
                            reasoner.add_event(d)
                        
                        encoded_result = base64.b64encode(processed_bytes).decode('utf-8')
                        response_data = {
                            "image": encoded_result,
                            "detections": detections
                        }
                        await websocket.send_text(json.dumps(response_data))
                    else:
                        await websocket.send_text(json.dumps({"status": "processing_failed"}))
                except Exception as e:
                    logger.error(f"WS | Frame error: {e}")
                    await websocket.send_text(json.dumps({"status": "error"}))
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS | Global error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    logger.info("SYSTEM | Booting AI Surveillance Platform...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
