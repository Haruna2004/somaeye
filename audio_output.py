import os
import subprocess

class AudioOutput:
    def __init__(self):
        # Native MacOS 'say' requires no initialization
        print("Audio Output: Using native macOS 'say' engine.")

    def speak(self, text):
        """Uses the native macOS 'say' command for zero-latency local speech."""
        if not text:
            return

        print(f"Speaking: {text}")
        try:
            # Using 'Tessa' voice as requested for a more pleasant sound
            subprocess.run(["say", "-v", "Tessa", text], check=True)
            
        except Exception as e:
            # Fallback to simulated print if even the system command fails
            print(f"Native Speech Error: {e}")
            print(f"Speech (Simulated): {text}")
