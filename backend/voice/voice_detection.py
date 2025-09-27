import speech_recognition as sr
import time
import threading

def normalize_speech(text):
    text = text.lower().strip()
    return text

def listen_for_speech():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    print("Voice detection started. Listening...")
    
    while True:
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)
            
            detected_text = recognizer.recognize_google(audio)
            normalized_text = normalize_speech(detected_text)
            
            print(f"Detected speech: {normalized_text}")
            
        except sr.UnknownValueError:
            print("Could not understand speech")
        except sr.RequestError as e:
            print(f"Recognition error: {e}")
        
        time.sleep(0.1)

def start_voice_detection():
    voice_thread = threading.Thread(target=listen_for_speech, daemon=True)
    voice_thread.start()
    return voice_thread

if __name__ == "__main__":
    start_voice_detection()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Voice detection stopped")
