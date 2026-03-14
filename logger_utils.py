import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

class BlackboxLogger:
    def __init__(self, name="AI_Surveillance", log_dir="blackbox"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers if re-initialized
        if not self.logger.handlers:
            # 1. Console Handler (Minimal / Clean)
            # Only [HH:MM:SS] | LEVEL | Message
            console_formatter = logging.Formatter(
                '[%(asctime)s] | %(levelname)-7s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
            
            # 2. Blackbox File Handler (Detailed / Audit)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-7s | %(filename)s:%(lineno)d | %(message)s'
            )
            
            # Use TimedRotatingFileHandler for 30 min intervals
            # 'M' for minutes, interval=30
            file_handler = TimedRotatingFileHandler(
                filename=os.path.join(self.log_dir, "audit.log"),
                when="M",
                interval=30,
                backupCount=48 # Keep 24 hours of logs
            )
            # Customizing the suffix to match timestamp request
            file_handler.suffix = "%Y-%m-%d_%H-%M-%S"
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

# Global instances for timing
def time_it(func):
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        # Logging the latency
        logging.getLogger("AI_Surveillance").debug(
            f"TELEMETRY | {func.__name__} took {(end - start)*1000:.2f}ms"
        )
        return result
    return wrapper

def time_it_sync(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logging.getLogger("AI_Surveillance").debug(
            f"TELEMETRY | {func.__name__} took {(end - start)*1000:.2f}ms"
        )
        return result
    return wrapper

# Initialize once
blackbox = BlackboxLogger()
logger = blackbox.get_logger()
logger.info("Blackbox Logger Initialized. Audit files rotating every 30 minutes.")
