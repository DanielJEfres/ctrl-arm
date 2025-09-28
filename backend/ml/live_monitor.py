
import serial
import serial.tools.list_ports
import numpy as np
import time
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def monitor_emg():
    print("="*60)
    print("LIVE EMG MONITOR")
    print("="*60)
    
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No devices found!")
        return
    
    port = None
    for p in ports:
        if any(x in p.description for x in ['XIAO', 'Arduino', 'USB Serial']):
            port = p.device
            break
    if not port:
        port = ports[0].device
    
    print(f"Connecting to {port}...")
    ser = serial.Serial(port, 115200, timeout=0.1)
    time.sleep(2)
    
    while ser.in_waiting:
        ser.readline()
    
    print("\n" + "="*60)
    print("MONITORING (Press Ctrl+C to stop)")
    print("="*60)
    print("\nLegend:")
    print("  STRONG = Strong signal (>200 above baseline)")
    print("  MEDIUM = Medium signal (100-200 above baseline)")
    print("  WEAK = Weak signal (50-100 above baseline)")
    print("  NONE = No signal (<50 above baseline)")
    print("-"*60)
    
    emg1_buffer = deque(maxlen=200)
    emg2_buffer = deque(maxlen=200)

    print("\nCalculating baseline (keep muscles relaxed)...")
    baseline_data_1 = []
    baseline_data_2 = []
    
    start_time = time.time()
    while time.time() - start_time < 2:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line and not line.startswith('#'):
                    values = line.split(',')
                    if len(values) >= 9:
                        baseline_data_1.append(int(values[1]))
                        baseline_data_2.append(int(values[2]))
            except:
                pass
    
    if baseline_data_1:
        baseline_1 = np.mean(baseline_data_1)
        baseline_2 = np.mean(baseline_data_2)
        noise_1 = np.std(baseline_data_1)
        noise_2 = np.std(baseline_data_2)
        
        print(f"\nBaseline established:")
        print(f"  Left:  {baseline_1:.0f} ± {noise_1:.0f}")
        print(f"  Right: {baseline_2:.0f} ± {noise_2:.0f}")
        print("\nNow flex your muscles!")
        print("-"*60)
    else:
        baseline_1 = 500
        baseline_2 = 500
        noise_1 = 10
        noise_2 = 10
    
    sample_count = 0
    gesture_detector = SimpleGestureDetector(baseline_1, baseline_2, noise_1, noise_2)

    try:
        while True:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            emg1 = int(values[1])
                            emg2 = int(values[2])

                            emg1_buffer.append(emg1)
                            emg2_buffer.append(emg2)

                            sample_count += 1

                            if sample_count % 20 == 0 and len(emg1_buffer) >= 50:
                                emg1_array = np.array(list(emg1_buffer)[-50:])
                                emg2_array = np.array(list(emg2_buffer)[-50:])

                                left_activity = np.mean(emg1_array) - baseline_1
                                right_activity = np.mean(emg2_array) - baseline_2

                                left_rms = np.sqrt(np.mean((emg1_array - baseline_1)**2))
                                right_rms = np.sqrt(np.mean((emg2_array - baseline_2)**2))

                                gesture = gesture_detector.detect(left_activity, right_activity)

                                left_indicator = get_indicator(left_activity)
                                right_indicator = get_indicator(right_activity)

                                display = f"\r{left_indicator} L: {emg1:4d} ({left_activity:+4.0f}) RMS:{left_rms:4.0f} | "
                                display += f"{right_indicator} R: {emg2:4d} ({right_activity:+4.0f}) RMS:{right_rms:4.0f} | "
                                display += f"[{gesture:12s}]"

                                print(display, end='')

                except Exception as e:
                    print(f"\nError: {e}")

    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("DIAGNOSTICS")
        print("="*60)
        
        if len(emg1_buffer) > 0:
            final_emg1 = np.array(emg1_buffer)
            final_emg2 = np.array(emg2_buffer)

            print(f"\nFinal statistics:")
            print(f"  Left EMG:")
            print(f"    Range: [{np.min(final_emg1):.0f}, {np.max(final_emg1):.0f}]")
            print(f"    Mean:  {np.mean(final_emg1):.0f}")
            print(f"    Std:   {np.std(final_emg1):.0f}")

            print(f"  Right EMG:")
            print(f"    Range: [{np.min(final_emg2):.0f}, {np.max(final_emg2):.0f}]")
            print(f"    Mean:  {np.mean(final_emg2):.0f}")
            print(f"    Std:   {np.std(final_emg2):.0f}")

            print("\nPotential issues:")

            if np.max(final_emg1) - np.min(final_emg1) < 50:
                print("  WARNING: Left sensor has very low variation - check connection")

            if np.max(final_emg2) - np.min(final_emg2) < 50:
                print("  WARNING: Right sensor has very low variation - check connection")

            if np.mean(final_emg1) < 100:
                print("  WARNING: Left sensor values very low - may need better skin contact")

            if np.mean(final_emg2) < 100:
                print("  WARNING: Right sensor values very low - may need better skin contact")

            if abs(np.mean(final_emg1) - np.mean(final_emg2)) < 10:
                print("  WARNING: Both sensors show similar values - might be cross-talk")
    
    finally:
        ser.close()

def get_indicator(activity):
    if activity > 200:
        return "STRONG"
    elif activity > 100:
        return "MEDIUM"
    elif activity > 50:
        return "WEAK"
    else:
        return "NONE"

class SimpleGestureDetector:

    def __init__(self, baseline_1, baseline_2, noise_1, noise_2):
        self.baseline_1 = baseline_1
        self.baseline_2 = baseline_2
        self.threshold_1 = baseline_1 + (3 * noise_1)
        self.threshold_2 = baseline_2 + (3 * noise_2)

    def detect(self, left_activity, right_activity):
        left_active = left_activity > 50
        right_active = right_activity > 50
        
        if left_active and right_active:
            return "BOTH"
        elif left_active:
            return "LEFT"
        elif right_active:
            return "RIGHT"
        else:
            return "REST"

if __name__ == "__main__":
    monitor_emg()


