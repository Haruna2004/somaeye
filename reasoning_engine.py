from google import genai
from google.genai import types
import json
import os
from logger_utils import logger, time_it

class ReasoningEngine:
    def __init__(self, api_key):
        logger.debug("GEMINI | Configuring Reasoning Engine (google-genai)...")
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3-flash-preview'
        self.event_buffer = []
        self.max_buffer_size = 20
        logger.debug(f"GEMINI | Engine ready with model: {self.model_id}")

    def add_event(self, event):
        self.event_buffer.append(event)
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop(0)

    @time_it
    async def evaluate_behavior(self, user_prompt, image_bytes=None):
        if not self.event_buffer and not image_bytes:
            return None

        # Format events for the prompt
        events_str = json.dumps(self.event_buffer, indent=2)
        
        has_image = "PROVIDED (Use this for visual details)" if image_bytes else "NOT PROVIDED (Do not guess visual details)"
        
        prompt_text = f"""
        You are an advanced AI surveillance reasoning engine.
        
        YOUR MISSION:
        Evaluate the provided VISION LOGS and/or IMAGE against the CUSTOMER PROMPT.
        
        STRICT OPERATIONAL RULES:
        1. VISION CONTEXT: An image is currently {has_image}.
        2. VISUAL CONFIRMATION: If the prompt requires visual detail (colors, glasses, hair, smiling) and NO IMAGE is provided, you must NOT trigger an alert.
        3. ACCURACY: If an image IS provided, look extremely closely at faces and clothing. Do not miss small details like eyeglasses.
        4. NO PARROTING: Never use the word "Concentrate" or "Requirements" in your message. Write a natural sounding alert.
        5. CHAIN OF THOUGHT: Mentally identify the person, check their movement in the logs, then check the image for the specific visual triggers requested.
        
        CUSTOMER PROMPT: "{user_prompt}"
        
        RECENT VISION LOGS (YOLO Tracking):
        {events_str}
        
        RESPONSE FORMAT (JSON ONLY):
        {{
            "trigger": true/false,
            "message": "A concise, professional description of why the alert triggered (e.g., 'Person wearing a blue shirt and glasses detected near exit')"
        }}
        
        If you decide NOT to trigger, return:
        {{
            "trigger": false,
            "message": ""
        }}
        """

        try:
            logger.debug(f"GEMINI | Requesting evaluation ({self.model_id}). Image: {bool(image_bytes)}")
            
            contents = [prompt_text]
            if image_bytes:
                contents.append(
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                )

            # Use asynchronous client for non-blocking generation
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            text = response.text.strip()
            
            if not text or text.lower() == "no_alert":
                return {"trigger": False, "message": ""}
                
            result = json.loads(text)
            
            # Simple sanitization to prevent parroting the instructions
            if "concentrate" in result.get("message", "").lower():
                logger.warning("GEMINI | Blocked instruction parroting.")
                result["trigger"] = False
            
            if result.get("trigger"):
                logger.info(f"GEMINI | Alert Generated: {result.get('message')}")
                
            return result
        except Exception as e:
            logger.error(f"GEMINI | Error in reasoning engine: {e}")
            return None
