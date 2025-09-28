  import serial
import csv
import time
import argparse
import os
from datetime import datetime
import threading
import queue
import numpy as np
import pandas as pd
from pathlib import Path
import signal
import sys

ACTION_LABELS = [
    'rest',
    'left_single',
    'right_single',
    'left_double',
    'right_double',
    'left_hold',
    'right_hold',
    'both_flex',
    'left_then_right',
    'right_then_left',
    'left_hard',
    'right_hard'
]

CALIBRATION_THRESHOLDS = {
    'baseline_left': 0,
    'baseline_right': 0,
    'mvc_left': 0,        # Maximum voluntary contraction
    'mvc_right': 0,
    'light_threshold_left': 0,
    'medium_threshold_left': 0,
    'hard_threshold_left': 0,
    'light_threshold_right': 0,
    'medium_threshold_right': 0,
    'hard_threshold_right': 0
}

class DataLogger:
    def __init__(self, port, baudrate=115200, output_dir=None):
        self.port = port
        self.baudrate = baudrate

        # Default to project root data/raw if no path provided
        if output_dir is None:
            script_dir = Path(__file__).parent.parent  # Go up from hardware/ to project root
            output_dir = script_dir / 'data' / 'raw'

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.serial_conn = None
        self.is_recording = False
        self.data_queue = queue.Queue()
        self.current_label = 'rest'
        self.session_data = []
        self.start_time = None
        self.gesture_counts = {}

        # Load existing gesture counts
        self.load_gesture_counter()
        
    def connect(self):
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            time.sleep(2)
            
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

        # Update and display gesture counter
        self.update_gesture_counter()

        return filename

    def update_gesture_counter(self):
        """Update and display count of recorded gestures"""
        if not hasattr(self, 'gesture_counts'):
            self.gesture_counts = {}

        # Count existing files by gesture
        if self.output_dir.exists():
            for csv_file in self.output_dir.glob("*.csv"):
                gesture = csv_file.stem.split('_')[0]  # Get gesture name from filename
                self.gesture_counts[gesture] = self.gesture_counts.get(gesture, 0) + 1

        # Display current counts
        print(f"\n📊 Gesture Recording Progress:")
        print(f"{'='*40}")

        total_files = 0
        for gesture in sorted(self.gesture_counts.keys()):
            count = self.gesture_counts[gesture]
            total_files += count
            status = "✅" if count >= 5 else "🔄"  # Mark as good if >= 5 examples
            print(f"  {gesture:<15} | {count:2d} examples {status}")

        print(f"{'='*40}")
        print(f"📈 Total: {total_files} gesture recordings")

        # Save counter to file for persistence
        counter_file = self.output_dir / "gesture_counts.json"
        try:
            import json
            with open(counter_file, 'w') as f:
                json.dump(self.gesture_counts, f, indent=2)
        except Exception as e:
            print(f"Could not save counter file: {e}")

        return total_files

    def load_gesture_counter(self):
        """Load existing gesture counts from file"""
        counter_file = self.output_dir / "gesture_counts.json"
        if counter_file.exists():
            try:
                import json
                with open(counter_file, 'r') as f:
                    self.gesture_counts = json.load(f)
                print(f"📊 Loaded gesture counts: {len(self.gesture_counts)} gestures tracked")
            except Exception as e:
                print(f"Could not load gesture counter: {e}")
                self.gesture_counts = {}

    def record_multiple_sessions(self, session_plan):
        print("\nMulti-Session Recording")
        print("-" * 23)

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
    
    def get_calibration_thresholds(self):
        return CALIBRATION_THRESHOLDS.copy()

    def close(self):
        if self.serial_conn:
            self.serial_conn.close()
            print("Connection closed")

    def calibrate_thresholds(self, calibration_data=None):
        global CALIBRATION_THRESHOLDS

        if calibration_data is None:
            # Use existing session data if available
            if not hasattr(self, 'calibration_sessions') or not self.calibration_sessions:
                print("No calibration data available. Run calibration first.")
                return False

            calibration_data = []
            for session in self.calibration_sessions:
                calibration_data.extend(session)

        if not calibration_data:
            print("No calibration data provided")
            return False

        # Convert to DataFrame for analysis
        df = pd.DataFrame(calibration_data)

        # Calculate baselines (rest periods)
        rest_data_left = df[df['label'] == 'rest']['emg1_left']
        rest_data_right = df[df['label'] == 'rest']['emg2_right']

        if len(rest_data_left) == 0 or len(rest_data_right) == 0:
            print("Insufficient rest data for calibration")
            return False

        baseline_left = rest_data_left.mean() + rest_data_left.std()
        baseline_right = rest_data_right.mean() + rest_data_right.std()

        # Calculate MVC (maximum voluntary contraction)
        mvc_left = df[df['label'] == 'left_hard']['emg1_left'].max()
        mvc_right = df[df['label'] == 'right_hard']['emg2_right'].max()

        if mvc_left <= baseline_left or mvc_right <= baseline_right:
            print("Invalid MVC values detected")
            return False

        # Calculate intensity thresholds as percentages of MVC
        mvc_range_left = mvc_left - baseline_left
        mvc_range_right = mvc_right - baseline_right

        thresholds = {
            'baseline_left': float(baseline_left),
            'baseline_right': float(baseline_right),
            'mvc_left': float(mvc_left),
            'mvc_right': float(mvc_right),
            'light_threshold_left': float(baseline_left + (mvc_range_left * 0.3)),
            'medium_threshold_left': float(baseline_left + (mvc_range_left * 0.6)),
            'hard_threshold_left': float(baseline_left + (mvc_range_left * 0.9)),
            'light_threshold_right': float(baseline_right + (mvc_range_right * 0.3)),
            'medium_threshold_right': float(baseline_right + (mvc_range_right * 0.6)),
            'hard_threshold_right': float(baseline_right + (mvc_range_right * 0.9))
        }

        # Update global thresholds
        CALIBRATION_THRESHOLDS.update(thresholds)

        # Save thresholds to file
        thresholds_file = self.output_dir / "calibration_thresholds.json"
        import json
        with open(thresholds_file, 'w') as f:
            json.dump(thresholds, f, indent=2)

        print("Calibration completed!")
        print(f"  Left MVC: {mvc_left:.1f} (baseline: {baseline_left:.1f})")
        print(f"  Right MVC: {mvc_right:.1f} (baseline: {baseline_right:.1f})")
        print(f"  Light threshold: {thresholds['light_threshold_left']:.1f}/{thresholds['light_threshold_right']:.1f}")
        print(f"  Medium threshold: {thresholds['medium_threshold_left']:.1f}/{thresholds['medium_threshold_right']:.1f}")
        print(f"  Hard threshold: {thresholds['hard_threshold_left']:.1f}/{thresholds['hard_threshold_right']:.1f}")
        print(f"  Thresholds saved to: {thresholds_file}")

        return True

    def load_calibration_thresholds(self):
        global CALIBRATION_THRESHOLDS

        thresholds_file = self.output_dir / "calibration_thresholds.json"
        if thresholds_file.exists():
            try:
                import json
                with open(thresholds_file, 'r') as f:
                    loaded_thresholds = json.load(f)
                    CALIBRATION_THRESHOLDS.update(loaded_thresholds)
                print(f"Loaded calibration thresholds from {thresholds_file}")
                return True
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Calibration file corrupted ({e}). Please recalibrate.")
                return False
        else:
            print("No calibration file found. Run calibration first.")
            return False

    def run_calibration_sequence(self):
        print("\nCalibration Sequence")
        print("-" * 20)
        print("This will set up your personalized muscle thresholds.")
        print("Follow the instructions for best results.\n")

        calibration_sessions = []

        # Step 1: Rest baseline
        print("Step 1: REST (10 seconds)")
        print("Keep your arm completely relaxed on the table.")
        input("Press Enter when ready...")
        self.start_recording('rest', 10)
        calibration_sessions.append(self.session_data.copy())
        print("Rest baseline recorded\n")

        # Step 2: Maximum left flex
        print("Step 2: MAXIMUM LEFT FLEX (5 seconds)")
        print("Flex your LEFT bicep as HARD as you comfortably can.")
        input("Press Enter when ready...")
        self.start_recording('left_hard', 5)
        calibration_sessions.append(self.session_data.copy())
        print("Left maximum recorded\n")

        # Step 3: Rest
        print("Step 3: REST (3 seconds)")
        print("Completely relax your arm.")
        input("Press Enter when ready...")
        self.start_recording('rest', 3)
        calibration_sessions.append(self.session_data.copy())
        print("Rest recorded\n")

        # Step 4: Light left flex (30% effort)
        print("Step 4: LIGHT LEFT FLEX (3 seconds)")
        print("Flex your LEFT bicep at about 30% of maximum effort.")
        input("Press Enter when ready...")
        self.start_recording('left_single', 3)
        calibration_sessions.append(self.session_data.copy())
        print("Light left flex recorded\n")

        # Step 5: Rest
        print("Step 5: REST (3 seconds)")
        print("Completely relax your arm.")
        input("Press Enter when ready...")
        self.start_recording('rest', 3)
        calibration_sessions.append(self.session_data.copy())
        print("Rest recorded\n")

        # Step 6: Maximum right flex
        print("Step 6: MAXIMUM RIGHT FLEX (5 seconds)")
        print("Flex your RIGHT bicep as HARD as you comfortably can.")
        input("Press Enter when ready...")
        self.start_recording('right_hard', 5)
        calibration_sessions.append(self.session_data.copy())
        print("Right maximum recorded\n")

        # Step 7: Rest
        print("Step 7: REST (3 seconds)")
        print("Completely relax your arm.")
        input("Press Enter when ready...")
        self.start_recording('rest', 3)
        calibration_sessions.append(self.session_data.copy())
        print("Rest recorded\n")

        # Step 8: Light right flex (30% effort)
        print("Step 8: LIGHT RIGHT FLEX (3 seconds)")
        print("Flex your RIGHT bicep at about 30% of maximum effort.")
        input("Press Enter when ready...")
        self.start_recording('right_single', 3)
        calibration_sessions.append(self.session_data.copy())
        print("Light right flex recorded\n")

        # Step 9: Final rest
        print("Step 9: FINAL REST (5 seconds)")
        print("Keep your arm completely relaxed.")
        input("Press Enter when ready...")
        self.start_recording('rest', 5)
        calibration_sessions.append(self.session_data.copy())
        print("Final rest recorded\n")

        # Store calibration sessions for threshold calculation
        self.calibration_sessions = calibration_sessions

        # Calculate and save thresholds
        all_calibration_data = []
        for session in calibration_sessions:
            all_calibration_data.extend(session)

        success = self.calibrate_thresholds(all_calibration_data)
        if success:
            print("\nCalibration complete! You can now collect training data.")
            return True
        else:
            print("\nCalibration failed. Please try again.")
            return False


def interactive_mode(logger):
    while True:
        print("\nData Logger - Interactive Mode")
        print("-" * 35)
        print("\nAvailable actions:")
        for i, label in enumerate(ACTION_LABELS, 1):
            print(f"  {i:2d}. {label}")
        print("\n  q. Quit")
        print("  m. Multi-session recording")
        print("  c. Run calibration sequence")
        print("  l. Load existing calibration")
        print("  p. Show progress (gesture counts)")

        choice = input("\nSelect action to record (1-14, q, m, c, l, p): ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'm':
            session_plan = [
                ('rest', 5, 'Keep your arm relaxed'),
                ('left_single', 5, 'Quick tap flex on left bicep'),
                ('right_single', 5, 'Quick tap flex on right bicep'),
                ('left_double', 5, 'Two quick taps on left'),
                ('right_double', 5, 'Two quick taps on right'),
                ('left_hold', 8, 'Sustained flex on left'),
                ('right_hold', 8, 'Sustained flex on right'),
                ('both_flex', 8, 'Simultaneous left+right flex'),
                ('left_then_right', 8, 'Left tap then right tap'),
                ('right_then_left', 8, 'Right tap then left tap'),
                ('left_hard', 8, 'High intensity left flex'),
                ('right_hard', 8, 'High intensity right flex'),
                ('rest', 5, 'Relax again'),
            ]
            logger.record_multiple_sessions(session_plan)

        elif choice == 'c':
            print("\nCalibration sequence - follow the prompts")
            calibration_plan = [
                ('rest', 10, 'Keep arm completely relaxed on table'),
                ('left_hard', 3, 'Maximum comfortable left flex'),
                ('rest', 3, 'Relax'),
                ('left_single', 3, 'Light left flex (30% effort)'),
                ('rest', 3, 'Relax'),
                ('right_hard', 3, 'Maximum comfortable right flex'),
                ('rest', 3, 'Relax'),
                ('right_single', 3, 'Light right flex (30% effort)'),
                ('rest', 5, 'Final relaxation'),
            ]
            logger.record_multiple_sessions(calibration_plan)

        elif choice == 'l':
            print("\nLoading calibration thresholds...")
            if logger.load_calibration_thresholds():
                print("Calibration loaded successfully!")
                print("You can now collect training data with personalized thresholds.")
            else:
                print("Failed to load calibration. Run calibration first.")

        elif choice == 'p':
            print("\nCurrent gesture recording progress:")
            print("=" * 40)
            logger.update_gesture_counter()
            input("\nPress Enter to continue...")

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
    parser.add_argument('--output-dir', type=str, default=None,
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

    # Use args.output_dir if provided, otherwise default to project root data/raw
    logger = DataLogger(args.port, output_dir=args.output_dir)

    if not logger.connect():
        return

    # Try to load existing calibration
    logger.load_calibration_thresholds()

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
