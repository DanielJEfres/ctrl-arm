import serial
import csv
import time
import argparse
import os
from datetime import datetime
import threading
import queue
import numpy as np
from pathlib import Path
import signal
import sys

# Available action labels for training
ACTION_LABELS = [
    'rest',        # No muscle activity
    'flex',        # Bicep/forearm flex
    'hold',        # Sustained flex
    'click',       # Quick flex and release
    'double_click', # Two quick flexes
    'wrist_up',    # Wrist rotation up
    'wrist_down',  # Wrist rotation down
    'wrist_left',  # Wrist rotation left
    'wrist_right', # Wrist rotation right
    'pinch',       # Finger pinch gesture
    'fist',        # Full fist clench
    'wave',        # Wave motion
    'scroll_up',   # Scroll up gesture
    'scroll_down', # Scroll down gesture
]

class DataLogger:
    def __init__(self, port, baudrate=115200, output_dir='data/raw'):
        self.port = port
        self.baudrate = baudrate
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.serial_conn = None
        self.is_recording = False
        self.data_queue = queue.Queue()
        self.current_label = 'rest'
        self.session_data = []
        self.start_time = None
        
    def connect(self):
        """Establish serial connection with XIAO"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            time.sleep(2)  # Wait for Arduino to reset
            
            # Clear initial messages
            while self.serial_conn.in_waiting:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line.startswith('#'):
                    print(f"Device: {line}")
                    
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
            
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False
    
    def read_serial_thread(self):
        while self.is_recording:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8').strip()

                    if line and not line.startswith('#'):
                        try:
                            values = line.split(',')
                            if len(values) == 9:
                                timestamp = int(values[0])
                                emg = [int(values[i]) for i in range(1, 3)]
                                imu = [float(values[i]) for i in range(3, 9)]

                                data_point = {
                                    'timestamp_ms': timestamp,
                                    'emg1_left': emg[0],
                                    'emg2_right': emg[1],
                                    'accel_x': imu[0],
                                    'accel_y': imu[1],
                                    'accel_z': imu[2],
                                    'gyro_x': imu[3],
                                    'gyro_y': imu[4],
                                    'gyro_z': imu[5],
                                    'label': self.current_label
                                }

                                self.data_queue.put(data_point)

                        except (ValueError, IndexError) as e:
                            print(f"Parse error: {e} - Line: {line}")

            except Exception as e:
                print(f"Read error: {e}")
                time.sleep(0.001)
    
    def process_data_thread(self):
        while self.is_recording or not self.data_queue.empty():
            try:
                data_point = self.data_queue.get(timeout=0.1)
                self.session_data.append(data_point)

                if len(self.session_data) % 100 == 0:
                    elapsed = (time.time() - self.start_time) if self.start_time else 0
                    print(f"  Samples: {len(self.session_data)} | "
                          f"Time: {elapsed:.1f}s | "
                          f"Label: {self.current_label} | "
                          f"EMG-L: {data_point['emg1_left']:4d} | "
                          f"EMG-R: {data_point['emg2_right']:4d} | "
                          f"GyroY: {data_point['gyro_y']:6.2f}")

            except queue.Empty:
                continue
    
    def start_recording(self, label='rest', duration=None):
        if not self.serial_conn:
            print("Not connected! Call connect() first.")
            return False

        self.current_label = label
        self.session_data = []
        self.is_recording = True
        self.start_time = time.time()

        read_thread = threading.Thread(target=self.read_serial_thread)
        process_thread = threading.Thread(target=self.process_data_thread)

        read_thread.start()
        process_thread.start()

        print(f"\nRecording '{label}' action...")
        print(f"Press Ctrl+C to stop or wait {duration}s" if duration else "Press Ctrl+C to stop")

        try:
            if duration:
                time.sleep(duration)
                self.stop_recording()
            else:
                read_thread.join()
                process_thread.join()

        except KeyboardInterrupt:
            self.stop_recording()

        read_thread.join(timeout=1)
        process_thread.join(timeout=1)

        return True
    
    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        time.sleep(0.5)

        if self.session_data:
            filename = self.save_session()
            print(f"\nSaved {len(self.session_data)} samples to {filename}")
        else:
            print("\nNo data recorded")
    
    def save_session(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{self.current_label}_{timestamp}.csv"

        with open(filename, 'w', newline='') as f:
            if self.session_data:
                writer = csv.DictWriter(f, fieldnames=self.session_data[0].keys())
                writer.writeheader()
                writer.writerows(self.session_data)

        meta_file = self.output_dir / f"{self.current_label}_{timestamp}_meta.txt"
        with open(meta_file, 'w') as f:
            f.write(f"Label: {self.current_label}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Duration: {time.time() - self.start_time:.2f} seconds\n")
            f.write(f"Samples: {len(self.session_data)}\n")
            f.write(f"Sample Rate: ~{len(self.session_data)/(time.time() - self.start_time):.1f} Hz\n")

        return filename
    
    def record_multiple_sessions(self, session_plan):
        print("\n" + "="*50)
        print("Multi-Session Recording")
        print("="*50)

        for i, (label, duration, instruction) in enumerate(session_plan):
            print(f"\n[{i+1}/{len(session_plan)}] Next: {label.upper()}")
            print(f"Instruction: {instruction}")
            input("Press Enter when ready...")

            for j in range(3, 0, -1):
                print(f"  Starting in {j}...")
                time.sleep(1)

            print("  GO!")
            self.start_recording(label, duration)

            if i < len(session_plan) - 1:
                print("\nRelax for 3 seconds...")
                time.sleep(3)

        print("\nAll sessions complete!")
    
    def close(self):
        if self.serial_conn:
            self.serial_conn.close()
            print("Connection closed")


def interactive_mode(logger):
    while True:
        print("\n" + "="*50)
        print("EMG + IMU Data Logger - Interactive Mode")
        print("="*50)
        print("\nAvailable actions:")
        for i, label in enumerate(ACTION_LABELS, 1):
            print(f"  {i:2d}. {label}")
        print("\n  q. Quit")
        print("  m. Multi-session recording")
        print("  c. Calibration sequence")

        choice = input("\nSelect action to record (1-14, q, m, c): ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'm':
            session_plan = [
                ('rest', 5, 'Keep your arm relaxed'),
                ('flex', 5, 'Flex your bicep moderately'),
                ('hold', 8, 'Flex and hold for the duration'),
                ('click', 5, 'Perform quick flex-release clicks'),
                ('wrist_up', 5, 'Rotate wrist upward'),
                ('wrist_down', 5, 'Rotate wrist downward'),
                ('rest', 5, 'Relax again'),
            ]
            logger.record_multiple_sessions(session_plan)

        elif choice == 'c':
            print("\nCalibration sequence - follow the prompts")
            calibration_plan = [
                ('rest', 10, 'Keep arm completely relaxed on table'),
                ('flex', 3, 'Maximum comfortable flex'),
                ('rest', 3, 'Relax'),
                ('flex', 3, 'Light flex (30% effort)'),
                ('rest', 3, 'Relax'),
                ('flex', 3, 'Medium flex (60% effort)'),
                ('rest', 5, 'Final relaxation'),
            ]
            logger.record_multiple_sessions(calibration_plan)

        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(ACTION_LABELS):
                    label = ACTION_LABELS[idx]
                    duration = input(f"Duration in seconds (Enter for manual stop): ").strip()
                    duration = int(duration) if duration else None
                    logger.start_recording(label, duration)
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input")


def main():
    parser = argparse.ArgumentParser(description='EMG + IMU Data Logger for XIAO Sense')
    parser.add_argument('--port', type=str, help='Serial port (e.g., COM3, /dev/ttyACM0)')
    parser.add_argument('--label', type=str, choices=ACTION_LABELS,
                       help='Action label for this recording')
    parser.add_argument('--duration', type=int, default=None,
                       help='Recording duration in seconds (default: manual stop)')
    parser.add_argument('--output-dir', type=str, default='data/raw',
                       help='Output directory for CSV files')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode with menu')
    parser.add_argument('--list-ports', action='store_true',
                       help='List available serial ports')

    args = parser.parse_args()

    if args.list_ports:
        import serial.tools.list_ports
        print("\nAvailable serial ports:")
        for port in serial.tools.list_ports.comports():
            print(f"  {port.device}: {port.description}")
        return

    if not args.port:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())

        for port in ports:
            if 'XIAO' in port.description or 'Arduino' in port.description or 'USB Serial' in port.description:
                args.port = port.device
                print(f"Auto-detected port: {args.port}")
                break

        if not args.port:
            if ports:
                print("\nAvailable ports:")
                for i, port in enumerate(ports):
                    print(f"  {i+1}. {port.device}: {port.description}")
                choice = input("Select port number: ").strip()
                try:
                    args.port = ports[int(choice)-1].device
                except:
                    print("Invalid selection")
                    return
            else:
                print("No serial ports found!")
                return

    logger = DataLogger(args.port, output_dir=args.output_dir)

    if not logger.connect():
        return

    def signal_handler(sig, frame):
        print("\nStopping...")
        logger.stop_recording()
        logger.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        if args.interactive:
            interactive_mode(logger)
        elif args.label:
            logger.start_recording(args.label, args.duration)
        else:
            print("\nNo label specified. Entering interactive mode...")
            interactive_mode(logger)

    finally:
        logger.close()


if __name__ == '__main__':
    main()
