#!/usr/bin/env python3

import speech_recognition as sr
import time
import sys
import os
import requests
import json
import platform
import subprocess
import shlex
import psutil  # Add psutil for process management

# Import constants for key mappings
try:
    from constants import SHORTCUT_MAPPINGS, KEY_NORMALIZATIONS
    print("[advanced_voice_listener] Constants loaded successfully")
    print(f"[advanced_voice_listener] SHORTCUT_MAPPINGS has {len(SHORTCUT_MAPPINGS)} entries")
    print(f"[advanced_voice_listener] KEY_NORMALIZATIONS has {len(KEY_NORMALIZATIONS)} entries")
except ImportError:
    print("[advanced_voice_listener] Could not import constants, using basic key mapping")
    SHORTCUT_MAPPINGS = {}
    KEY_NORMALIZATIONS = {}

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
_typing_mode_pending = False

# Track EMG control process
_emg_process = None
_emg_controller = None

def _spoken_to_text(s: str) -> str:
    """Convert simple spoken punctuation/controls to characters."""
    repl = {
        "new line": "\n",
        "newline": "\n",
        "line break": "\n",
        "tab": "\t",
        "comma": ",",
        "period": ".",
        "full stop": ".",
        "dot": ".",
        "exclamation point": "!",
        "exclamation mark": "!",
        "question mark": "?",
        "colon": ":",
        "semicolon": ";",
        "dash": "-",
        "hyphen": "-",
        "underscore": "_",
        "slash": "/",
        "back slash": "\\",
        "backslash": "\\",
        "open parenthesis": "(",
        "close parenthesis": ")",
        "open bracket": "[",
        "close bracket": "]",
        "open brace": "{",
        "close brace": "}",
        "quote": '"',
        "double quote": '"',
        "single quote": "'",
    }
    for phrase in sorted(repl.keys(), key=len, reverse=True):
        s = s.replace(phrase, repl[phrase])
    return s

def _type_text(text: str) -> str:
    """Type text into the active app using best available backend."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if part:
                pyautogui.write(part)
            if i < len(parts) - 1:
                pyautogui.press("enter")
        return "Typed text"
    except Exception:
        pass

    if platform.system().lower() == "darwin":
        try:
            def esc(s):
                return s.replace("\\", "\\\\").replace('"', '\\"')
            lines = text.split("\n")
            script_lines = ["tell application \"System Events\""]
            for idx, line in enumerate(lines):
                if line:
                    script_lines.append(f"keystroke \"{esc(line)}\"")
                if idx < len(lines) - 1:
                    script_lines.append("key code 36")  # Return
            script_lines.append("end tell")
            script = "\n".join(script_lines)
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return "Typed text"
        except Exception as e:
            return f"Typing failed: {e}"

    return "Typing not supported on this platform"

def _mac_osascript(script: str) -> tuple[bool, str]:
    try:
        out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return (out.returncode == 0, (out.stdout or out.stderr or "").strip())
    except Exception as e:
        return False, str(e)

def open_app(app_name: str) -> str:
    app = app_name.strip()
    if not app:
        return "No app specified"
    
    system = platform.system().lower()
    
    if system == "darwin":
        # macOS
        try:
            subprocess.run(["open", "-a", app], check=True)
            return f"Opened {app}"
        except Exception:
            ok, msg = _mac_osascript(f'tell application "{app}" to activate')
            return f"Opened {app}" if ok else f"Failed to open {app}: {msg}"
    
    elif system == "windows":
        # Windows
        try:
            # Try common app names and their executables
            app_lower = app.lower()
            
            # Common Windows apps
            win_apps = {
                "chrome": "chrome",
                "google chrome": "chrome",
                "firefox": "firefox",
                "edge": "msedge",
                "microsoft edge": "msedge",
                "notepad": "notepad",
                "calculator": "calc",
                "calc": "calc",
                "explorer": "explorer",
                "file explorer": "explorer",
                "cmd": "cmd",
                "command prompt": "cmd",
                "powershell": "powershell",
                "paint": "mspaint",
                "word": "winword",
                "microsoft word": "winword",
                "excel": "excel",
                "microsoft excel": "excel",
                "outlook": "outlook",
                "microsoft outlook": "outlook",
                "teams": "ms-teams",
                "microsoft teams": "ms-teams",
                "discord": "discord",
                "spotify": "spotify",
                "steam": "steam",
                "minecraft": "minecraft",
                "xbox": "xbox",
                "xbox app": "xbox",
            }
            
            # Try to find the executable
            exe = win_apps.get(app_lower, app)
            
            # First try to start it directly
            try:
                subprocess.Popen([exe], shell=True)
                return f"Opened {app}"
            except:
                # Try with start command
                subprocess.run(["cmd", "/c", "start", "", exe], shell=True, check=False)
                return f"Opened {app}"
        except Exception as e:
            return f"Failed to open {app}: {e}"
    
    elif system == "linux":
        # Linux
        try:
            # Try common Linux desktop launchers
            launchers = ["xdg-open", "gnome-open", "kde-open"]
            for launcher in launchers:
                try:
                    subprocess.run([launcher, app], check=True, capture_output=True)
                    return f"Opened {app}"
                except:
                    continue
            
            # Try to run directly
            subprocess.Popen([app], shell=True)
            return f"Opened {app}"
        except Exception as e:
            return f"Failed to open {app}: {e}"
    
    return f"Platform {system} not supported"

def close_app(app_name: str) -> str:
    app = app_name.strip()
    if not app:
        return "No app specified"
    
    system = platform.system().lower()
    
    if system == "darwin":
        # macOS
        ok, msg = _mac_osascript(f'tell application "{app}" to quit')
        return f"Closed {app}" if ok else f"Failed to close {app}: {msg}"
    
    elif system == "windows":
        # Windows
        try:
            app_lower = app.lower()
            
            # Map common app names to process names
            process_map = {
                "chrome": "chrome.exe",
                "google chrome": "chrome.exe",
                "firefox": "firefox.exe",
                "edge": "msedge.exe",
                "microsoft edge": "msedge.exe",
                "notepad": "notepad.exe",
                "calculator": "calculator.exe",
                "calc": "calculator.exe",
                "explorer": "explorer.exe",
                "file explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "command prompt": "cmd.exe",
                "powershell": "powershell.exe",
                "paint": "mspaint.exe",
                "word": "winword.exe",
                "microsoft word": "winword.exe",
                "excel": "excel.exe",
                "microsoft excel": "excel.exe",
                "outlook": "outlook.exe",
                "microsoft outlook": "outlook.exe",
                "teams": "teams.exe",
                "microsoft teams": "teams.exe",
                "discord": "discord.exe",
                "spotify": "spotify.exe",
                "steam": "steam.exe",
                "minecraft": "minecraft.exe",
                "xbox": "gamingapp.exe",
                "xbox app": "gamingapp.exe",
            }
            
            process_name = process_map.get(app_lower, f"{app}.exe")
            
            # Use taskkill to close the app
            result = subprocess.run(["taskkill", "/F", "/IM", process_name], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"Closed {app}"
            else:
                # Try without .exe if it failed
                if not process_name.endswith(".exe"):
                    process_name += ".exe"
                    result = subprocess.run(["taskkill", "/F", "/IM", process_name], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        return f"Closed {app}"
                
                return f"Failed to close {app}: Process not found"
        except Exception as e:
            return f"Failed to close {app}: {e}"
    
    elif system == "linux":
        # Linux
        try:
            # Try pkill first
            result = subprocess.run(["pkill", "-f", app], capture_output=True)
            if result.returncode == 0:
                return f"Closed {app}"
            
            # Try killall
            result = subprocess.run(["killall", app], capture_output=True)
            if result.returncode == 0:
                return f"Closed {app}"
            
            return f"Failed to close {app}: Process not found"
        except Exception as e:
            return f"Failed to close {app}: {e}"
    
    return f"Platform {system} not supported"

def focus_app(app_name: str) -> str:
    app = app_name.strip()
    if not app:
        return "No app specified"
    
    system = platform.system().lower()
    
    if system == "darwin":
        # macOS
        ok, msg = _mac_osascript(f'tell application "{app}" to activate')
        return f"Switched to {app}" if ok else f"Failed to switch to {app}: {msg}"
    
    elif system == "windows":
        # Windows - use PowerShell to bring window to front
        try:
            # PowerShell script to find and activate window
            ps_script = f'''
            $app = "{app}"
            $processes = Get-Process | Where-Object {{$_.MainWindowTitle -like "*$app*" -or $_.ProcessName -like "*$app*"}}
            if ($processes) {{
                $processes | ForEach-Object {{
                    [Microsoft.VisualBasic.Interaction]::AppActivate($_.Id)
                }}
                "Success"
            }} else {{
                # Try to start the app if not running
                Start-Process $app -ErrorAction SilentlyContinue
                "Started"
            }}
            '''
            
            result = subprocess.run(["powershell", "-Command", ps_script], 
                                  capture_output=True, text=True)
            
            if "Success" in result.stdout or "Started" in result.stdout:
                return f"Switched to {app}"
            else:
                # Fallback: try to open the app
                return open_app(app)
        except Exception as e:
            return f"Failed to switch to {app}: {e}"
    
    elif system == "linux":
        # Linux - use wmctrl if available
        try:
            # Try wmctrl to switch to window
            result = subprocess.run(["wmctrl", "-a", app], capture_output=True)
            if result.returncode == 0:
                return f"Switched to {app}"
            
            # Fallback: try to open the app
            return open_app(app)
        except:
            # If wmctrl not available, try to open the app
            return open_app(app)
    
    return f"Platform {system} not supported"

def minimize_front_window() -> str:
    system = platform.system().lower()
    
    if system == "darwin":
        # macOS
        ok, msg = _mac_osascript('tell application "System Events" to keystroke "m" using {command down}')
        return "Minimized window" if ok else f"Minimize failed: {msg}"
    
    elif system == "windows":
        # Windows - use Win+Down to minimize
        try:
            import pyautogui
            pyautogui.hotkey('win', 'down')
            return "Minimized window"
        except:
            # Fallback: use PowerShell
            try:
                ps_script = '''
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {
                    [DllImport("user32.dll")]
                    public static extern IntPtr GetForegroundWindow();
                    [DllImport("user32.dll")]
                    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                }
                "@
                $hwnd = [Win32]::GetForegroundWindow()
                [Win32]::ShowWindow($hwnd, 6)  # SW_MINIMIZE = 6
                '''
                subprocess.run(["powershell", "-Command", ps_script], check=True)
                return "Minimized window"
            except Exception as e:
                return f"Minimize failed: {e}"
    
    elif system == "linux":
        # Linux - use xdotool or wmctrl
        try:
            # Try xdotool
            subprocess.run(["xdotool", "getactivewindow", "windowminimize"], check=True)
            return "Minimized window"
        except:
            try:
                # Try wmctrl
                subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,hidden"], check=True)
                return "Minimized window"
            except:
                return "Minimize requires xdotool or wmctrl"
    
    return f"Platform {system} not supported"

def maximize_front_window() -> str:
    system = platform.system().lower()
    
    if system == "darwin":
        # macOS
        ok, msg = _mac_osascript('tell application "System Events" to keystroke "f" using {control down, command down}')
        return "Toggled full screen" if ok else f"Maximize failed: {msg}"
    
    elif system == "windows":
        # Windows - use Win+Up to maximize
        try:
            import pyautogui
            pyautogui.hotkey('win', 'up')
            return "Maximized window"
        except:
            # Fallback: use PowerShell
            try:
                ps_script = '''
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {
                    [DllImport("user32.dll")]
                    public static extern IntPtr GetForegroundWindow();
                    [DllImport("user32.dll")]
                    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                }
                "@
                $hwnd = [Win32]::GetForegroundWindow()
                [Win32]::ShowWindow($hwnd, 3)  # SW_MAXIMIZE = 3
                '''
                subprocess.run(["powershell", "-Command", ps_script], check=True)
                return "Maximized window"
            except Exception as e:
                return f"Maximize failed: {e}"
    
    elif system == "linux":
        # Linux - use wmctrl or xdotool
        try:
            # Try wmctrl for maximize
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"], check=True)
            return "Maximized window"
        except:
            try:
                # Try xdotool
                subprocess.run(["xdotool", "key", "super+Up"], check=True)
                return "Maximized window"
            except:
                return "Maximize requires wmctrl or xdotool"
    
    return f"Platform {system} not supported"

def minimize_app_windows(app_name: str) -> str:
    system = platform.system().lower()
    
    if system == "darwin":
        app = app_name.strip()
        if not app:
            return minimize_front_window()
        script = (
            'tell application "System Events"\n'
            f'  tell process "{app}"\n'
            '    try\n'
            '      repeat with w in windows\n'
            '        set value of attribute "AXMinimized" of w to true\n'
            '      end repeat\n'
            '      return "ok"\n'
            '    on error errMsg\n'
            '      return errMsg\n'
            '    end try\n'
            '  end tell\n'
            'end tell'
        )
        ok, msg = _mac_osascript(script)
        return "Minimized app windows" if ok and (msg == "ok" or msg == "") else f"Minimize failed: {msg}"
    
    elif system == "windows":
        # Windows - minimize all windows of an app
        app = app_name.strip()
        if not app:
            return minimize_front_window()
        
        try:
            ps_script = f'''
            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {{
                [DllImport("user32.dll")]
                public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
            }}
            "@
            
            $app = "{app}"
            $processes = Get-Process | Where-Object {{$_.MainWindowTitle -like "*$app*" -or $_.ProcessName -like "*$app*"}}
            if ($processes) {{
                $processes | ForEach-Object {{
                    if ($_.MainWindowHandle -ne 0) {{
                        [Win32]::ShowWindow($_.MainWindowHandle, 6)  # SW_MINIMIZE = 6
                    }}
                }}
                "Success"
            }} else {{
                "No windows found"
            }}
            '''
            
            result = subprocess.run(["powershell", "-Command", ps_script], 
                                  capture_output=True, text=True)
            
            if "Success" in result.stdout:
                return f"Minimized {app} windows"
            else:
                return f"No {app} windows found"
        except Exception as e:
            return f"Failed to minimize {app}: {e}"
    
    elif system == "linux":
        # Linux - minimize app windows using wmctrl
        app = app_name.strip()
        if not app:
            return minimize_front_window()
        
        try:
            # Get all windows for the app and minimize them
            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if app.lower() in line.lower():
                        window_id = line.split()[0]
                        subprocess.run(["wmctrl", "-i", "-r", window_id, "-b", "add,hidden"], check=False)
                return f"Minimized {app} windows"
            return f"No {app} windows found"
        except:
            return "Minimize app requires wmctrl"
    
    return f"Platform {system} not supported"

def stop_emg_control() -> str:
    """Stop the EMG control system"""
    global _emg_process, _emg_controller
    
    try:
        # First try to stop the controller if it's running in the same process
        if _emg_controller:
            try:
                _emg_controller.is_running = False
                _emg_controller = None
                return "EMG control stopped - you can use your mouse now"
            except Exception as e:
                print(f"[advanced_voice_listener] Error stopping controller: {e}")
        
        # Also try to kill any Python processes running EMG control
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('emg_control.py' in str(arg) or 'enhanced_emg_control.py' in str(arg) or 'launcher.py' in str(arg) for arg in cmdline):
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    return "EMG control stopped - you can use your mouse now"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # If we have a tracked subprocess, kill it
        if _emg_process:
            try:
                _emg_process.terminate()
                _emg_process.wait(timeout=3)
            except:
                try:
                    _emg_process.kill()
                except:
                    pass
            _emg_process = None
            return "EMG control stopped - you can use your mouse now"
        
        return "No EMG control process found running"
    except Exception as e:
        return f"Error stopping EMG control: {e}"

def start_emg_control(mode: str = "enhanced") -> str:
    """Start the EMG control system"""
    global _emg_process, _emg_controller
    
    # First check if it's already running
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('emg_control.py' in str(arg) or 'enhanced_emg_control.py' in str(arg) for arg in cmdline):
                return "EMG control is already running"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    try:
        # Find the backend/ml directory
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'ml'))
        
        if mode.lower() in ["enhanced", "imu", "cursor"]:
            script_path = os.path.join(backend_dir, 'enhanced_emg_control.py')
        else:
            script_path = os.path.join(backend_dir, 'emg_control.py')
        
        if not os.path.exists(script_path):
            return f"EMG control script not found at {script_path}"
        
        # Start the EMG control in a subprocess
        _emg_process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return f"Started {mode} EMG control"
    except Exception as e:
        return f"Failed to start EMG control: {e}"

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

def process_key_combination(key_input):
    """Process complex key combinations like 'control plus v' into 'ctrl+v'"""
    key_input = key_input.lower().strip()
    print(f"[advanced_voice_listener] Processing key combination: '{key_input}'")
    
    # First check if it's already a known shortcut
    if key_input in SHORTCUT_MAPPINGS:
        result = SHORTCUT_MAPPINGS[key_input]
        print(f"[advanced_voice_listener] Found shortcut mapping: '{key_input}' -> '{result}'")
        return result
    
    # Handle "plus" combinations like "control plus v"
    if " plus " in key_input:
        parts = key_input.split(" plus ")
        if len(parts) == 2:
            modifier = parts[0].strip()
            key = parts[1].strip()
            
            print(f"[advanced_voice_listener] Plus combination: modifier='{modifier}', key='{key}'")
            
            # Normalize modifier - handle "control" specifically
            if modifier == "control":
                modifier = "ctrl"
            else:
                modifier = KEY_NORMALIZATIONS.get(modifier, modifier)
            
            # Normalize key
            key = KEY_NORMALIZATIONS.get(key, key)
            
            result = f"{modifier}+{key}"
            print(f"[advanced_voice_listener] Plus combination result: '{result}'")
            return result
    
    # Handle "and" combinations like "control and c"
    if " and " in key_input:
        parts = key_input.split(" and ")
        if len(parts) == 2:
            modifier = parts[0].strip()
            key = parts[1].strip()
            
            # Normalize modifier - handle "control" specifically
            if modifier == "control":
                modifier = "ctrl"
            else:
                modifier = KEY_NORMALIZATIONS.get(modifier, modifier)
            
            # Normalize key
            key = KEY_NORMALIZATIONS.get(key, key)
            
            return f"{modifier}+{key}"
    
    # Handle single keys
    normalized_key = KEY_NORMALIZATIONS.get(key_input, key_input)
    return normalized_key

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
        if f"change {phrase} to" in command or f"set {phrase} to" in command or f"change the {phrase} to" in command:
            print(f"[advanced_voice_listener] Gesture change command detected for {phrase}")
            parts = command.split(" to ")
            if len(parts) > 1:
                key_input = parts[1].strip().replace(" key", "").replace("key", "").lower()
                
                # Handle complex key combinations like "control plus v"
                mapped_key = process_key_combination(key_input)
                
                print(f"[advanced_voice_listener] Mapping '{key_input}' to '{mapped_key}'")
                
                try:
                    print(f"[advanced_voice_listener] About to update gesture '{gesture}' with key '{mapped_key}'")
                    gesture_mapper.update_gesture_key(gesture, mapped_key)
                    gesture_mapper.save_config()
                    print(f"[advanced_voice_listener] Successfully changed {gesture} to {mapped_key}")
                    return f"Changed {gesture} to {mapped_key}"
                except Exception as e:
                    print(f"[advanced_voice_listener] Error changing {gesture} to {mapped_key}: {e}")
                    return f"Error changing {gesture} to {mapped_key}: {e}"
    
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
    global _should_exit, _typing_mode_pending
    
    command = normalize_command(command)
    set_voice_status(f"Processing: {command}")
    
    send_voice_data(command)
    
    if "stop listening" in command or "exit" in command or "quit" in command:
        set_voice_status("Shutting down voice listener")
        _should_exit = True
        return

    if _typing_mode_pending:
        to_type = _spoken_to_text(command)
        result = _type_text(to_type)
        _typing_mode_pending = False
        set_voice_status(result)
        send_voice_data(command, result)
        time.sleep(0.5)
        set_voice_status("Listening for 'Gemini'...")
        return

    if command.startswith("type "):
        to_type = _spoken_to_text(command[len("type "):].strip())
        result = _type_text(to_type)
        set_voice_status(result)
        send_voice_data(command, result)
        time.sleep(0.5)
        set_voice_status("Listening for 'Gemini'...")
        return

    if command in ("type", "start typing", "typing mode"):
        _typing_mode_pending = True
        set_voice_status("Typing mode: say what to type")
        send_voice_data(command, "typing-mode-armed")
        return

    if command.startswith("open "):
        app = command[len("open "):].strip()
        result = open_app(app)
        set_voice_status(result)
        send_voice_data(command, result)
        return
    # Handle EMG control commands
    if "stop emg" in command or "stop control" in command or command == "stop":
        result = stop_emg_control()
        set_voice_status(result)
        send_voice_data(command, result)
        time.sleep(0.5)
        set_voice_status("Listening for 'Gemini'...")
        return
    
    if "start emg" in command or "start control" in command:
        if "enhanced" in command or "imu" in command or "cursor" in command:
            result = start_emg_control("enhanced")
        else:
            result = start_emg_control("basic")
        set_voice_status(result)
        send_voice_data(command, result)
        time.sleep(0.5)
        set_voice_status("Listening for 'Gemini'...")
        return
    
    if command.startswith("close "):
        app = command[len("close "):].strip()
        result = close_app(app)
        set_voice_status(result)
        send_voice_data(command, result)
        return
    if command.startswith("switch to ") or command.startswith("focus ") or command.startswith("activate "):
        app = command.split(" ", 1)[1].strip()
        result = focus_app(app)
        set_voice_status(result)
        send_voice_data(command, result)
        return
    if command.startswith("minimize "):
        target = command[len("minimize "):].strip()
        if target in ("window", "the window", "front window"):
            result = minimize_front_window()
        else:
            focus_app(target)
            result = minimize_app_windows(target)
        set_voice_status(result)
        send_voice_data(command, result)
        return
    if command.startswith("maximize "):
        target = command[len("maximize "):].strip()
        if target in ("window", "the window", "front window"):
            result = maximize_front_window()
        else:
            focus_app(target)
            result = maximize_front_window()
        set_voice_status(result)
        send_voice_data(command, result)
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
