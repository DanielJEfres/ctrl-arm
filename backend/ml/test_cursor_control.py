#!/usr/bin/env python3
"""
Test script for IMU cursor control
This script tests the cursor control without requiring EMG data
"""

import serial
import serial.tools.list_ports
import numpy as np
import pyautogui
import time
import threading
from collections import deque

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001

class CursorControlTester:
    def __init__(self):
        print("\n" + "="*60)
        print(" "*20 + "CURSOR CONTROL TESTER")
        print("="*60)
        
        self.serial_conn = None
        self.connect_device()
        
        # IMU settings
        self.imu_baseline = {'accel_x': 0, 'accel_y': 0, 'accel_z': 0}
        self.imu_calibrated = False
        
        # Cursor control settings
        self.cursor_sensitivity = 2.0
        self.cursor_deadzone = 0.05
        self.cursor_smoothing_factor = 0.3
        self.cursor_update_interval = 0.016  # 60 FPS
        
        # Smoothing
        self.cursor_velocity = {'x': 0, 'y': 0}
        self.cursor_position = {'x': 0, 'y': 0}
        self.target_cursor_velocity = {'x': 0, 'y': 0}
        
        self.is_running = False
        self.last_cursor_time = 0

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

    def calculate_cursor_movement(self, accel_x, accel_y, accel_z):
        """Calculate cursor movement based on IMU data"""
        if not self.imu_calibrated:
            return 0, 0
        
        # Calculate deviation from baseline
        delta_x = accel_x - self.imu_baseline['accel_x']
        delta_y = accel_y - self.imu_baseline['accel_y']
        delta_z = accel_z - self.imu_baseline['accel_z']
        
        # Map IMU to cursor movement
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

    def run_test(self):
        """Run the cursor control test"""
        if not self.serial_conn:
            print("❌ No device connected!")
            return
        
        # Calibrate IMU
        if not self.calibrate_imu():
            return
        
        print("\n" + "="*60)
        print("🎮 CURSOR CONTROL TEST")
        print("="*60)
        print("Move your chest to control the cursor:")
        print("  Lean forward  → Move cursor up")
        print("  Lean backward → Move cursor down")
        print("  Lean left     → Move cursor left")
        print("  Lean right    → Move cursor right")
        print("\nPress Ctrl+C to exit")
        print("="*60)
        
        self.is_running = True
        last_display_time = time.time()
        
        try:
            while self.is_running:
                if self.serial_conn.in_waiting:
                    try:
                        line = self.serial_conn.readline().decode('utf-8').strip()
                        if line and not line.startswith('#'):
                            values = line.split(',')
                            if len(values) >= 9:
                                accel_x = float(values[3])
                                accel_y = float(values[4])
                                accel_z = float(values[5])
                                
                                # Update cursor
                                self.update_cursor(accel_x, accel_y, accel_z)
                                
                                # Display status
                                current_time = time.time()
                                if current_time - last_display_time > 0.1:
                                    cursor_info = f"Cursor: {self.cursor_velocity['x']:+.1f},{self.cursor_velocity['y']:+.1f}"
                                    imu_info = f"IMU: {accel_x:+.2f},{accel_y:+.2f},{accel_z:+.2f}"
                                    
                                    status = f"\r{cursor_info} | {imu_info}"
                                    print(status, end='', flush=True)
                                    last_display_time = current_time
                    except:
                        pass
                
                time.sleep(0.001)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Test stopped!")
        finally:
            self.is_running = False
            if self.serial_conn:
                self.serial_conn.close()
            print("\n✅ Cursor control test completed!")

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
    
    tester = CursorControlTester()
    tester.run_test()

if __name__ == "__main__":
    main()
