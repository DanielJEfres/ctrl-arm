from google.adk import Agent
from google.adk.tools import FunctionTool
import os
import sys

# Add the gesture_mapping_agent directory to path for importing key_mapper
_agent_dir = os.path.dirname(__file__)
if _agent_dir not in sys.path:
    sys.path.append(_agent_dir)

from key_mapper import GestureKeyMapper

_mapper = GestureKeyMapper()


def set_mode(mode: str) -> str:
    if _mapper.set_current_keys_from_mode(mode):
        _mapper.save_config()
        return f"Mode set to {mode}. Current keys updated."
    return f"Unknown mode: {mode}"


def set_key(gesture: str, key: str) -> str:
    if _mapper.update_gesture_key(gesture, key):
        _mapper.save_config()
        return f"Updated {gesture} -> {key}"
    return f"Unknown gesture: {gesture}"


def get_current_keys() -> dict:
    return _mapper.config.get('current_keys', {})


def suggest_mode_for_app(app_name: str) -> str:
    return _mapper.select_mode_for_app(app_name)


set_mode_tool = FunctionTool(set_mode)
set_key_tool = FunctionTool(set_key)
get_keys_tool = FunctionTool(get_current_keys)
suggest_mode_tool = FunctionTool(suggest_mode_for_app)

root_agent = Agent(
    name="gesture_mapping_agent",
    model="gemini-2.5-flash",
    tools=[set_mode_tool, set_key_tool, get_keys_tool, suggest_mode_tool],
)


