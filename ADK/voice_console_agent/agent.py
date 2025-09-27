from google.adk import Agent
from google.adk.tools import FunctionTool
import subprocess
import sys
import os
import threading
import queue
import time


_detect_queue: "queue.Queue[str]" = queue.Queue()
_watch_proc: subprocess.Popen | None = None
_watch_thread: threading.Thread | None = None
_is_watching: bool = False


def _enqueue_detected(line: str) -> None:
    text = line.strip()
    if text.startswith("Detected:"):

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
        for raw in iter(proc.stdout.readline, ""):
            if not _is_watching:
                break
            _enqueue_detected(raw)
    except Exception as e:
        print(f"[voice_console_agent] watcher error: {e}")
    finally:
        _is_watching = False


def start_watching() -> str:
    """Start the voice console runner and watch for Detected: lines."""
    global _watch_proc, _watch_thread, _is_watching
    if _is_watching and _watch_proc and _watch_proc.poll() is None:
        return "Already watching voice output."

    script_path = os.path.join(os.path.dirname(__file__), "console_runner.py")
    if not os.path.exists(script_path):
        return f"Voice script not found at {script_path}"

    try:
        _watch_proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        _is_watching = True
        _watch_thread = threading.Thread(target=_watch_stdout, args=(_watch_proc,), daemon=True)
        _watch_thread.start()
        return "Started voice detection with wake word 'Gemini'. Say 'Gemini' to activate, then speak your command."
    except Exception as e:
        _is_watching = False
        return f"Failed to start watcher: {e}"


def stop_watching() -> str:
    """Stop the watcher and underlying process."""
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
    """Return next detected text from console, waiting up to timeout seconds."""
    try:
        text = _detect_queue.get(timeout=timeout)
        return text
    except queue.Empty:
        return "(no detected speech within timeout)"


def ask_gemini(prompt: str) -> str:
    """Pass text to Gemini and return response. Placeholder uses tool-less flow."""
    return f"User said: {prompt}"


def respond_to_next_detected(timeout: int = 15) -> str:
    """Wait for next detected utterance, then prompt Gemini to answer helpfully."""
    try:
        utterance = _detect_queue.get(timeout=timeout)
        return (
            f"Voice input: {utterance}\n"
            f"Please provide a concise, helpful response."
        )
    except queue.Empty:
        return "(no detected speech within timeout)"


def listen_and_respond(timeout: int = 20) -> str:
    """Ensure watcher is running, then wait for next detected and prompt Gemini.

    This lets you do everything in a single terminal session.
    """
    status = []
    if not (_is_watching and _watch_proc and _watch_proc.poll() is None):
        status_msg = start_watching()
        status.append(status_msg)
    resp = respond_to_next_detected(timeout=timeout)
    if status:
        return "\n".join(status + [resp])
    return resp


start_tool = FunctionTool(start_watching)
stop_tool = FunctionTool(stop_watching)
next_tool = FunctionTool(next_detected)
ask_tool = FunctionTool(ask_gemini)
respond_tool = FunctionTool(respond_to_next_detected)
listen_tool = FunctionTool(listen_and_respond)

root_agent = Agent(
    name="voice_console_agent",
    model="gemini-2.5-flash",
    tools=[start_tool, stop_tool, next_tool, ask_tool, respond_tool, listen_tool],
)
