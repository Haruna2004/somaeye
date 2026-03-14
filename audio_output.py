import os
import subprocess

class AudioOutput:
    def __init__(self):
        # Native MacOS 'say' requires no initialization
        print("Audio Output: Using native macOS 'say' engine.")

    def speak(self, text):
        """Uses the native macOS 'say' command in a non-blocking manner."""
        if not text:
            return

        print(f"Speaking: {text}")
        try:
            # Using Popen to make it non-blocking so the reasoning loop continues
            subprocess.Popen(["say", "-v", "Tessa", text])
            
        except Exception as e:
            print(f"Native Speech Error: {e}")
            print(f"Speech (Simulated): {text}")
