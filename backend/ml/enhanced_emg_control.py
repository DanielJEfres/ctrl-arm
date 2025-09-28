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
        print(" "*15 + "ENHANCED EMG + IMU CONTROL")
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
        
        # IMU cursor control settings
        self.cursor_sensitivity = 2.0  # Adjust this for cursor speed
        self.cursor_deadzone = 0.05   # Minimum movement to register
        self.cursor_smoothing_factor = 0.3  # Higher = smoother, lower = more responsive
        
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

    def load_model(self):
        """Load the existing EMG decision tree model"""
        model_path = Path(__file__).parent / "emg_model.pkl"
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.decision_tree = data['model']
                    self.scaler = data['scaler']
                    print("✓ Loaded decision tree model for EMG gestures")
            except Exception as e:
                print(f"✗ Failed to load ML model: {e}")
                self.decision_tree = None
        else:
            print("⚠ Using threshold detection only for EMG gestures")
            self.decision_tree = None

    def connect_device(self):
        """Connect to the XIAO device"""
        print("\n🔌 Connecting to device...")

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("❌ No devices found!")
            return False

        print("📋 Available ports:")
        for i, p in enumerate(ports):
            print(f"   {i+1}. {p.device} - {p.description}")

        port = None
        
        # Try to find XIAO/Arduino ports first
        for p in ports:
            if any(x in p.description.lower() for x in ['xiao', 'arduino', 'usb serial', 'usb-serial', 'ch340', 'cp210', 'ftdi']):
                port = p.device
                print(f"🎯 Found potential device: {p.device} - {p.description}")
                break

        # If no specific device found, let user choose
        if not port:
            print("\n🤔 No XIAO/Arduino device auto-detected.")
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
                        print(f"❌ Please enter a number between 1 and {len(ports)}")
                except ValueError:
                    print("❌ Please enter a valid number")
                except KeyboardInterrupt:
                    print("\n👋 Exiting...")
                    return False

        print(f"\n🔗 Attempting to connect to {port}...")

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=0.01)
            time.sleep(2)  # Give more time for connection

            # Clear any existing data
            print("🧹 Clearing buffer...")
            time.sleep(0.5)
            while self.serial_conn.in_waiting:
                self.serial_conn.readline()

            print(f"✓ Connected to {port}")
            print("📡 Waiting for data...")
            
            # Test if we're getting data
            test_start = time.time()
            while time.time() - test_start < 3:
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('#'):
                        print(f"📊 Sample data: {line[:50]}...")
                        return True
                time.sleep(0.1)
            
            print("⚠️  No data received. Check if XIAO is running the correct firmware.")
            return True  # Still return True, might work during calibration

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("\n🔧 Troubleshooting tips:")
            print("   • Check USB cable connection")
            print("   • Verify XIAO Sense is powered on")
            print("   • Try a different USB port")
            print("   • Make sure Arduino firmware is uploaded")
            print("   • Check if another program is using the port")
            return False

    def calibrate_emg(self):
        """Calibrate EMG sensors for personalized thresholds"""
        print("\n📊 EMG Calibration")
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

            print(f"\n✓ EMG Calibration complete!")
            print(f"   Left:  {self.baseline_left:.0f} ± {self.noise_left:.0f}")
            print(f"   Right: {self.baseline_right:.0f} ± {self.noise_right:.0f}")

            # Adjust threshold based on noise
            min_threshold = max(40, self.noise_multiplier * max(self.noise_left, self.noise_right))
            self.activation_threshold = min_threshold
            print(f"   Activation threshold: {self.activation_threshold:.0f}")

            return True
        else:
            print("❌ EMG calibration failed - no data")
            return False

    def calibrate_imu(self):
        """Calibrate IMU for cursor control"""
        print("\n🎯 IMU Calibration for Cursor Control")
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
            self.imu_baseline['accel_x'] = np.mean(imu_data['accel_x'])
            self.imu_baseline['accel_y'] = np.mean(imu_data['accel_y'])
            self.imu_baseline['accel_z'] = np.mean(imu_data['accel_z'])
            
            print(f"\n✓ IMU Calibration complete!")
            print(f"   X: {self.imu_baseline['accel_x']:.3f}")
            print(f"   Y: {self.imu_baseline['accel_y']:.3f}")
            print(f"   Z: {self.imu_baseline['accel_z']:.3f}")
            print("\n🎮 Cursor Control Mapping:")
            print("   Lean forward  → Move cursor up")
            print("   Lean backward → Move cursor down")
            print("   Lean left     → Move cursor left")
            print("   Lean right    → Move cursor right")
            
            self.imu_calibrated = True
            return True
        else:
            print("❌ IMU calibration failed - no data")
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
        """Calculate cursor movement based on IMU data"""
        if not self.imu_calibrated:
            return 0, 0
        
        # Calculate deviation from baseline
        delta_x = accel_x - self.imu_baseline['accel_x']
        delta_y = accel_y - self.imu_baseline['accel_y']
        delta_z = accel_z - self.imu_baseline['accel_z']
        
        # Map IMU to cursor movement
        # X-axis: left/right lean -> cursor left/right
        # Y-axis: forward/back lean -> cursor up/down (inverted for natural feel)
        cursor_delta_x = delta_x * self.cursor_sensitivity
        cursor_delta_y = -delta_y * self.cursor_sensitivity  # Inverted for natural feel
        
        # Apply deadzone
        if abs(cursor_delta_x) < self.cursor_deadzone:
            cursor_delta_x = 0
        if abs(cursor_delta_y) < self.cursor_deadzone:
            cursor_delta_y = 0
        
        return cursor_delta_x, cursor_delta_y

    def smooth_cursor_movement(self, target_x, target_y):
        """Apply smoothing to cursor movement for natural feel"""
        # Update target velocity
        self.target_cursor_velocity['x'] = target_x
        self.target_cursor_velocity['y'] = target_y
        
        # Smooth velocity changes
        self.cursor_velocity['x'] += (self.target_cursor_velocity['x'] - self.cursor_velocity['x']) * self.cursor_smoothing_factor
        self.cursor_velocity['y'] += (self.target_cursor_velocity['y'] - self.cursor_velocity['y']) * self.cursor_smoothing_factor
        
        # Update position
        self.cursor_position['x'] += self.cursor_velocity['x']
        self.cursor_position['y'] += self.cursor_velocity['y']
        
        return self.cursor_position['x'], self.cursor_position['y']

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
        
        # Move cursor if there's significant movement
        if abs(smooth_delta_x) > 0.1 or abs(smooth_delta_y) > 0.1:
            try:
                current_x, current_y = pyautogui.position()
                new_x = max(0, min(pyautogui.size().width, current_x + smooth_delta_x))
                new_y = max(0, min(pyautogui.size().height, current_y + smooth_delta_y))
                pyautogui.moveTo(new_x, new_y)
            except:
                pass  # Ignore cursor movement errors
        
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
        print("\n🎮 Enhanced Control Active")
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
                            
                            # Show cursor velocity
                            cursor_info = f"Cursor: {self.cursor_velocity['x']:+.1f},{self.cursor_velocity['y']:+.1f}"
                            
                            status = f"\rEMG L:{left_activity:+4.0f} {left_bar:10s} | R:{right_activity:+4.0f} {right_bar:10s} | [{gesture:12s}] | {cursor_info}"
                            
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
        print("\n\n📊 Session Statistics")
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
            print("❌ No device connected!")
            return

        # Calibrate both EMG and IMU
        if not self.calibrate_emg():
            return
        
        if not self.calibrate_imu():
            return

        print("\n" + "="*60)
        print("🎮 ENHANCED GESTURE + CURSOR CONTROLS")
        print("="*60)
        print("EMG Gestures:")
        print("  Light flex left  → Left click")
        print("  Light flex right → Right click")
        print("  Both light flex  → Double click")
        print("  Strong left      → Scroll up")
        print("  Strong right     → Scroll down")
        print("  Both strong      → Middle click")
        print("\nCursor Control:")
        print("  Lean forward  → Move cursor up")
        print("  Lean backward → Move cursor down")
        print("  Lean left     → Move cursor left")
        print("  Lean right    → Move cursor right")
        print("\nSystem:")
        if self.decision_tree:
            print("  ✓ Using decision tree for complex EMG gestures")
            print("  ✓ Using thresholds for simple EMG gestures")
        else:
            print("  ⚠ Using threshold detection only for EMG")
        print("  ✓ IMU-based cursor control enabled")
        print("  ✓ Latency ~30ms for gestures, ~16ms for cursor")
        print("\n⚠️  Move mouse to corner to stop")
        print("Press Ctrl+C to exit")
        print("="*60)

        self.is_running = True

        # Start data reading thread
        read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        read_thread.start()

        try:
            self.process_data()
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping...")
        finally:
            self.is_running = False
            self.show_stats()

            if self.serial_conn:
                self.serial_conn.close()

            print("\n✅ Enhanced control stopped!")

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
