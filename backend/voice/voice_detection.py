import speech_recognition as sr
import time
import threading

def normalize_speech(text):
    text = text.lower().strip()
    return text

def test_microphone():
    try:
        mic_list = sr.Microphone.list_microphone_names()
        print(f"Available microphones: {len(mic_list)}")
        for i, name in enumerate(mic_list):
            print(f"  {i}: {name}")
        return len(mic_list) > 0
    except Exception as e:
        print(f"Error checking microphones: {e}")
        return False

def listen_for_speech():
    recognizer = sr.Recognizer()
    
    if not test_microphone():
        print("No microphones found!")
        return
    
    try:
        mic = sr.Microphone()
    except Exception as e:
        print(f"Error initializing microphone: {e}")
        return
    
    print("Voice detection started. Listening...")
    
    try:
        with mic as source:
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Starting detection...")
    except Exception as e:
        print(f"Error during noise adjustment: {e}")
    
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3
    
    while True:
        try:
            with mic as source:
                print("Listening...")
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
            
            try:
                detected_text = recognizer.recognize_google(audio, language='en-US')
                if detected_text:
                    normalized_text = normalize_speech(detected_text)
                    print(f"Detected: '{normalized_text}'")
                    
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Google Speech Recognition error: {e}")
                time.sleep(2)
                
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            print(f"Error in voice detection: {e}")
            time.sleep(1)

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