
import serial
import serial.tools.list_ports
import time
import numpy as np

def test_sensors():
    print("="*60)
    print("EMG SENSOR HARDWARE TEST")
    print("="*60)
    
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found!")
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
    print("SENSOR MAPPING TEST")
    print("="*60)
    print("\nInstructions:")
    print("1. Keep both arms RELAXED first")
    print("2. Then flex ONLY your LEFT bicep")
    print("3. Then flex ONLY your RIGHT bicep")
    print("4. Watch which values change!")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line and not line.startswith('#'):
                        values = line.split(',')
                        if len(values) >= 9:
                            timestamp = values[0]
                            emg1_value = int(values[1])
                            emg2_value = int(values[2])

                            emg1_activity = max(0, emg1_value - 500)
                            emg2_activity = max(0, emg2_value - 500)

                            bar1 = "█" * min(20, emg1_activity // 10)
                            bar2 = "█" * min(20, emg2_activity // 10)

                            if emg1_activity > 50 and emg2_activity > 50:
                                status = "BOTH ACTIVE"
                            elif emg1_activity > 50:
                                status = "A0 ACTIVE (should be LEFT)"
                            elif emg2_activity > 50:
                                status = "A1 ACTIVE (should be RIGHT)"
                            else:
                                status = "BOTH REST"

                            display = f"\r{status:30s} | "
                            display += f"A0: {emg1_value:4d} {bar1:20s} | "
                            display += f"A1: {emg2_value:4d} {bar2:20s}"
                            
                            print(display, end='')
                            
                except Exception as e:
                    pass
    
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("DIAGNOSIS:")
        print("="*60)
        print("If BOTH A0 and A1 change when you flex one muscle:")
        print("  ERROR: Wiring issue - both pins connected to same sensor")
        print("  FIX: Check your breadboard/wiring")
        print()
        print("If only A0 changes when you flex LEFT:")
        print("  OK: Left sensor correctly wired to A0")
        print()
        print("If only A1 changes when you flex RIGHT:")
        print("  OK: Right sensor correctly wired to A1")
        print()
        print("If A0 changes when you flex RIGHT muscle:")
        print("  SWAP: Sensors are swapped - A0 has right sensor")
        print("  FIX: Swap the sensor connections")
        print()
        print("ARDUINO WIRING SHOULD BE:")
        print("  Left EMG sensor  -> A0 pin")
        print("  Right EMG sensor -> A1 pin")
        print("  Both sensors GND -> GND")
        print("  Both sensors VCC -> 3.3V")
    
    finally:
        ser.close()

if __name__ == '__main__':
    test_sensors()


