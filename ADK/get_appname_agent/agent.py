from google.adk import Agent
from google.adk.tools import FunctionTool

import os, sys, time, threading, subprocess, platform, shlex
from typing import Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

try:
    from gesture_mapping_agent.key_mapper import GestureKeyMapper
    _CONFIG_HINT = os.getenv("CTRLARM_CONFIG") or os.path.join(_PROJECT_ROOT, "config.yaml")
    _mapper = GestureKeyMapper(config_path=os.path.abspath(_CONFIG_HINT))
except Exception as e:
    print(f"[context_agent] Warning: GestureKeyMapper unavailable: {e}")
    _mapper = None


_OS = platform.system().lower()

def _mac_front_app() -> Tuple[Optional[str], Optional[str]]:
    try:
        from AppKit import NSWorkspace  # PyObjC
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None, None
        name = str(app.localizedName() or "") or None
        bid = str(app.bundleIdentifier() or "") or None
        return name, bid
    except Exception as e:
        return None, None

def _win_front_app() -> Tuple[Optional[str], Optional[str]]:
    try:
        import win32gui, win32process, psutil  # pywin32 + psutil
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None, None
        title = win32gui.GetWindowText(hwnd) or None
        tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = None
        if pid:
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
            except Exception:
                pass
        return title, proc_name
    except Exception:
        return None, None

def _linux_front_app() -> Tuple[Optional[str], Optional[str]]:
    try:
        win_id = subprocess.check_output(shlex.split("xdotool getactivewindow"), text=True).strip()
        out = subprocess.check_output(shlex.split("wmctrl -l -x"), text=True, stderr=subprocess.DEVNULL)
        title, klass = None, None
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 5:
                wid_hex, _, _, wmclass, wtitle = parts[0], parts[2], parts[3], parts[3], parts[4]
                if wtitle and win_id and wtitle.strip():
                    if not title or len(wtitle) > len(title):
                        title = wtitle.strip()
                        klass = wmclass.strip()
        return title, klass
    except Exception:
        try:
            out = subprocess.check_output(shlex.split("wmctrl -lx"), text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                if " * " in line or "  -1 " in line:  # not reliable across WMs; best-effort
                    parts = line.split(None, 4)
                    if len(parts) >= 5:
                        return parts[4].strip(), parts[3].strip()
        except Exception:
            pass
        return None, None

def get_foreground_app() -> Tuple[Optional[str], Optional[str]]:
    if _OS == "darwin":
        return _mac_front_app()
    if _OS == "windows":
        return _win_front_app()
    return _linux_front_app()


_watch_thread: Optional[threading.Thread] = None
_watch_running = False
_current: Tuple[Optional[str], Optional[str]] = (None, None)
_lock = threading.Lock()

def _watch_loop(poll_ms: int = 500):
    global _current
    print("[context_agent] Context watcher running…")
    prev = (None, None)
    while _watch_running:
        name, ident = get_foreground_app()
        with _lock:
            _current = (name, ident)
        if (name, ident) != prev and name:
            print(f"[context_agent] Active → {name} ({ident or 'unknown'})")
            sys.stdout.flush()
            prev = (name, ident)
        time.sleep(max(0.05, poll_ms / 1000.0))
    print("[context_agent] Context watcher stopped.")


def start_context_watcher(poll_ms: int = 500) -> str:
    """
    Start background watcher that tracks the foreground application.
    poll_ms: polling interval in milliseconds (default: 500)
    """
    global _watch_thread, _watch_running
    if _watch_running:
        return "Context watcher already running."
    _watch_running = True
    _watch_thread = threading.Thread(target=_watch_loop, kwargs={"poll_ms": poll_ms}, daemon=True)
    _watch_thread.start()
    return f"Context watcher started (poll={poll_ms}ms)."

def stop_context_watcher() -> str:
    """Stop background watcher."""
    global _watch_running
    if not _watch_running:
        return "Context watcher not running."
    _watch_running = False
    return "Stopping context watcher…"

def get_current_app() -> dict:
    """
    Return the most recently observed foreground app.
    For macOS: {'name': app_name, 'id': bundle_id}
    For Windows: {'name': window_title, 'id': process_name}
    For Linux: {'name': window_title, 'id': wm_class}
    """
    with _lock:
        name, ident = _current
    return {"name": name, "id": ident}

def await_context_change(timeout_s: float = 10.0) -> dict:
    """
    Block until the foreground app changes (or timeout).
    Returns {'changed': bool, 'name': str|None, 'id': str|None}
    """
    deadline = time.time() + max(0.1, timeout_s)
    with _lock:
        start = _current
    while time.time() < deadline:
        time.sleep(0.1)
        with _lock:
            now = _current
        if now != start and any(now):
            return {"changed": True, "name": now[0], "id": now[1]}
    with _lock:
        name, ident = _current
    return {"changed": False, "name": name, "id": ident}

def suggest_mode_for_current_app() -> str:
    """
    Uses GestureKeyMapper.select_mode_for_app(app_name) to propose a mode.
    """
    if _mapper is None:
        return "Mapper unavailable; cannot suggest a mode."
    with _lock:
        name, _ = _current
    if not name:
        return "No active app detected yet."
    mode = _mapper.select_mode_for_app(name)
    return f"Suggested mode for '{name}': {mode}"


start_tool   = FunctionTool(start_context_watcher)
stop_tool    = FunctionTool(stop_context_watcher)
get_tool     = FunctionTool(get_current_app)
await_tool   = FunctionTool(await_context_change)
suggest_tool = FunctionTool(suggest_mode_for_current_app)

root_agent = Agent(
    name="context_agent",
    model="gemini-2.5-flash",   
    tools=[start_tool, stop_tool, get_tool, await_tool, suggest_tool],
)

try:
    print("[context_agent] Auto-starting context watcher…")
    print(start_context_watcher())
except Exception as e:
    print(f"[context_agent] Could not auto-start watcher: {e}")
