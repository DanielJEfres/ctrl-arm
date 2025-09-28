from google.adk import Agent
from google.adk.tools import FunctionTool
import subprocess
import sys
import os
import threading
import queue
import time
import json
import re
from datetime import datetime
from dotenv import load_dotenv

_ADK_DIR = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_ADK_DIR, ".."))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

try:
    from gesture_mapping_agent.key_mapper import GestureKeyMapper
    _CONFIG_HINT = os.getenv("CTRLARM_CONFIG") or os.path.join(_PROJECT_ROOT, "config.yaml")
    _CONFIG_HINT = os.path.abspath(_CONFIG_HINT)
    print(f"[voice_console_agent] Using config: {_CONFIG_HINT}")
    _gesture_mapper = GestureKeyMapper(config_path=_CONFIG_HINT)
except Exception as e:
    print(f"[voice_console_agent] Warning: Could not load gesture mapper: {e}")
    _gesture_mapper = None

_detect_queue: "queue.Queue[str]" = queue.Queue()
_watch_proc: subprocess.Popen | None = None
_watch_thread: threading.Thread | None = None
_consumer_thread: threading.Thread | None = None
_is_watching: bool = False

WAKE_WORD = "gemini"
_listen_for_command: bool = False

def _enqueue_detected(line: str) -> None:
    text = (line or "").strip()
    if not text.startswith("Detected:"):
        return
    payload = text[len("Detected:"):].strip()
    if payload.startswith("'") and payload.endswith("'") and len(payload) >= 2:
        payload = payload[1:-1]
    if payload:
        _detect_queue.put(payload)
        print(f"[voice_console_agent] queued: {payload}")
        sys.stdout.flush()

def _watch_stdout(proc: subprocess.Popen) -> None:
    global _is_watching
    try:
        for raw in iter(proc.stdout.readline, ''):
            if not _is_watching:
                break
            if not raw:
                time.sleep(0.01)
                continue
            _enqueue_detected(raw)
    except Exception as e:
        print(f"[voice_console_agent] watcher error: {e}")
    finally:
        _is_watching = False

def _consume_and_act():
    global _listen_for_command
    print("[voice_console_agent] Consumer running (voice → intent → action)")
    sys.stdout.flush()

    while _is_watching:
        try:
            utter = _detect_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if not utter:
            continue

        text_lc = utter.strip().lower()

        if not _listen_for_command:
            clean = re.sub(r"[^\w]", "", text_lc)
            if (WAKE_WORD in text_lc) or (WAKE_WORD in clean):
                print("[voice_console_agent] Wake word detected. Say your command…")
                sys.stdout.flush()
                _listen_for_command = True
            else:
                continue
        else:
            print(f"[voice_console_agent] Command: {utter}")
            sys.stdout.flush()
            try:
                result = process_voice_command(utter)
                print(f"[voice_console_agent] Result: {result}")
            except Exception as e:
                print(f"[voice_console_agent] Error executing command: {e}")
            finally:
                _listen_for_command = False
                print("[voice_console_agent] Listening for 'Gemini'…")
                sys.stdout.flush()

def start_watching() -> str:
    global _watch_proc, _watch_thread, _consumer_thread, _is_watching
    if _is_watching and _watch_proc and _watch_proc.poll() is None:
        return "Already watching voice output."

    script_path = os.path.join(_ADK_DIR, "console_runner.py")
    if not os.path.exists(script_path):
        return f"Voice script not found at {script_path}"

    try:
        _watch_proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        _is_watching = True
        _watch_thread = threading.Thread(target=_watch_stdout, args=(_watch_proc,), daemon=True)
        _watch_thread.start()
        _consumer_thread = threading.Thread(target=_consume_and_act, daemon=True)
        _consumer_thread.start()
        return "Started voice detection. Say 'Gemini' then your command."
    except Exception as e:
        _is_watching = False
        return f"Failed to start watcher: {e}"

def stop_watching() -> str:
    global _watch_proc, _is_watching
    _is_watching = False
    if _watch_proc:
        try:
            _watch_proc.terminate()
            _watch_proc.wait(timeout=5)
            return "Stopped watching."
        except Exception:
            try:
                _watch_proc.kill()
                return "Force-stopped watching."
            except Exception as e:
                return f"Failed to stop watcher: {e}"
    return "Watcher was not running."

def next_detected(timeout: int = 10) -> str:
    try:
        return _detect_queue.get(timeout=timeout)
    except queue.Empty:
        return "(no detected speech within timeout)"

def ask_gemini(prompt: str) -> str:
    return f"User said: {prompt}"

def respond_to_next_detected(timeout: int = 15) -> str:
    try:
        utterance = _detect_queue.get(timeout=timeout)
        return f"Voice input: {utterance}\nPlease provide a concise, helpful response."
    except queue.Empty:
        return "(no detected speech within timeout)"

def listen_and_respond(timeout: int = 20) -> str:
    status = []
    if not (_is_watching and _watch_proc and _watch_proc.poll() is None):
        status_msg = start_watching()
        status.append(status_msg)
    resp = respond_to_next_detected(timeout=timeout)
    if status:
        return "\n".join(status + [resp])
    return resp

def process_voice_command(utterance: str) -> str:
    cmd = utterance.lower().strip()
    cmd = re.sub(r"[^\w\s]", "", cmd)

    mode_patterns = [
        r"(?:set|switch|change)\s+(?:the\s+)?mode\s+(?:to\s+)?([a-z0-9_]+)",
        r"(?:set|switch|change)\s+(?:to\s+)?([a-z0-9_]+)\s+mode",
        r"(?:set|switch|change)\s+(?:the\s+)?([a-z0-9_]+)\s+mode",
        r"(?:set|switch|change)\s+(?:to\s+)?([a-z0-9_]+)$",
        r"(?:set|switch|change)\s+(?:the\s+)?([a-z0-9_]+)",
    ]
    for pat in mode_patterns:
        m = re.search(pat, cmd)
        if m:
            mode = m.group(1)
            if not mode.endswith("_mode"):
                mode = f"{mode}_mode"
            return gesture_set_mode(mode)

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
        "right hard": "right_hard",
    }
    for phrase, gesture in gesture_phrases.items():
        if re.search(rf"(?:change|set|map)\s+{re.escape(phrase)}\s+to\s+", cmd):
            key = cmd.split(" to ")[-1].strip().replace(" key", "").replace("key", "")
            return gesture_set_key(gesture, key)

    if ("current keys" in cmd) or ("show keys" in cmd):
        return gesture_get_current_keys()
    if "time" in cmd:
        return get_time()
    if "weather" in cmd:
        loc = "local"
        if " in " in cmd:
            loc = cmd.split(" in ")[-1].strip()
        return get_weather(loc)

    return f"Voice command received (no action matched): {utterance}"

def gesture_set_mode(mode: str) -> str:
    if not _gesture_mapper:
        return "Gesture mapper not available"
    
    if _gesture_mapper.set_current_keys_from_mode(mode):
        _gesture_mapper.save_config()
        return f"Mode set to {mode}. Current keys updated."
    available_modes = _gesture_mapper.get_available_modes()
    return f"Unknown mode: {mode}. Available modes: {', '.join(available_modes)}"

def gesture_set_key(gesture: str, key: str) -> str:
    if not _gesture_mapper:
        return "Gesture mapper not available"
    if _gesture_mapper.update_gesture_key(gesture, key):
        _gesture_mapper.save_config()
        return f"Updated {gesture} -> {key}"
    available = _gesture_mapper.config.get("gesture_labels", [])
    return f"Unknown gesture: {gesture}. Available gestures: {', '.join(available)}"

def gesture_get_current_keys() -> str:
    if not _gesture_mapper:
        return "Gesture mapper not available"
    keys = _gesture_mapper.config.get("current_keys", {})
    if not keys:
        return "No current key mappings set."
    lines = ["Current gesture key mappings:"]
    for gesture, key in keys.items():
        if key:
            lines.append(f"  {gesture}: {key}")
    return "\n".join(lines)

def gesture_suggest_mode_for_app(app_name: str) -> str:
    if not _gesture_mapper:
        return "Gesture mapper not available"
    mode = _gesture_mapper.select_mode_for_app(app_name)
    return f"Suggested mode for '{app_name}': {mode}"

def get_weather(location: str) -> str:
    return f"The current weather in {location} is sunny and 72°F"

def get_time(location: str = "local") -> str:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"The current time in {location} is {current_time}"

def process_emg_signal(signal_data: str, sampling_rate: int = 1000) -> str:
    try:
        data = [float(x.strip()) for x in signal_data.split(",")]
        rms = (sum(x**2 for x in data) / max(1, len(data))) ** 0.5
        features = {"rms": round(rms, 4), "signal_length": len(data), "sampling_rate": sampling_rate}
        return f"EMG signal processed: {json.dumps(features)}"
    except Exception as e:
        return f"Error processing EMG signal: {str(e)}"

def recognize_gesture(emg_rms: float, motion_intensity: float = 0.0) -> str:
    if emg_rms > 0.4 and motion_intensity > 2.0:
        gesture, confidence = "strong_grip", 0.85
    elif emg_rms > 0.2:
        gesture, confidence = "point", 0.75
    else:
        gesture, confidence = "rest", 0.60
    return f"Gesture: {gesture} (confidence: {confidence})"

start_tool             = FunctionTool(start_watching)
stop_tool              = FunctionTool(stop_watching)
next_tool              = FunctionTool(next_detected)
ask_tool               = FunctionTool(ask_gemini)
respond_tool           = FunctionTool(respond_to_next_detected)
listen_tool            = FunctionTool(listen_and_respond)

gesture_mode_tool      = FunctionTool(gesture_set_mode)
gesture_key_tool       = FunctionTool(gesture_set_key)
gesture_keys_tool      = FunctionTool(gesture_get_current_keys)
gesture_suggest_tool   = FunctionTool(gesture_suggest_mode_for_app)

weather_tool           = FunctionTool(get_weather)
time_tool              = FunctionTool(get_time)
emg_tool               = FunctionTool(process_emg_signal)
gesture_recognize_tool = FunctionTool(recognize_gesture)

voice_process_tool     = FunctionTool(process_voice_command)

root_agent = Agent(
    name="voice_console_agent",
    model="gemini-2.5-flash",
    tools=[
        start_tool, stop_tool, next_tool, ask_tool, respond_tool, listen_tool, voice_process_tool,
        gesture_mode_tool, gesture_key_tool, gesture_keys_tool, gesture_suggest_tool,
        weather_tool, time_tool, emg_tool, gesture_recognize_tool,
    ],
)

try:
    print("[voice_console_agent] Starting voice detection...")
    
    advanced_listener_path = os.path.join(os.path.dirname(__file__), 'advanced_voice_listener.py')
    if os.path.exists(advanced_listener_path):
        print("[voice_console_agent] Using advanced voice listener")
        print("[voice_console_agent] Say 'Gemini, your command' in one phrase for instant response")
        
        import threading
        import sys
        current_dir = os.path.dirname(__file__)
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from advanced_voice_listener import listen_and_execute, process_gesture_command
        
        def custom_process_command(command):
            print(f"[voice_console_agent] Processing: {command}")
            result = process_voice_command(command)
            print(f"[voice_console_agent] Result: {result}")
            return result
        
        import advanced_voice_listener
        advanced_voice_listener.process_gesture_command = custom_process_command
        
        voice_thread = threading.Thread(target=listen_and_execute, daemon=True)
        voice_thread.start()
        print("[voice_console_agent] Voice listener started")
        
    else:
        print("[voice_console_agent] Using fallback voice system")
        start_result = start_watching()
        print(f"[voice_console_agent] {start_result}")
        
except Exception as e:
    print(f"[voice_console_agent] Could not start advanced voice: {e}")
    print("[voice_console_agent] Falling back to old system")
    try:
        start_result = start_watching()
        print(f"[voice_console_agent] {start_result}")
    except Exception as e2:
        print(f"[voice_console_agent] Fallback failed: {e2}")

def run_standalone_voice_mode():
    print("[voice_console_agent] Standalone voice mode. Press Ctrl+C to exit.")
    print("[voice_console_agent] Listening for 'Gemini'")
    sys.stdout.flush()
    try:
        while True:
            try:
                utterance = next_detected(timeout=10)
                if utterance and not utterance.startswith("("):
                    global _listen_for_command
                    low = utterance.lower()
                    if (WAKE_WORD in low) or (WAKE_WORD in re.sub(r"[^\w]", "", low)):
                        print("[voice_console_agent] Wake word detected. Say your command")
                        _listen_for_command = True
                    elif _listen_for_command:
                        print(f"[voice_console_agent] Command: {utterance}")
                        result = process_voice_command(utterance)
                        print(f"[voice_console_agent] Result: {result}")
                        _listen_for_command = False
                        print("[voice_console_agent] Listening for 'Gemini'")
            except KeyboardInterrupt:
                print("\n[voice_console_agent] Exiting")
                break
            except Exception as e:
                print(f"[voice_console_agent] Voice processing error: {e}")
            time.sleep(0.05)
    finally:
        print("[voice_console_agent] Stopping voice detection")
        stop_watching()

if __name__ == "__main__" or "--standalone" in sys.argv:
    if _is_watching:
        run_standalone_voice_mode()
