from google.adk import Agent
from google.adk.tools import FunctionTool
import json
from datetime import datetime


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


# Create tools
weather_tool = FunctionTool(get_weather)
time_tool = FunctionTool(get_time)
emg_tool = FunctionTool(process_emg_signal)
gesture_tool = FunctionTool(recognize_gesture)

root_agent = Agent(
    name="multi_tool_agent",
    model="gemini-2.5-flash",
    tools=[weather_tool, time_tool, emg_tool, gesture_tool]
)
