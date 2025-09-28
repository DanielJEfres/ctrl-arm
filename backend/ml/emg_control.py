import serial
import serial.tools.list_ports
import numpy as np
import pyautogui
import time
import threading
import queue
from collections import deque
from pathlib import Path
import pickle
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
import json
import websockets
import asyncio
import yaml

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001

class SmartEMGController:
    def __init__(self):
        print("\n" + "="*60)
        print(" "*15 + "SMART EMG CONTROL")
        print("="*60)

        self.serial_conn = None
        self.connect_device()

        self.emg1_buffer = deque(maxlen=30)
        self.emg2_buffer = deque(maxlen=30)
        self.data_queue = queue.Queue(maxsize=200)

        self.baseline_left = 0
        self.baseline_right = 0
        self.noise_left = 0
        self.noise_right = 0

        # thresholds for fast detection
        self.activation_threshold = 40
        self.strong_threshold = 200  # higher threshold for scroll actions
        self.noise_multiplier = 3
        
        # ml model
        self.decision_tree = None
        self.scaler = StandardScaler()
        self.load_model()
        
        # fast processing settings
        self.window_size = 15
        self.process_interval = 15
        
        self.is_running = False
        self.last_action_time = 0
        self.action_cooldown = 0.3
        
        self.gesture_history = deque(maxlen=3)
        self.last_gesture = 'rest'
        
        self.min_gesture_duration = 2
        
        self.gesture_counts = {}
        self.threshold_count = 0
        self.ml_count = 0
        
        # WebSocket server for real-time visualization
        self.websocket_server = None
        self.connected_clients = set()
        self.start_websocket_server()
        
        self.gesture_config = self.load_gesture_config()
        self.last_config_check = time.time()
        self.config_check_interval = 5  # Check config every 5 seconds

    def load_gesture_config(self):
        """Load gesture configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent.parent.parent / "hardware" / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.full_config = yaml.safe_load(f)
                
                # Get current mode and its key mappings
                current_mode = self.full_config.get('active_profile', 'default_mode')
                gesture_keys = self.full_config.get('gesture_keys', {})
                mode_keys = gesture_keys.get(current_mode, {})
                
                if mode_keys:
                    print(f"Loaded gesture config for mode: {current_mode}")
                    # Filter out null values
                    filtered_keys = {k: v for k, v in mode_keys.items() if v and v != 'null'}
                    return filtered_keys
                else:
                    print(f"No keys found for mode: {current_mode}, using defaults")
                    return self.get_default_gestures()
            else:
                print("Config file not found, using default gestures")
                self.full_config = None
                return self.get_default_gestures()
        except Exception as e:
            print(f"Error loading config: {e}, using default gestures")
            self.full_config = None
            return self.get_default_gestures()
    
    def switch_to_mode(self, mode_name):
        """Switch to a different control mode and update config file"""
        if not self.full_config:
            return False
        
        try:
            gesture_keys = self.full_config.get('gesture_keys', {})
            if mode_name in gesture_keys:
                # Update active profile in config
                self.full_config['active_profile'] = mode_name
                
                # Get the new mode's keys
                mode_keys = gesture_keys.get(mode_name, {})
                self.gesture_config = {k: v for k, v in mode_keys.items() if v and v != 'null'}
                
                # Save the updated config
                config_path = Path(__file__).parent.parent.parent / "hardware" / "config.yaml"
                with open(config_path, 'w') as f:
                    yaml.safe_dump(self.full_config, f, default_flow_style=False, sort_keys=False)
                
                print(f"Switched to {mode_name} mode")
                return True
        except Exception as e:
            print(f"Error switching mode: {e}")
        return False

    def get_default_gestures(self):
        """Default gesture mappings if config fails"""
        return {
            'left_single': 'tab',
            'right_single': 'enter', 
            'left_double': 'escape',
            'right_double': 'space',
            'left_hold': 'ctrl',
            'right_hold': 'alt',
            'both_flex': 'shift',
            'left_then_right': 'f1',
            'right_then_left': 'f2',
            'left_hard': 'f3',
            'right_hard': 'f4'
        }

    def load_model(self):
        # load existing model if available
        model_path = Path(__file__).parent / "emg_model.pkl"
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.decision_tree = data['model']
                    self.scaler = data['scaler']
                    print("loaded decision tree model")
            except:
                print("no ml model found, using thresholds only")
                self.decision_tree = None
        else:
            print("using threshold detection only")
            self.decision_tree = None

    def connect_device(self):
        print("\nconnecting to device...")

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("no devices found!")
            return False

        port = None
        for p in ports:
            if any(x in p.description for x in ['XIAO', 'Arduino', 'USB Serial']):
                port = p.device
                break

        if not port:
            port = ports[0].device

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=0.01)
            time.sleep(1.5)

            while self.serial_conn.in_waiting:
                self.serial_conn.readline()

            print(f"connected to {port}")
            return True

        except Exception as e:
            print(f"connection failed: {e}")
            return False

    def calibrate(self):
        print("\ncalibration")
        print("-"*60)
        print("\nkeep arms relaxed for 2 seconds...")
        
        for i in range(2, 0, -1):
            print(f"   {i}...")
            time.sleep(1)

        print("\nreading baseline...")

        baseline_data_left = []
        baseline_data_right = []

        start_time = time.time()
        while time.time() - start_time < 2:
            if self.serial_conn.in_waiting:
                try:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            baseline_data_left.append(int(values[1]))
                            baseline_data_right.append(int(values[2]))
                except:
                    pass

        if baseline_data_left:
            self.baseline_left = np.mean(baseline_data_left)
            self.baseline_right = np.mean(baseline_data_right)
            self.noise_left = np.std(baseline_data_left)
            self.noise_right = np.std(baseline_data_right)

            print(f"\ncalibration complete!")
            print(f"   left:  {self.baseline_left:.0f} +/- {self.noise_left:.0f}")
            print(f"   right: {self.baseline_right:.0f} +/- {self.noise_right:.0f}")

            # adjust threshold based on noise
            min_threshold = max(40, self.noise_multiplier * max(self.noise_left, self.noise_right))
            self.activation_threshold = min_threshold
            print(f"   activation threshold: {self.activation_threshold:.0f}")

            return True
        else:
            print("calibration failed - no data")
            return False

    def start_websocket_server(self):
        """Start WebSocket server for real-time data streaming"""
        try:
            async def handle_client(websocket, path):
                """Handle new WebSocket client connections"""
                self.connected_clients.add(websocket)
                print("Visualizer connected")
                try:
                    await websocket.wait_closed()
                finally:
                    self.connected_clients.discard(websocket)
                    print("Visualizer disconnected")
            
            # Start WebSocket server in a separate thread
            def run_server():
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Start the WebSocket server
                    start_server = websockets.serve(handle_client, "localhost", 8765)
                    loop.run_until_complete(start_server)
                    print("WebSocket server started on ws://localhost:8765")
                    loop.run_forever()
                except Exception as e:
                    print(f"WebSocket server error: {e}")
                finally:
                    loop.close()
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
        except Exception as e:
            print(f"Failed to start WebSocket server: {e}")

    def broadcast_data(self, data):
        """Broadcast EMG data to all connected clients"""
        if self.connected_clients:
            message = json.dumps(data)
            
            # Create a task to send data to all clients
            async def send_to_all():
                disconnected = set()
                for client in self.connected_clients:
                    try:
                        await client.send(message)
                    except:
                        disconnected.add(client)
                # Remove disconnected clients
                self.connected_clients -= disconnected
            
            # Try to get the event loop and schedule the task
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    asyncio.create_task(send_to_all())
                else:
                    # If loop is not running, run until complete
                    loop.run_until_complete(send_to_all())
            except RuntimeError:
                # No event loop in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_to_all())
                loop.close()

    def extract_features(self, emg1_window, emg2_window):
        # fast feature extraction for ml
        emg1_array = np.array(emg1_window)
        emg2_array = np.array(emg2_window)
        
        features = [
            np.mean(emg1_array),
            np.std(emg1_array),
            np.max(emg1_array),
            np.max(emg1_array) - np.min(emg1_array),
            np.sqrt(np.mean(emg1_array**2)),
            np.mean(emg2_array),
            np.std(emg2_array),
            np.max(emg2_array),
            np.max(emg2_array) - np.min(emg2_array),
            np.sqrt(np.mean(emg2_array**2)),
            np.corrcoef(emg1_array, emg2_array)[0, 1] if len(emg1_array) > 1 else 0,
            np.mean(emg1_array) - self.baseline_left,
            np.mean(emg2_array) - self.baseline_right
        ]
        return features

    def detect_gesture_smart(self, left_activity, right_activity, emg1_window, emg2_window):
        # first try fast threshold detection
        left_active = left_activity > self.activation_threshold
        right_active = right_activity > self.activation_threshold
        
        # clear cases use thresholds for speed
        if not left_active and not right_active:
            self.threshold_count += 1
            return 'rest'
        
        left_strong = left_activity > self.strong_threshold
        right_strong = right_activity > self.strong_threshold
        
        # much lower thresholds for both actions (50% more sensitive for both)
        both_activation = self.activation_threshold * 0.5  # 20 instead of 40
        both_strong_threshold = self.strong_threshold * 0.6  # 120 instead of 200
        left_active_both = left_activity > both_activation
        right_active_both = right_activity > both_activation
        left_strong_both = left_activity > both_strong_threshold
        right_strong_both = right_activity > both_strong_threshold
        
        # check for both actions first with more sensitive thresholds
        if left_active_both and right_active_both:
            # use ml for better both gesture detection if available
            if self.decision_tree:
                try:
                    features = self.extract_features(emg1_window, emg2_window)
                    features_scaled = self.scaler.transform([features])
                    gesture = self.decision_tree.predict(features_scaled)[0]
                    self.ml_count += 1
                    return gesture
                except:
                    pass
            
            # fallback to threshold logic with sensitive thresholds
            self.threshold_count += 1
            return 'both_strong' if (left_strong_both and right_strong_both) else 'both_flex'
        
        # single muscle actions use normal thresholds
        self.threshold_count += 1
        
        if left_active and not right_active:
            return 'left_hard' if left_strong else 'left_single'
        elif right_active and not left_active:
            return 'right_hard' if right_strong else 'right_single'
        else:
            # shouldn't reach here but default to both_flex
            return 'both_flex'

    def execute_action(self, gesture):
        current_time = time.time()
        
        # use longer cooldown for scroll actions
        cooldown = 0.5 if 'hard' in gesture else self.action_cooldown
        
        if current_time - self.last_action_time < cooldown:
            return

        key_mapping = self.gesture_config.get(gesture)
        
        if key_mapping and key_mapping != 'null' and key_mapping is not None:
            # Check if it's a mouse action
            mouse_actions = {
                'click': lambda: pyautogui.click(),
                'rightclick': lambda: pyautogui.click(button='right'),
                'doubleclick': lambda: pyautogui.doubleClick(),
                'middleclick': lambda: pyautogui.click(button='middle'),
                'scrollup': lambda: pyautogui.scroll(2),
                'scrolldown': lambda: pyautogui.scroll(-2),
                'drag': lambda: pyautogui.mouseDown(),
                'rightdrag': lambda: pyautogui.mouseDown(button='right')
            }
            
            if key_mapping.lower() in mouse_actions:
                print(f"\n>> {gesture}: {key_mapping}")
                mouse_actions[key_mapping.lower()]()
            else:
                # It's a keyboard key
                print(f"\n>> {gesture}: {key_mapping}")
                self.send_key(key_mapping)
            
            self.last_action_time = current_time
            self.gesture_counts[gesture] = self.gesture_counts.get(gesture, 0) + 1
        # Don't print anything for gestures with no action

    def send_key(self, key_combo):
        """Send key combination based on config"""
        try:
            if '+' in key_combo:
                keys = key_combo.split('+')
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key_combo)
        except Exception as e:
            print(f"Error sending key '{key_combo}': {e}")

    def read_serial_data(self):
        while self.is_running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            emg1 = int(values[1])
                            emg2 = int(values[2])
                            
                            if self.data_queue.qsize() > 150:
                                try:
                                    self.data_queue.get_nowait()
                                except:
                                    pass
                            
                            self.data_queue.put((emg1, emg2))
            except:
                pass
            
            time.sleep(0.001)

    def process_data(self):
        print("\ncontrol active")
        print("-"*60)

        last_display_time = time.time()
        sample_count = 0

        while self.is_running:
            try:
                if not self.data_queue.empty():
                    emg1, emg2 = self.data_queue.get_nowait()
                    self.emg1_buffer.append(emg1)
                    self.emg2_buffer.append(emg2)
                    sample_count += 1

                    if sample_count % self.process_interval == 0 and len(self.emg1_buffer) >= self.window_size:
                        left_data = list(self.emg1_buffer)[-self.window_size:]
                        right_data = list(self.emg2_buffer)[-self.window_size:]
                        
                        left_activity = np.mean(left_data) - self.baseline_left
                        right_activity = np.mean(right_data) - self.baseline_right
                        
                        # smart detection uses both threshold and ml
                        gesture = self.detect_gesture_smart(left_activity, right_activity, left_data, right_data)
                        self.gesture_history.append(gesture)

                        # Broadcast real-time data to visualizer
                        self.broadcast_data({
                            'timestamp': time.time(),
                            'emg1': emg1,
                            'emg2': emg2,
                            'left_activity': left_activity,
                            'right_activity': right_activity,
                            'gesture': gesture,
                            'baseline_left': self.baseline_left,
                            'baseline_right': self.baseline_right,
                            'activation_threshold': self.activation_threshold,
                            'strong_threshold': self.strong_threshold
                        })

                        current_time = time.time()
                        
                        # Periodically reload config to pick up changes
                        if current_time - self.last_config_check > self.config_check_interval:
                            new_config = self.load_gesture_config()
                            if new_config != self.gesture_config:
                                self.gesture_config = new_config
                                print("\n[Config reloaded]")
                            self.last_config_check = current_time
                        
                        if current_time - last_display_time > 0.15:
                            left_bar = "=" * min(10, int(left_activity / 10))
                            right_bar = "=" * min(10, int(right_activity / 10))

                            status = f"\rl:{left_activity:+4.0f} {left_bar:10s} | "
                            status += f"r:{right_activity:+4.0f} {right_bar:10s} | "
                            status += f"[{gesture:12s}]"

                            print(status, end='', flush=True)
                            last_display_time = current_time

                        if gesture != 'rest':
                            recent = list(self.gesture_history)[-self.min_gesture_duration:]
                            if len(recent) >= self.min_gesture_duration and all(g == gesture for g in recent):
                                self.execute_action(gesture)
                                self.gesture_history.clear()

            except Exception:
                pass

            time.sleep(0.002)

    def show_stats(self):
        print("\n\nsession statistics")
        print("-"*60)

        if self.gesture_counts:
            total = sum(self.gesture_counts.values())
            print(f"total actions: {total}")
            
            # show detection method usage
            total_detections = self.threshold_count + self.ml_count
            if total_detections > 0:
                print(f"threshold: {self.threshold_count} ({self.threshold_count/total_detections*100:.1f}%)")
                print(f"ml model:  {self.ml_count} ({self.ml_count/total_detections*100:.1f}%)")

            print("\ngestures:")
            for gesture, count in sorted(self.gesture_counts.items(),
                                        key=lambda x: x[1], reverse=True):
                print(f"  {gesture:12s}: {count:3d}")
        else:
            print("no actions performed")

    def run(self):
        if not self.serial_conn:
            print("no device connected!")
            return

        if not self.calibrate():
            return

        print("\n" + "="*60)
        print("smart gesture controls")
        print("="*60)
        
        # Show actual key mappings from config
        if self.gesture_config:
            print("Current key mappings:")
            for gesture, key in self.gesture_config.items():
                if key and key != 'null':
                    print(f"  {gesture:15s} -> {key}")
        else:
            print("Using default mappings")
        
        print("\nsystem:")
        if self.decision_tree:
            print("  * using decision tree for complex gestures")
            print("  * thresholds for simple gestures")
        else:
            print("  * using threshold detection only")
        print("  * latency ~30ms")
        print("\nwarning: move mouse to corner to stop")
        print("press ctrl+c to exit")
        print("="*60)

        self.is_running = True

        read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        read_thread.start()

        try:
            self.process_data()
        except KeyboardInterrupt:
            print("\n\nstopping...")
        finally:
            self.is_running = False
            self.show_stats()

            if self.serial_conn:
                self.serial_conn.close()

            print("\nsmart control stopped!")

def main():
    try:
        import pyautogui
    except ImportError:
        print("installing pyautogui...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        import pyautogui

    controller = SmartEMGController()
    controller.run()

if __name__ == "__main__":
    main()
