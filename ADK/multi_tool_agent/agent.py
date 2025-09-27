from google.adk import Agent
from google.adk.tools import FunctionTool
import json
from datetime import datetime
import os
import importlib.util


def get_weather(location: str) -> str:
    """Get the current weather for a location"""
    return f"The current weather in {location} is sunny and 72°F"


def get_time(location: str) -> str:
    """Get the current time for a location"""  
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"The current time in {location} is {current_time}"


def process_emg_signal(signal_data: str, sampling_rate: int = 1000) -> str:
    """Process EMG signal and extract features"""
    try:
        data = [float(x.strip()) for x in signal_data.split(',')]
        rms = (sum(x**2 for x in data) / len(data)) ** 0.5
        features = {
            "rms": round(rms, 4),
            "signal_length": len(data),
            "sampling_rate": sampling_rate
        }
        return f"EMG signal processed: {json.dumps(features)}"
    except Exception as e:
        return f"Error processing EMG signal: {str(e)}"


def recognize_gesture(emg_rms: float, motion_intensity: float = 0.0) -> str:
    """Recognize gesture from sensor features"""
    if emg_rms > 0.4 and motion_intensity > 2.0:
        gesture = "strong_grip"
        confidence = 0.85
    elif emg_rms > 0.2:
        gesture = "point" 
        confidence = 0.75
    else:
        gesture = "rest"
        confidence = 0.60
    
    return f"Gesture: {gesture} (confidence: {confidence})"



weather_tool = FunctionTool(get_weather)
time_tool = FunctionTool(get_time)
emg_tool = FunctionTool(process_emg_signal)
gesture_tool = FunctionTool(recognize_gesture)

# base agent (will be recreated below to include voice tools)
root_agent = Agent(
    name="multi_tool_agent",
    model="gemini-2.5-flash",
    tools=[weather_tool, time_tool, emg_tool, gesture_tool]
)


_voice_agent_module = None
_voice_agent_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "voice_console_agent",
    "agent.py",
)


def _load_voice_agent_module():
    global _voice_agent_module
    if _voice_agent_module is not None:
        return _voice_agent_module
    spec = importlib.util.spec_from_file_location(
        "voice_console_agent_agent", _voice_agent_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not create spec for voice_console_agent.agent")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _voice_agent_module = module
    return module


def voice_start_watching() -> str:
    return _load_voice_agent_module().start_watching()


def voice_stop_watching() -> str:
    return _load_voice_agent_module().stop_watching()


def voice_next_detected(timeout: int = 10) -> str:
    return _load_voice_agent_module().next_detected(timeout=timeout)


def voice_ask_gemini(prompt: str) -> str:
    return _load_voice_agent_module().ask_gemini(prompt)


def voice_respond_to_next_detected(timeout: int = 15) -> str:
    return _load_voice_agent_module().respond_to_next_detected(timeout=timeout)


def voice_listen_and_respond(timeout: int = 20) -> str:
    return _load_voice_agent_module().listen_and_respond(timeout=timeout)


voice_start_tool = FunctionTool(voice_start_watching)
voice_stop_tool = FunctionTool(voice_stop_watching)
voice_next_tool = FunctionTool(voice_next_detected)
voice_ask_tool = FunctionTool(voice_ask_gemini)
voice_respond_tool = FunctionTool(voice_respond_to_next_detected)
voice_listen_tool = FunctionTool(voice_listen_and_respond)

root_agent = Agent(
    name="multi_tool_agent",
    model="gemini-2.5-flash",
    tools=[
        weather_tool,
        time_tool,
        emg_tool,
        gesture_tool,
        voice_start_tool,
        voice_stop_tool,
        voice_next_tool,
        voice_ask_tool,
        voice_respond_tool,
        voice_listen_tool,
    ],
)
