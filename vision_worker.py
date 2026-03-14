import cv2
import numpy as np
import time
from ultralytics import YOLO
from logger_utils import logger, time_it_sync

class VisionWorker:
    def __init__(self, model_path='yolo11n.pt'):
        logger.debug(f"YOLO | Loading AI model {model_path}...")
        self.model = YOLO(model_path)
        logger.debug("YOLO | Model loaded successfully.")

    @time_it_sync
    def process_frame(self, frame_bytes: bytes):
        """Processes a single frame from bytes (sent via WebSocket)."""
        # Convert bytes to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error("YOLO | Failed to decode frame bytes.")
            return None, []

        # Run YOLOv11 inference with tracking
        results = self.model.track(frame, persist=True, verbose=False)
        
        detections = []
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            clss = results[0].boxes.cls.cpu().numpy().astype(int)
            
            for box, track_id, cls in zip(boxes, track_ids, clss):
                name = self.model.names[cls]
                detections.append({
                    "track_id": int(track_id),
                    "object": name,
                    "bbox": box.tolist(),
                    "timestamp": time.time()
                })
        
        if detections:
            logger.debug(f"YOLO | Detected: {[d['object'] for d in detections]}")

        # Generate annotated frame
        annotated_frame = results[0].plot()
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        
        return buffer.tobytes(), detections
