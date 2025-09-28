#!/usr/bin/env python3
"""
Port Scanner for Ctrl-ARM
Scans all available serial ports and tests connections
"""

import serial
import serial.tools.list_ports
import time
import sys

def scan_ports():
    """Scan all available serial ports"""
    print("🔍 Scanning for serial ports...")
    print("=" * 60)
    
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("❌ No serial ports found!")
        print("\n🔧 Troubleshooting:")
        print("   • Check if XIAO Sense is connected via USB")
        print("   • Try a different USB cable")
        print("   • Try a different USB port")
        print("   • Check if device is powered on")
        return []
    
    print(f"📋 Found {len(ports)} port(s):")
    print()
    
    for i, port in enumerate(ports):
        print(f"{i+1:2d}. Device: {port.device}")
        print(f"     Description: {port.description}")
        print(f"     Hardware ID: {port.hwid}")
        print(f"     Manufacturer: {getattr(port, 'manufacturer', 'Unknown')}")
        print(f"     Product: {getattr(port, 'product', 'Unknown')}")
        print(f"     Serial Number: {getattr(port, 'serial_number', 'Unknown')}")
        print()
    
    return ports

def test_port(port_device, baudrate=115200):
    """Test connection to a specific port"""
    print(f"🔗 Testing {port_device} at {baudrate} baud...")
    
    try:
        # Try to open the port
        ser = serial.Serial(port_device, baudrate, timeout=1.0)
        time.sleep(1)  # Give it time to initialize
        
        print(f"✓ Successfully opened {port_device}")
        
        # Clear any existing data
        ser.reset_input_buffer()
        time.sleep(0.5)
        
        # Try to read data
        print("📡 Looking for data...")
        data_found = False
        sample_data = []
        
        start_time = time.time()
        while time.time() - start_time < 5:  # Wait up to 5 seconds
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        sample_data.append(line)
                        data_found = True
                        print(f"📊 Data: {line[:80]}{'...' if len(line) > 80 else ''}")
                        
                        # If we get 3 lines, that's enough
                        if len(sample_data) >= 3:
                            break
                except Exception as e:
                    print(f"⚠️  Error reading data: {e}")
                    break
            time.sleep(0.1)
        
        ser.close()
        
        if data_found:
            print(f"✅ {port_device} is working! Found {len(sample_data)} data lines")
            return True
        else:
            print(f"⚠️  {port_device} opened but no data received")
            print("   • Check if XIAO firmware is uploaded")
            print("   • Verify baudrate is correct (115200)")
            print("   • Make sure device is sending data")
            return False
            
    except serial.SerialException as e:
        print(f"❌ Failed to open {port_device}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with {port_device}: {e}")
        return False

def test_all_ports(ports):
    """Test all available ports"""
    print("🧪 Testing all ports...")
    print("=" * 60)
    
    working_ports = []
    
    for i, port in enumerate(ports):
        print(f"\n[{i+1}/{len(ports)}] Testing {port.device}")
        print("-" * 40)
        
        if test_port(port.device):
            working_ports.append(port)
    
    return working_ports

def main():
    """Main function"""
    print("🔍 Ctrl-ARM Port Scanner")
    print("=" * 60)
    print()
    
    # Scan for ports
    ports = scan_ports()
    
    if not ports:
        return
    
    # Test all ports
    working_ports = test_all_ports(ports)
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    if working_ports:
        print(f"✅ Found {len(working_ports)} working port(s):")
        for port in working_ports:
            print(f"   • {port.device} - {port.description}")
        
        print(f"\n🎯 Recommended port: {working_ports[0].device}")
        print(f"   Use this in your cursor test: {working_ports[0].device}")
    else:
        print("❌ No working ports found!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check USB connection")
        print("2. Verify XIAO Sense is powered on")
        print("3. Upload the Arduino firmware:")
        print("   - Open hardware/xiao_data_streamer/xiao_data_streamer.ino")
        print("   - Upload to XIAO Sense board")
        print("4. Try different USB cable/port")
        print("5. Check if another program is using the port")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Port scan cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
