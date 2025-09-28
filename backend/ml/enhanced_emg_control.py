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
import math

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001

class EnhancedEMGController:
    def __init__(self):
        print("\n" + "="*60)
        print(" "*15 + "enhanced emg + imu control")
        print("="*60)

        self.serial_conn = None
        self.connect_device()

        # EMG data buffers
        self.emg1_buffer = deque(maxlen=30)
        self.emg2_buffer = deque(maxlen=30)
        self.data_queue = queue.Queue(maxsize=200)

        # IMU data buffers for cursor control
        self.imu_buffer = deque(maxlen=10)  # Smaller buffer for real-time cursor control
        self.cursor_smoothing_buffer = deque(maxlen=5)  # For smooth cursor movement
        
        # EMG calibration
        self.baseline_left = 0
        self.baseline_right = 0
        self.noise_left = 0
        self.noise_right = 0

        # EMG thresholds
        self.activation_threshold = 40
        self.strong_threshold = 200
        self.noise_multiplier = 3
        
        # ML model
        self.decision_tree = None
        self.scaler = StandardScaler()
        self.load_model()
        
        # Processing settings
        self.window_size = 15
        self.process_interval = 15
        
        # Control state
        self.is_running = False
        self.last_action_time = 0
        self.action_cooldown = 0.3
        
        # Gesture detection
        self.gesture_history = deque(maxlen=3)
        self.last_gesture = 'rest'
        self.min_gesture_duration = 2
        
        # Statistics
        self.gesture_counts = {}
        self.threshold_count = 0
        self.ml_count = 0
        
        # imu cursor control settings
        self.cursor_sensitivity = 25.0  # much higher for actual movement
        self.cursor_deadzone = 0.008   # very small deadzone
        self.cursor_smoothing_factor = 0.6  # slightly smoother for control
        
        # IMU calibration
        self.imu_baseline = {'accel_x': 0, 'accel_y': 0, 'accel_z': 0}
        self.imu_calibrated = False
        
        # Cursor control state
        self.cursor_enabled = True
        self.last_cursor_time = 0
        self.cursor_update_interval = 0.016  # ~60 FPS for smooth cursor movement
        
        # Smooth cursor movement
        self.cursor_velocity = {'x': 0, 'y': 0}
        self.cursor_position = {'x': 0, 'y': 0}
        self.target_cursor_velocity = {'x': 0, 'y': 0}
        
        # drift compensation
        self.drift_samples = []  # to detect and compensate for drift
        self.drift_compensation = {'x': 0, 'y': 0, 'z': 0}
        
        # click intent detection for cursor smoothing
        self.click_intent_threshold = 0.3  # seconds of low movement to detect click intent
        self.click_intent_movement_threshold = 2.0  # pixels per second to consider "trying to click"
        self.movement_history = deque(maxlen=30)  # track recent movements
        self.cursor_slowdown_factor = 0.1  # how much to slow cursor during click intent
        self.last_movement_time = time.time()
        self.click_intent_active = False

    def load_model(self):
        """Load the existing EMG decision tree model"""
        model_path = Path(__file__).parent / "emg_model.pkl"
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.decision_tree = data['model']
                    self.scaler = data['scaler']
                    print("loaded decision tree model for emg gestures")
            except Exception as e:
                print(f"failed to load ml model: {e}")
                self.decision_tree = None
        else:
            print("using threshold detection only for emg gestures")
            self.decision_tree = None

    def connect_device(self):
        """Connect to the XIAO device"""
        print("\nconnecting to device...")

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("no devices found!")
            return False

        print("available ports:")
        for i, p in enumerate(ports):
            print(f"   {i+1}. {p.device} - {p.description}")

        port = None
        
        # Try to find XIAO/Arduino ports first
        for p in ports:
            if any(x in p.description.lower() for x in ['xiao', 'arduino', 'usb serial', 'usb-serial', 'ch340', 'cp210', 'ftdi']):
                port = p.device
                print(f"found potential device: {p.device} - {p.description}")
                break

        # If no specific device found, let user choose
        if not port:
            print("\nno xiao/arduino device auto-detected.")
            print("Please select a port:")
            for i, p in enumerate(ports):
                print(f"   {i+1}. {p.device} - {p.description}")
            
            while True:
                try:
                    choice = input(f"\nEnter port number (1-{len(ports)}) or press Enter for first port: ").strip()
                    if not choice:
                        port = ports[0].device
                        break
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(ports):
                        port = ports[choice_num - 1].device
                        break
                    else:
                        print(f"please enter a number between 1 and {len(ports)}")
                except ValueError:
                    print("please enter a valid number")
                except KeyboardInterrupt:
                    print("\nexiting...")
                    return False

        print(f"\nattempting to connect to {port}...")

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=0.01)
            time.sleep(2)  # Give more time for connection

            # Clear any existing data
            print("clearing buffer...")
            time.sleep(0.5)
            while self.serial_conn.in_waiting:
                self.serial_conn.readline()

            print(f"connected to {port}")
            print("waiting for data...")
            
            # Test if we're getting data
            test_start = time.time()
            while time.time() - test_start < 3:
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('#'):
                        print(f"sample data: {line[:50]}...")
                        return True
                time.sleep(0.1)
            
            print("no data received. check if xiao is running the correct firmware.")
            return True  # Still return True, might work during calibration

        except Exception as e:
            print(f"connection failed: {e}")
            print("\ntroubleshooting tips:")
            print("   - check usb cable connection")
            print("   - verify xiao sense is powered on")
            print("   - try a different usb port")
            print("   - make sure arduino firmware is uploaded")
            print("   - check if another program is using the port")
            return False

    def calibrate_emg(self):
        """Calibrate EMG sensors for personalized thresholds"""
        print("\nemg calibration")
        print("-" * 40)
        print("Keep arms relaxed for 2 seconds...")
        
        for i in range(2, 0, -1):
            print(f"   {i}...")
            time.sleep(1)

        print("\nReading baseline...")

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

            print(f"\nemg calibration complete")
            print(f"   Left:  {self.baseline_left:.0f} ± {self.noise_left:.0f}")
            print(f"   Right: {self.baseline_right:.0f} ± {self.noise_right:.0f}")

            # Adjust threshold based on noise
            min_threshold = max(40, self.noise_multiplier * max(self.noise_left, self.noise_right))
            self.activation_threshold = min_threshold
            print(f"   Activation threshold: {self.activation_threshold:.0f}")

            return True
        else:
            print("emg calibration failed - no data")
            return False

    def calibrate_imu(self):
        """Calibrate IMU for cursor control"""
        print("\nimu calibration for cursor control")
        print("-" * 40)
        print("Sit in neutral position (chest straight) for 3 seconds...")
        
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)

        print("\nReading IMU baseline...")

        imu_data = {'accel_x': [], 'accel_y': [], 'accel_z': []}

        start_time = time.time()
        while time.time() - start_time < 3:
            if self.serial_conn.in_waiting:
                try:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            imu_data['accel_x'].append(float(values[3]))
                            imu_data['accel_y'].append(float(values[4]))
                            imu_data['accel_z'].append(float(values[5]))
                except:
                    pass

        if imu_data['accel_x']:
            # calculate baseline with better averaging
            self.imu_baseline['accel_x'] = np.median(imu_data['accel_x'])  # use median to reduce outliers
            self.imu_baseline['accel_y'] = np.median(imu_data['accel_y'])
            self.imu_baseline['accel_z'] = np.median(imu_data['accel_z'])
            
            # calculate noise levels for adaptive deadzones
            self.drift_compensation['x'] = np.std(imu_data['accel_x'])
            self.drift_compensation['y'] = np.std(imu_data['accel_y'])
            self.drift_compensation['z'] = np.std(imu_data['accel_z'])
            
            print(f"\nimu calibration complete")
            print(f"   X: {self.imu_baseline['accel_x']:.3f} (noise: {self.drift_compensation['x']:.4f})")
            print(f"   Y: {self.imu_baseline['accel_y']:.3f} (noise: {self.drift_compensation['y']:.4f})")
            print(f"   Z: {self.imu_baseline['accel_z']:.3f} (noise: {self.drift_compensation['z']:.4f})")
            print("\ncursor control mapping (flight controls):")
            print("   lean forward  -> move cursor down (like pushing stick forward)")
            print("   lean backward -> move cursor up (like pulling stick back)")
            print("   lean left     -> move cursor left")
            print("   lean right    -> move cursor right")
            print("   automatic slowdown when trying to click")
            
            self.imu_calibrated = True
            return True
        else:
            print("imu calibration failed - no data")
            return False

    def extract_features(self, emg1_window, emg2_window):
        """Extract features for EMG gesture recognition"""
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
        """Detect EMG gestures using hybrid threshold + ML approach"""
        # Fast threshold detection
        left_active = left_activity > self.activation_threshold
        right_active = right_activity > self.activation_threshold
        
        # Clear cases use thresholds for speed
        if not left_active and not right_active:
            self.threshold_count += 1
            return 'rest'
        
        left_strong = left_activity > self.strong_threshold
        right_strong = right_activity > self.strong_threshold
        
        # Lower thresholds for both actions
        both_activation = self.activation_threshold * 0.5
        both_strong_threshold = self.strong_threshold * 0.6
        left_active_both = left_activity > both_activation
        right_active_both = right_activity > both_activation
        left_strong_both = left_activity > both_strong_threshold
        right_strong_both = right_activity > both_strong_threshold
        
        # Check for both actions first
        if left_active_both and right_active_both:
            # Use ML for better both gesture detection if available
            if self.decision_tree:
                try:
                    features = self.extract_features(emg1_window, emg2_window)
                    features_scaled = self.scaler.transform([features])
                    gesture = self.decision_tree.predict(features_scaled)[0]
                    self.ml_count += 1
                    return gesture
                except:
                    pass
            
            # Fallback to threshold logic
            self.threshold_count += 1
            return 'both_strong' if (left_strong_both and right_strong_both) else 'both_flex'
        
        # Single muscle actions
        self.threshold_count += 1
        
        if left_active and not right_active:
            return 'left_strong' if left_strong else 'left_flex'
        elif right_active and not left_active:
            return 'right_strong' if right_strong else 'right_flex'
        else:
            return 'both_flex'

    def calculate_cursor_movement(self, accel_x, accel_y, accel_z):
        # calculate cursor movement based on imu data
        if not self.imu_calibrated:
            return 0, 0
        
        # calculate deviation from baseline
        delta_x = accel_x - self.imu_baseline['accel_x']
        delta_y = accel_y - self.imu_baseline['accel_y']
        delta_z = accel_z - self.imu_baseline['accel_z']
        
        # flight controls mapping:
        # left/right: delta_y controls horizontal (working well)
        # forward/backward: delta_z controls vertical BUT INVERTED for flight controls
        # lean forward (positive delta_z) -> cursor moves DOWN (like pushing stick forward)
        # lean backward (negative delta_z) -> cursor moves UP (like pulling stick back)
        cursor_delta_x = delta_y * self.cursor_sensitivity  # y controls horizontal
        cursor_delta_y = delta_z * self.cursor_sensitivity  # z for vertical (flight style - forward=down)
        
        # apply deadzone with scaling to make small movements more responsive
        if abs(delta_y) < self.cursor_deadzone:
            cursor_delta_x = 0
        else:
            # scale up small movements
            sign_x = 1 if cursor_delta_x > 0 else -1
            cursor_delta_x = sign_x * max(abs(cursor_delta_x), 0.5)
            
        if abs(delta_z) < self.cursor_deadzone:
            cursor_delta_y = 0
        else:
            # scale up small movements
            sign_y = 1 if cursor_delta_y > 0 else -1
            cursor_delta_y = sign_y * max(abs(cursor_delta_y), 0.5)
        
        return cursor_delta_x, cursor_delta_y

    def detect_click_intent(self, delta_x, delta_y):
        # detect if user is trying to click (low movement for a period)
        current_time = time.time()
        movement_magnitude = abs(delta_x) + abs(delta_y)
        
        # add current movement to history with timestamp
        self.movement_history.append((current_time, movement_magnitude))
        
        # calculate average movement over last 0.3 seconds
        recent_movements = [(t, m) for t, m in self.movement_history if current_time - t <= self.click_intent_threshold]
        
        if len(recent_movements) > 5:  # need some samples
            avg_movement = sum(m for t, m in recent_movements) / len(recent_movements)
            
            # if average movement is low, user might be trying to click
            if avg_movement < self.click_intent_movement_threshold:
                self.click_intent_active = True
                return True
            else:
                self.click_intent_active = False
                return False
        
        self.click_intent_active = False
        return False
    
    def smooth_cursor_movement(self, target_x, target_y):
        # apply smoothing to cursor movement for natural feel
        # check for click intent and slow down cursor if detected
        click_intent = self.detect_click_intent(target_x, target_y)
        
        # apply slowdown if user is trying to click
        if click_intent:
            target_x *= self.cursor_slowdown_factor
            target_y *= self.cursor_slowdown_factor
        
        # update target velocity
        self.target_cursor_velocity['x'] = target_x
        self.target_cursor_velocity['y'] = target_y
        
        # smooth velocity changes with higher responsiveness
        smoothing = self.cursor_smoothing_factor
        if click_intent:
            smoothing *= 2.0  # extra smoothing during click intent
            
        self.cursor_velocity['x'] += (self.target_cursor_velocity['x'] - self.cursor_velocity['x']) * smoothing
        self.cursor_velocity['y'] += (self.target_cursor_velocity['y'] - self.cursor_velocity['y']) * smoothing
        
        # return velocity directly for more immediate response
        return self.cursor_velocity['x'], self.cursor_velocity['y']

    def update_cursor(self, accel_x, accel_y, accel_z):
        """Update cursor position based on IMU data"""
        if not self.cursor_enabled:
            return
        
        current_time = time.time()
        if current_time - self.last_cursor_time < self.cursor_update_interval:
            return
        
        # Calculate raw cursor movement
        raw_delta_x, raw_delta_y = self.calculate_cursor_movement(accel_x, accel_y, accel_z)
        
        # Apply smoothing
        smooth_delta_x, smooth_delta_y = self.smooth_cursor_movement(raw_delta_x, raw_delta_y)
        
        # move cursor with very low threshold for responsiveness
        if abs(smooth_delta_x) > 0.001 or abs(smooth_delta_y) > 0.001:
            try:
                current_x, current_y = pyautogui.position()
                # direct movement without extra scaling
                move_x = smooth_delta_x
                move_y = smooth_delta_y
                new_x = max(0, min(pyautogui.size().width - 1, current_x + move_x))
                new_y = max(0, min(pyautogui.size().height - 1, current_y + move_y))
                pyautogui.moveTo(new_x, new_y, duration=0)  # instant movement
            except:
                pass  # ignore cursor movement errors
        
        self.last_cursor_time = current_time

    def execute_action(self, gesture):
        """Execute actions based on detected gestures"""
        current_time = time.time()
        
        # Use longer cooldown for scroll actions
        cooldown = 0.5 if 'strong' in gesture else self.action_cooldown
        
        if current_time - self.last_action_time < cooldown:
            return

        actions = {
            'left_flex': ('left click', lambda: pyautogui.click()),
            'right_flex': ('right click', lambda: pyautogui.click(button='right')),
            'both_flex': ('double click', lambda: pyautogui.doubleClick()),
            'left_strong': ('scroll up', lambda: pyautogui.scroll(2)),
            'right_strong': ('scroll down', lambda: pyautogui.scroll(-2)),
            'both_strong': ('middle click', lambda: pyautogui.click(button='middle'))
        }

        if gesture in actions:
            name, action = actions[gesture]
            print(f"\n>> {name}")
            action()

            self.last_action_time = current_time
            self.gesture_counts[gesture] = self.gesture_counts.get(gesture, 0) + 1

    def read_serial_data(self):
        """Read data from serial port in separate thread"""
        while self.is_running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            emg1 = int(values[1])
                            emg2 = int(values[2])
                            accel_x = float(values[3])
                            accel_y = float(values[4])
                            accel_z = float(values[5])
                            
                            # Queue data for processing
                            if self.data_queue.qsize() > 150:
                                try:
                                    self.data_queue.get_nowait()
                                except:
                                    pass
                            
                            self.data_queue.put((emg1, emg2, accel_x, accel_y, accel_z))
            except:
                pass
            
            time.sleep(0.001)

    def process_data(self):
        """Main data processing loop"""
        print("\nenhanced control active")
        print("-" * 60)

        last_display_time = time.time()
        sample_count = 0

        while self.is_running:
            try:
                if not self.data_queue.empty():
                    emg1, emg2, accel_x, accel_y, accel_z = self.data_queue.get_nowait()
                    
                    # Update EMG buffers
                    self.emg1_buffer.append(emg1)
                    self.emg2_buffer.append(emg2)
                    
                    # Update cursor position based on IMU
                    self.update_cursor(accel_x, accel_y, accel_z)
                    
                    sample_count += 1

                    # Process EMG gestures
                    if sample_count % self.process_interval == 0 and len(self.emg1_buffer) >= self.window_size:
                        left_data = list(self.emg1_buffer)[-self.window_size:]
                        right_data = list(self.emg2_buffer)[-self.window_size:]
                        
                        left_activity = np.mean(left_data) - self.baseline_left
                        right_activity = np.mean(right_data) - self.baseline_right
                        
                        # Detect gesture
                        gesture = self.detect_gesture_smart(left_activity, right_activity, left_data, right_data)
                        self.gesture_history.append(gesture)

                        # Display status
                        current_time = time.time()
                        if current_time - last_display_time > 0.15:
                            left_bar = "=" * min(10, int(left_activity / 10))
                            right_bar = "=" * min(10, int(right_activity / 10))
                            
                            # show cursor velocity and click intent status
                            cursor_info = f"cursor: {self.cursor_velocity['x']:+.1f},{self.cursor_velocity['y']:+.1f}"
                            click_status = " [click-intent]" if self.click_intent_active else ""
                            
                            status = f"\remg l:{left_activity:+4.0f} {left_bar:10s} | r:{right_activity:+4.0f} {right_bar:10s} | [{gesture:12s}] | {cursor_info}{click_status}"
                            
                            print(status, end='', flush=True)
                            last_display_time = current_time

                        # Execute gesture actions
                        if gesture != 'rest':
                            recent = list(self.gesture_history)[-self.min_gesture_duration:]
                            if len(recent) >= self.min_gesture_duration and all(g == gesture for g in recent):
                                self.execute_action(gesture)
                                self.gesture_history.clear()

            except Exception as e:
                pass

            time.sleep(0.002)

    def show_stats(self):
        """Display session statistics"""
        print("\n\nsession statistics")
        print("-" * 60)

        if self.gesture_counts:
            total = sum(self.gesture_counts.values())
            print(f"Total actions: {total}")
            
            # Show detection method usage
            total_detections = self.threshold_count + self.ml_count
            if total_detections > 0:
                print(f"Threshold detection: {self.threshold_count} ({self.threshold_count/total_detections*100:.1f}%)")
                print(f"ML model detection:  {self.ml_count} ({self.ml_count/total_detections*100:.1f}%)")

            print("\nGestures performed:")
            for gesture, count in sorted(self.gesture_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {gesture:12s}: {count:3d}")
        else:
            print("No actions performed")

    def run(self):
        """Main run function"""
        if not self.serial_conn:
            print("no device connected")
            return

        # Calibrate both EMG and IMU
        if not self.calibrate_emg():
            return
        
        if not self.calibrate_imu():
            return

        print("\n" + "="*60)
        print("enhanced gesture + cursor controls")
        print("="*60)
        print("emg gestures:")
        print("  light flex left  -> left click")
        print("  light flex right -> right click")
        print("  both light flex  -> double click")
        print("  strong left      -> scroll up")
        print("  strong right     -> scroll down")
        print("  both strong      -> middle click")
        print("\ncursor control (flight style):")
        print("  lean forward  -> move cursor down")
        print("  lean backward -> move cursor up")
        print("  lean left     -> move cursor left")
        print("  lean right    -> move cursor right")
        print("  auto-slowdown when click detected")
        print("\nsystem:")
        if self.decision_tree:
            print("  using decision tree for complex emg gestures")
            print("  using thresholds for simple emg gestures")
        else:
            print("  using threshold detection only for emg")
        print("  imu-based cursor control enabled")
        print("  latency ~30ms for gestures, ~16ms for cursor")
        print("  flight controls with click-intent smoothing")
        print("\nmove mouse to corner to stop")
        print("press ctrl+c to exit")
        print("="*60)

        self.is_running = True

        # Start data reading thread
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

            print("\nenhanced control stopped")

def main():
    """Main entry point"""
    try:
        import pyautogui
    except ImportError:
        print("Installing pyautogui...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        import pyautogui

    controller = EnhancedEMGController()
    controller.run()

if __name__ == "__main__":
    main()
