from voice.voice_detection import start_voice_detection
import time

print("Starting voice detection...")
start_voice_detection()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Voice detection stopped")