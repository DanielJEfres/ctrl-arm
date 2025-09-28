#!/usr/bin/env python3
from google.adk import Agent
from google.adk.tools import FunctionTool
import os, sys, time, threading, subprocess, platform, shlex, re, json
from typing import Optional, Tuple, Dict

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
_DEBUG = os.getenv("CONTEXT_DEBUG", "0") == "1"

def _safe_load_yaml(path: str) -> dict:
    data = {}
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except ModuleNotFoundError:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}

def _load_app_mode_mapping() -> Dict[str, str]:
    cfg_path = os.getenv("CTRLARM_CONFIG") or os.path.join(_PROJECT_ROOT, "config.yaml")
    cfg = _safe_load_yaml(cfg_path)
    mapping = cfg.get("app_mode_mapping") or {}
    norm: Dict[str, str] = {}
    for k, v in mapping.items():
        if isinstance(k, str) and isinstance(v, str):
            norm[k] = v
            norm[k.lower()] = v
    return norm

_APP_MODE_MAP = _load_app_mode_mapping()
_ALLOWED_MODES = {"work_mode", "game_mode", "creative_mode", "default_mode"}

def _mac_front_app() -> Tuple[Optional[str], Optional[str]]:
    try:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is not None:
            name = str(app.localizedName() or "") or None
            bid  = str(app.bundleIdentifier() or "") or None
            if name or bid:
                return name, bid
    except Exception as e:
        if _DEBUG:
            print(f"[context_agent] PyObjC path failed: {e}", file=sys.stderr)
    try:
        name = subprocess.check_output(
            ["/usr/bin/osascript", "-e",
             'tell application "System Events" to get name of first application process whose frontmost is true'],
            text=True
        ).strip() or None
        bid = None
        if name:
            try:
                bid = subprocess.check_output(
                    ["/usr/bin/osascript", "-e", f'id of app "{name}"'],
                    text=True
                ).strip() or None
            except Exception as e2:
                if _DEBUG:
                    print(f"[context_agent] AppleScript id lookup failed: {e2}", file=sys.stderr)
                bid = None
        if name or bid:
            return name, bid
    except Exception as e1:
        if _DEBUG:
            print(f"[context_agent] AppleScript path failed: {e1}", file=sys.stderr)
    try:
        asn = subprocess.check_output(["/usr/bin/lsappinfo", "front"], text=True).strip()
        bid = None
        if ":" in asn:
            parts = asn.split(":")
            bid = parts[-1] if parts else None
        name = None
        if bid:
            try:
                name = subprocess.check_output(
                    ["/usr/bin/osascript", "-e", f'tell application id "{bid}" to name'],
                    text=True
                ).strip() or None
            except Exception:
                name = None
        return name, bid
    except Exception as e3:
        if _DEBUG:
            print(f"[context_agent] lsappinfo path failed: {e3}", file=sys.stderr)
    return None, None

def _win_front_app() -> Tuple[Optional[str], Optional[str]]:
    try:
        import win32gui, win32process, psutil
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None, None
        title = win32gui.GetWindowText(hwnd) or None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = None
        if pid:
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
            except Exception:
                pass
        return title, proc_name
    except Exception as e:
        if _DEBUG:
            print(f"[context_agent] Windows front app failed: {e}", file=sys.stderr)
        return None, None

def _linux_front_app() -> Tuple[Optional[str], Optional[str]]:
    try:
        win_id = subprocess.check_output(shlex.split("xdotool getactivewindow"), text=True).strip()
        out = subprocess.check_output(shlex.split("wmctrl -l -x"), text=True, stderr=subprocess.DEVNULL)
        title, klass = None, None
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 5:
                wid_hex, _, _, wmclass, wtitle = parts[0], parts[1], parts[2], parts[2], parts[4]
                try:
                    if int(wid_hex, 16) == int(win_id):
                        title = wtitle.strip() if wtitle else None
                        klass = wmclass.strip() if wmclass else None
                        return title, klass
                except Exception:
                    pass
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 5:
                wtitle = parts[4]
                if wtitle and wtitle.strip():
                    if not title or len(wtitle) > len(title):
                        title = wtitle.strip()
                        klass = parts[2].strip()
        return title, klass
    except Exception as e:
        if _DEBUG:
            print(f"[context_agent] Linux front app primary failed: {e}", file=sys.stderr)
        try:
            out = subprocess.check_output(shlex.split("wmctrl -lx"), text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    return parts[4].strip(), parts[2].strip()
        except Exception as e2:
            if _DEBUG:
                print(f"[context_agent] Linux fallback failed: {e2}", file=sys.stderr)
        return None, None

def get_foreground_app() -> Tuple[Optional[str], Optional[str]]:
    if _OS == "darwin":
        return _mac_front_app()
    if _OS == "windows":
        return _win_front_app()
    return _linux_front_app()

_genai_model_name = os.getenv("GEMINI_CLASSIFIER_MODEL", "gemini-1.5-flash")
_gemini_ready = False
_app_mode_cache: Dict[str, str] = {}

def _ensure_gemini() -> bool:
    global _gemini_ready
    if _gemini_ready:
        return True
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        if _DEBUG:
            print("[context_agent] No GOOGLE_API_KEY/GEMINI_API_KEY in environment", file=sys.stderr)
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _ = genai.GenerativeModel(_genai_model_name)
        _gemini_ready = True
        return True
    except Exception as e:
        print(f"[context_agent] Gemini init failed: {e}", file=sys.stderr)
        return False

def _llm_guess_mode(app_name: Optional[str], bundle_or_ident: Optional[str]) -> Optional[str]:
    if not app_name:
        return None
    key = app_name.lower()
    if key in _app_mode_cache:
        return _app_mode_cache[key]
    if not _ensure_gemini():
        return None
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel(_genai_model_name)
        prompt = (
            "You are a strict classifier. Pick ONE label for the application below.\n"
            "Allowed labels (exactly one): work_mode, game_mode, creative_mode, default_mode.\n\n"
            f"App name: {app_name}\n"
            f"Identifier (optional): {bundle_or_ident or 'unknown'}\n\n"
            "Answer with ONLY the label, nothing else."
        )
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip().lower()
        for tok in _ALLOWED_MODES:
            if tok in text:
                _app_mode_cache[key] = tok
                return tok
        cleaned = text.replace(" ", "_")
        if cleaned in _ALLOWED_MODES:
            _app_mode_cache[key] = cleaned
            return cleaned
        return None
    except Exception as e:
        if _DEBUG:
            print(f"[context_agent] Gemini classify failed: {e}", file=sys.stderr)
        return None

def _heuristic_guess_mode(app_name: str, ident: Optional[str]) -> Optional[str]:
    n = app_name.lower()
    if any(k in n for k in ["code", "vscode", "xcode", "cursor", "intellij", "pycharm", "webstorm", "rider"]):
        return "work_mode"
    if any(k in n for k in ["unity", "unreal", "steam", "epic games"]):
        return "game_mode"
    if any(k in n for k in ["blender", "photoshop", "illustrator", "figma", "after effects", "premiere"]):
        return "creative_mode"
    if any(k in n for k in ["chrome", "safari", "firefox", "arc", "edge"]):
        return "default_mode"
    return None

def resolve_mode_for_app(name: Optional[str], ident: Optional[str]) -> str:
    if not name:
        return "default_mode"
    m = _APP_MODE_MAP.get(name) or _APP_MODE_MAP.get(name.lower())
    if isinstance(m, str) and m in _ALLOWED_MODES:
        return m
    mode = _llm_guess_mode(name, ident)
    if isinstance(mode, str) and mode in _ALLOWED_MODES:
        return mode
    if _mapper is not None:
        try:
            m2 = _mapper.select_mode_for_app(name)
            if isinstance(m2, str) and m2 in _ALLOWED_MODES:
                return m2
        except Exception:
            pass
    h = _heuristic_guess_mode(name, ident)
    if h:
        return h
    return "default_mode"

def _apply_mode(mode: str) -> bool:
    if _mapper is None:
        print(f"[context_agent] Mapper unavailable; cannot switch to {mode}")
        return False
    try:
        _mapper.set_current_keys_from_mode(mode)
        _mapper.save_config()
        return True
    except Exception as e:
        print(f"[context_agent] Error applying mode {mode}: {e}")
        return False

_watch_thread: Optional[threading.Thread] = None
_watch_running = False
_current: Tuple[Optional[str], Optional[str]] = (None, None)
_lock = threading.Lock()

def _watch_loop(poll_ms: int = 500, heartbeat_s: Optional[float] = 5.0):
    global _current
    print("[context_agent] Context watcher running…")
    prev = (None, None)
    last_beat = 0.0
    name, ident = get_foreground_app()
    with _lock:
        _current = (name, ident)
    mode = resolve_mode_for_app(name, ident)
    switched = _apply_mode(mode)
    print(f"[context_agent] Active → {name or 'None'} ({ident or 'unknown'}) ⇒ {mode}{' (keys updated)' if switched else ''}")
    sys.stdout.flush()
    prev = (name, ident)
    last_beat = time.time()
    while _watch_running:
        name, ident = get_foreground_app()
        with _lock:
            _current = (name, ident)
        changed = (name, ident) != prev
        beat_due = heartbeat_s is not None and (time.time() - last_beat) >= max(0.5, heartbeat_s)
        if changed or beat_due:
            mode = resolve_mode_for_app(name, ident)
            switched = _apply_mode(mode) if changed else False
            print(f"[context_agent] Active → {name or 'None'} ({ident or 'unknown'}) ⇒ {mode}{' (keys updated)' if switched else ''}")
            sys.stdout.flush()
            prev = (name, ident)
            if beat_due:
                last_beat = time.time()
        time.sleep(max(0.05, poll_ms / 1000.0))
    print("[context_agent] Context watcher stopped.")

def start_context_watcher(poll_ms: int = 500, heartbeat_s: Optional[float] = 5.0) -> str:
    global _watch_thread, _watch_running
    if _watch_running:
        return "Context watcher already running."
    _watch_running = True
    _watch_thread = threading.Thread(
        target=_watch_loop, kwargs={"poll_ms": poll_ms, "heartbeat_s": heartbeat_s}, daemon=True
    )
    _watch_thread.start()
    return f"Context watcher started (poll={poll_ms}ms, heartbeat={heartbeat_s or 'off'})."

def stop_context_watcher() -> str:
    global _watch_running
    if not _watch_running:
        return "Context watcher not running."
    _watch_running = False
    return "Stopping context watcher…"

def get_current_app() -> dict:
    with _lock:
        name, ident = _current
    return {"name": name, "id": ident}

def await_context_change(timeout_s: float = 10.0) -> dict:
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
    if _mapper is None:
        return "Mapper unavailable; cannot suggest a mode."
    with _lock:
        name, _ = _current
    if not name:
        return "No active app detected yet."
    mode = resolve_mode_for_app(name, None)
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

def _autostart():
    try:
        print("[context_agent] Auto-starting context watcher…")
        msg = start_context_watcher(poll_ms=300, heartbeat_s=3.0)
        print(msg)
        sys.stdout.flush()
    except Exception as e:
        print(f"[context_agent] Could not auto-start watcher: {e}")
        sys.stdout.flush()

if os.getenv("CTX_AUTOSTART", "1") == "1":
    _autostart()

if __name__ == "__main__":
    if not _watch_running:
        _autostart()
