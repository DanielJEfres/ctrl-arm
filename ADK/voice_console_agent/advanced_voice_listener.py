#!/usr/bin/env python3

import speech_recognition as sr
import time
import sys
import os
import requests
import json

_ADK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ADK_ROOT not in sys.path:
    sys.path.append(_ADK_ROOT)

try:
    from gesture_mapping_agent.key_mapper import GestureKeyMapper
    gesture_mapper = GestureKeyMapper()
    print("[advanced_voice_listener] Gesture mapper loaded successfully")
except Exception as e:
    print(f"[advanced_voice_listener] Could not load gesture mapper: {e}")
    gesture_mapper = None

_voice_status = "Waiting"
_should_exit = False

def send_voice_data(text: str, response: str = None):
    """Send voice data to the Electron app via HTTP"""
    try:
        data = {
            "text": text,
            "response": response,
            "timestamp": time.time(),
            "status": "detected" if response is None else "response"
        }
        
        response_obj = requests.post(
            "http://localhost:3000/api/voice-data",
            json=data,
            timeout=2
        )
        
        if response_obj.status_code == 200:
            print(f"[advanced_voice_listener] Voice data sent successfully")
        else:
            print(f"[advanced_voice_listener] Failed to send voice data: {response_obj.status_code}")
            
    except Exception as e:
        print(f"[advanced_voice_listener] Error sending voice data: {e}")

def send_voice_status(status: str, message: str):
    """Send voice status to the Electron app via HTTP"""
    try:
        data = {
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        
        response_obj = requests.post(
            "http://localhost:3000/api/voice-status",
            json=data,
            timeout=2
        )
        
        if response_obj.status_code == 200:
            print(f"[advanced_voice_listener] Voice status sent successfully")
        else:
            print(f"[advanced_voice_listener] Failed to send voice status: {response_obj.status_code}")
            
    except Exception as e:
        print(f"[advanced_voice_listener] Error sending voice status: {e}")

def set_voice_status(status):
    global _voice_status
    _voice_status = status
    print(f"[Status] {status}")
    
    if "Listening" in status:
        send_voice_status("listening", status)
    elif "Processing" in status:
        send_voice_status("processing", status)
    elif "Wake word detected" in status:
        send_voice_status("activated", status)
    elif "Error" in status or "error" in status:
        send_voice_status("error", status)
    elif "stopped" in status.lower():
        send_voice_status("stopped", status)
    else:
        send_voice_status("listening", status)

def get_voice_status():
    return _voice_status

def should_exit_app():
    return _should_exit

def normalize_command(command):
    command = command.lower().strip()
    
    gemini_alternatives = [
        "jimmy", "jemini", "jeremy", "germany", "jemon", "jerome", 
        "jamini", "gemeni", "jiminy", "gemmy", "jenny", "jemeni",
        "hello g", "hello j", "hey g", "gemina", "gemini's", "gremlin"
    ]
    
    for alt in gemini_alternatives:
        if alt in command:
            command = command.replace(alt, "gemini")
    
    command = command.replace("first", "single")
    command = command.replace("1st", "single") 
    command = command.replace("second", "double")
    command = command.replace("2nd", "double")
    command = command.replace("press", "single")
    command = command.replace("click", "single")
    
    return command

def process_gesture_command(command):
    if not gesture_mapper:
        return f"Voice command received: {command} (gesture mapper not available)"
    
    print(f"[advanced_voice_listener] Processing command: '{command}'")
    
    if "set mode to" in command or "switch to" in command or "change mode to" in command:
        print(f"[advanced_voice_listener] Mode change command detected")
        
        mode_mappings = {
            "work": "work_mode",
            "game": "game_mode", 
            "creative": "creative_mode",
            "default": "default_mode"
        }
        
        for mode in ["work_mode", "game_mode", "creative_mode", "default_mode"]:
            if mode.replace("_", " ") in command or mode in command:
                print(f"[advanced_voice_listener] Found exact mode: {mode}")
                try:
                    gesture_mapper.set_current_keys_from_mode(mode)
                    gesture_mapper.save_config()
                    print(f"[advanced_voice_listener] Successfully switched to {mode}")
                    return f"Switched to {mode} and updated gesture keys"
                except Exception as e:
                    print(f"[advanced_voice_listener] Error switching to {mode}: {e}")
                    return f"Error switching to {mode}: {e}"
        
        for partial, full_mode in mode_mappings.items():
            if partial in command:
                print(f"[advanced_voice_listener] Found partial mode '{partial}', mapping to {full_mode}")
                try:
                    gesture_mapper.set_current_keys_from_mode(full_mode)
                    gesture_mapper.save_config()
                    print(f"[advanced_voice_listener] Successfully switched to {full_mode}")
                    return f"Switched to {full_mode} and updated gesture keys"
                except Exception as e:
                    print(f"[advanced_voice_listener] Error switching to {full_mode}: {e}")
                    return f"Error switching to {full_mode}: {e}"
    
    print(f"[advanced_voice_listener] No mode change pattern matched")
    
    gesture_phrases = {
        "left single": "left_single",
        "right single": "right_single", 
        "left double": "left_double",
        "right double": "right_double",
        "left hold": "left_hold",
        "right hold": "right_hold",
        "both flex": "both_flex",
        "left then right": "left_then_right",
        "right then left": "right_then_left",
        "left hard": "left_hard",
        "right hard": "right_hard"
    }
    
    for phrase, gesture in gesture_phrases.items():
        if f"change {phrase} to" in command or f"set {phrase} to" in command:
            parts = command.split(" to ")
            if len(parts) > 1:
                key = parts[1].strip().replace(" key", "").replace("key", "")
                try:
                    gesture_mapper.update_gesture_key(gesture, key)
                    gesture_mapper.save_config()
                    return f"Changed {gesture} to {key}"
                except Exception as e:
                    return f"Error changing {gesture} to {key}: {e}"
    
    if "current keys" in command or "show keys" in command:
        try:
            keys = gesture_mapper.get_current_keys()
            return f"Current gesture keys: {keys}"
        except Exception as e:
            return f"Error getting current keys: {e}"
    
    if "time" in command:
        import datetime
        return f"Current time: {datetime.datetime.now().strftime('%H:%M:%S')}"
    
    return f"Voice command received: {command}"

def execute_command(command):
    global _should_exit
    
    command = normalize_command(command)
    set_voice_status(f"Processing: {command}")
    
    send_voice_data(command)
    
    if "stop listening" in command or "exit" in command or "quit" in command:
        set_voice_status("Shutting down voice listener")
        _should_exit = True
        return
    
    result = process_gesture_command(command)
    set_voice_status(result)
    
    send_voice_data(command, result)
    
    time.sleep(1)
    set_voice_status("Listening for 'Gemini'...")

def listen_and_execute():
    global _should_exit
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("[advanced_voice_listener] Adjusting for ambient noise...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print("[advanced_voice_listener] Ready! Say 'Gemini' followed by your command.")
    set_voice_status("Listening for 'Gemini'...")
    
    send_voice_status("listening", "Listening for 'Gemini'...")
    
    wake_word_detected = False
    
    while not _should_exit:
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=8)
            
            try:
                command = recognizer.recognize_google(audio).lower().strip()
                print(f"[advanced_voice_listener] Heard: {command}")
                
                if not wake_word_detected:
                    normalized = normalize_command(command)
                    
                    if "gemini" in normalized:
                        print(f"[advanced_voice_listener] Wake word detected! (heard: '{command}')")
                        
                        words = normalized.split()
                        if len(words) > 1:
                            actual_command = normalized.replace("gemini", "", 1).strip()
                            if actual_command and len(actual_command.split()) > 0:
                                print(f"[advanced_voice_listener] Processing command in same utterance: '{actual_command}'")
                                execute_command(actual_command)
                                continue
                        
                        set_voice_status("Wake word detected - speak your command")
                        wake_word_detected = True
                else:
                    print(f"[advanced_voice_listener] Processing follow-up command: '{command}'")
                    execute_command(command)
                    wake_word_detected = False
                        
            except sr.UnknownValueError:
                if wake_word_detected:
                    set_voice_status("Didn't catch that. Listening for 'Gemini'...")
                    wake_word_detected = False
                pass
                
            except sr.RequestError as e:
                print(f"[advanced_voice_listener] Speech recognition error: {e}")
                set_voice_status("Recognition error - check internet connection")
                time.sleep(2)
                
        except sr.WaitTimeoutError:
            pass
        except KeyboardInterrupt:
            print("\n[advanced_voice_listener] Exiting...")
            break
        except Exception as e:
            print(f"[advanced_voice_listener] Unexpected error: {e}")
            time.sleep(1)
    
    set_voice_status("Voice listener stopped")

def main():
    try:
        listen_and_execute()
    except KeyboardInterrupt:
        print("\n[advanced_voice_listener] Shutting down...")
        set_voice_status("Voice listener stopped")

if __name__ == "__main__":
    main()
