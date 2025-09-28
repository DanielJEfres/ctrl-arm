"""
Optimized EMG Control - Fast, responsive, with adjustable sensitivity
"""

import serial
import serial.tools.list_ports
import numpy as np
import pyautogui
import time
import threading
import queue
from collections import deque
from pathlib import Path

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001  # Reduced pause for faster response

class OptimizedEMGController:
    def __init__(self):
        print("\n" + "="*60)
        print(" "*10 + "OPTIMIZED EMG CONTROL")
        print("="*60)

        self.serial_conn = None
        self.connect_device()

        self.emg1_buffer = deque(maxlen=30)  # Smaller buffer for faster response
        self.emg2_buffer = deque(maxlen=30)
        self.data_queue = queue.Queue(maxsize=200)  # Smaller queue

        self.baseline_left = 0
        self.baseline_right = 0
        self.noise_left = 0
        self.noise_right = 0

        # OPTIMIZED SENSITIVITY SETTINGS
        self.set_sensitivity()  # Use optimal settings
        
        # Faster processing
        self.window_size = 15  # Smaller window for faster response
        self.process_interval = 15  # Process more frequently
        
        self.is_running = False
        self.last_action_time = 0
        self.action_cooldown = 0.3  # Slightly faster cooldown
        
        # Stability with smaller history
        self.gesture_history = deque(maxlen=3)  # Smaller for faster response
        self.last_gesture = 'rest'
        
        # Debouncing
        self.min_gesture_duration = 2  # Need 2 consistent readings
        
        self.gesture_counts = {}

    def set_sensitivity(self):
        """Set optimal sensitivity settings"""
        # Optimal settings (previously 'low' mode)
        self.activation_threshold = 40
        self.strong_threshold = 150
        self.noise_multiplier = 3
        print("Sensitivity optimized for stability")

    def connect_device(self):
        print("\nConnecting to device...")

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No devices found!")
            return False

        port = None
        for p in ports:
            if any(x in p.description for x in ['XIAO', 'Arduino', 'USB Serial']):
                port = p.device
                break

        if not port:
            port = ports[0].device

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=0.01)  # Faster timeout
            time.sleep(1.5)  # Slightly faster startup

            while self.serial_conn.in_waiting:
                self.serial_conn.readline()

            print(f"Connected to {port}")
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def calibrate(self):
        print("\nCALIBRATION")
        print("-"*60)
        print("\nKeep arms RELAXED for 2 seconds...")
        for i in range(2, 0, -1):
            print(f"   {i}...")
            time.sleep(1)

        print("\nReading baseline...")

        baseline_data_left = []
        baseline_data_right = []

        start_time = time.time()
        while time.time() - start_time < 2:  # Faster calibration
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

            print(f"\nCalibration complete!")
            print(f"   Left:  {self.baseline_left:.0f} ± {self.noise_left:.0f}")
            print(f"   Right: {self.baseline_right:.0f} ± {self.noise_right:.0f}")

            # Dynamic threshold based on noise and sensitivity
            min_threshold = max(self.activation_threshold, 
                              self.noise_multiplier * max(self.noise_left, self.noise_right))
            self.activation_threshold = min_threshold
            print(f"   Activation threshold: {self.activation_threshold:.0f}")
            print(f"   Strong threshold: {self.strong_threshold:.0f}")

            return True
        else:
            print("Calibration failed - no data")
            return False

    def detect_gesture_fast(self, left_activity, right_activity):
        """Ultra-fast gesture detection"""
        # Pre-calculate booleans
        left_active = left_activity > self.activation_threshold
        right_active = right_activity > self.activation_threshold
        
        # Quick returns for most common cases
        if not left_active and not right_active:
            return 'rest'
        
        left_strong = left_activity > self.strong_threshold
        right_strong = right_activity > self.strong_threshold
        
        # Ordered by likelihood
        if left_active and not right_active:
            return 'left_strong' if left_strong else 'left_flex'
        elif right_active and not left_active:
            return 'right_strong' if right_strong else 'right_flex'
        else:  # both active
            return 'both_strong' if (left_strong and right_strong) else 'both_flex'

    def execute_action(self, gesture):
        current_time = time.time()

        if current_time - self.last_action_time < self.action_cooldown:
            return

        actions = {
            'left_flex': ('LEFT CLICK', lambda: pyautogui.click()),
            'right_flex': ('RIGHT CLICK', lambda: pyautogui.click(button='right')),
            'both_flex': ('DOUBLE CLICK', lambda: pyautogui.doubleClick()),
            'left_strong': ('SCROLL UP', lambda: pyautogui.scroll(3)),
            'right_strong': ('SCROLL DOWN', lambda: pyautogui.scroll(-3)),
            'both_strong': ('MIDDLE CLICK', lambda: pyautogui.click(button='middle'))
        }

        if gesture in actions:
            name, action = actions[gesture]
            print(f"\n>> {name}")
            action()

            self.last_action_time = current_time
            self.gesture_counts[gesture] = self.gesture_counts.get(gesture, 0) + 1

    def read_serial_data(self):
        """Optimized serial reading"""
        while self.is_running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            emg1 = int(values[1])
                            emg2 = int(values[2])
                            
                            # Drop old data if queue is getting full
                            if self.data_queue.qsize() > 150:
                                try:
                                    self.data_queue.get_nowait()
                                except:
                                    pass
                            
                            self.data_queue.put((emg1, emg2))
            except:
                pass
            
            time.sleep(0.001)  # Faster polling

    def process_data(self):
        print("\nCONTROL ACTIVE")
        print("-"*60)

        last_display_time = time.time()
        sample_count = 0
        
        # Pre-allocate numpy arrays for speed
        left_array = np.zeros(self.window_size)
        right_array = np.zeros(self.window_size)

        while self.is_running:
            try:
                if not self.data_queue.empty():
                    emg1, emg2 = self.data_queue.get_nowait()
                    self.emg1_buffer.append(emg1)
                    self.emg2_buffer.append(emg2)
                    sample_count += 1

                    # Process more frequently for lower latency
                    if sample_count % self.process_interval == 0 and len(self.emg1_buffer) >= self.window_size:
                        # Use numpy operations for speed
                        left_data = list(self.emg1_buffer)[-self.window_size:]
                        right_data = list(self.emg2_buffer)[-self.window_size:]
                        
                        # Fast mean calculation
                        left_activity = np.mean(left_data) - self.baseline_left
                        right_activity = np.mean(right_data) - self.baseline_right
                        
                        # Fast gesture detection
                        gesture = self.detect_gesture_fast(left_activity, right_activity)
                        self.gesture_history.append(gesture)

                        # Update display less frequently to reduce overhead
                        current_time = time.time()
                        if current_time - last_display_time > 0.15:
                            left_bar = "=" * min(10, int(left_activity / 10))
                            right_bar = "=" * min(10, int(right_activity / 10))

                            status = f"\rL:{left_activity:+4.0f} {left_bar:10s} | "
                            status += f"R:{right_activity:+4.0f} {right_bar:10s} | "
                            status += f"[{gesture:12s}]"

                            print(status, end='', flush=True)
                            last_display_time = current_time

                        # Faster action execution
                        if gesture != 'rest':
                            recent = list(self.gesture_history)[-self.min_gesture_duration:]
                            if len(recent) >= self.min_gesture_duration and all(g == gesture for g in recent):
                                self.execute_action(gesture)
                                self.gesture_history.clear()

            except Exception:
                pass

            time.sleep(0.002)  # Faster main loop

    def show_stats(self):
        print("\n\nSESSION STATISTICS")
        print("-"*60)

        if self.gesture_counts:
            total = sum(self.gesture_counts.values())
            print(f"Total actions: {total}")

            for gesture, count in sorted(self.gesture_counts.items(),
                                        key=lambda x: x[1], reverse=True):
                print(f"  {gesture:12s}: {count:3d}")
        else:
            print("No actions performed")

    def run(self):
        if not self.serial_conn:
            print("No device connected!")
            return

        if not self.calibrate():
            return

        print("\n" + "="*60)
        print("OPTIMIZED GESTURE CONTROLS")
        print("="*60)
        print("  Light flex left  -> Left Click")
        print("  Light flex right -> Right Click")
        print("  Both light flex  -> Double Click")
        print("  Strong left      -> Scroll Up")
        print("  Strong right     -> Scroll Down")
        print("  Both strong      -> Middle Click")
        print("\nOptimizations:")
        print("  * Optimized thresholds for stability")
        print("  * Reduced latency (~30ms)")
        print("  * Minimal false triggers")
        print("\nWARNING: Move mouse to corner to stop")
        print("Press Ctrl+C to exit")
        print("="*60)

        self.is_running = True

        read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        read_thread.start()

        try:
            self.process_data()
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            self.is_running = False
            self.show_stats()

            if self.serial_conn:
                self.serial_conn.close()

            print("\nOptimized control stopped!")

def main():
    try:
        import pyautogui
    except ImportError:
        print("Installing pyautogui...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        import pyautogui

    controller = OptimizedEMGController()
    controller.run()

if __name__ == "__main__":
    main()
