import httpx
import os
from logger_utils import logger

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip('"').strip("'")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip('"').strip("'")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("TelegramNotifier | TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing. Telegram alerts disabled.")
        else:
            logger.info("TelegramNotifier | Configured and ready.")

    async def send_alert(self, message: str, image_bytes: bytes = None):
        if not self.enabled:
            return

        try:
            async with httpx.AsyncClient() as client:
                if image_bytes:
                    # Send photo with caption
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                    files = {'photo': ('alert.jpg', image_bytes, 'image/jpeg')}
                    data = {'chat_id': self.chat_id, 'caption': message}
                    response = await client.post(url, data=data, files=files)
                else:
                    # Send text message
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                    data = {'chat_id': self.chat_id, 'text': message}
                    response = await client.post(url, data=data)
                
                if response.status_code != 200:
                    logger.error(f"TelegramNotifier | Failed to send alert: {response.status_code} - {response.text}")
                else:
                    logger.info("TelegramNotifier | Telegram alert sent successfully.")
        except Exception as e:
            logger.error(f"TelegramNotifier | Error sending alert: {e}")
