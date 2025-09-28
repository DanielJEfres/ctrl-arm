#!/usr/bin/env python3
"""
Ctrl-ARM Demo Script
Demonstrates the enhanced EMG + IMU control system
"""

import time
import sys
from pathlib import Path

def print_banner():
    """Print the demo banner"""
    print("\n" + "="*70)
    print(" "*25 + "CTRL-ARM DEMO")
    print("="*70)
    print()
    print("🎮 Enhanced Muscle + Movement Control Demo")
    print("   Combining EMG gestures with IMU cursor control")
    print()

def print_features():
    """Print feature overview"""
    print("✨ Features Demonstrated:")
    print()
    print("🦾 EMG Gesture Control:")
    print("   • Left bicep flex     → Left click")
    print("   • Right bicep flex    → Right click") 
    print("   • Both biceps flex    → Double click")
    print("   • Strong left flex    → Scroll up")
    print("   • Strong right flex   → Scroll down")
    print("   • Both strong flex    → Middle click")
    print()
    print("🎯 IMU Cursor Control:")
    print("   • Lean forward        → Move cursor up")
    print("   • Lean backward       → Move cursor down")
    print("   • Lean left           → Move cursor left")
    print("   • Lean right          → Move cursor right")
    print()
    print("🧠 AI Features:")
    print("   • Decision tree ML model (89.87% accuracy)")
    print("   • Personalized calibration")
    print("   • Real-time processing (200Hz)")
    print("   • Smooth cursor movement (60 FPS)")
    print()

def print_requirements():
    """Print hardware requirements"""
    print("🔧 Hardware Requirements:")
    print()
    print("Required:")
    print("   • MyoWare EMG sensors (2x)")
    print("   • Seeed Studio XIAO Sense board")
    print("   • USB cable")
    print("   • Computer with Python 3.7+")
    print()
    print("Setup:")
    print("   • Attach EMG sensors to biceps")
    print("   • Mount XIAO Sense on chest (IMU for cursor)")
    print("   • Connect via USB")
    print()

def print_usage():
    """Print usage instructions"""
    print("🚀 How to Run:")
    print()
    print("1. Basic Demo (EMG only):")
    print("   python emg_control.py")
    print()
    print("2. Enhanced Demo (EMG + IMU):")
    print("   python enhanced_emg_control.py")
    print()
    print("3. Cursor Test Only:")
    print("   python test_cursor_control.py")
    print()
    print("4. Interactive Launcher:")
    print("   python launcher.py")
    print()

def print_tips():
    """Print usage tips"""
    print("💡 Tips for Best Results:")
    print()
    print("EMG Gestures:")
    print("   • Keep muscles relaxed during calibration")
    print("   • Use consistent flex strength")
    print("   • Record 20-30 examples per gesture")
    print("   • Recalibrate if accuracy drops")
    print()
    print("Cursor Control:")
    print("   • Sit in neutral position during IMU calibration")
    print("   • Mount XIAO Sense securely on chest")
    print("   • Start with low sensitivity, adjust as needed")
    print("   • Use smooth, deliberate movements")
    print()

def print_troubleshooting():
    """Print troubleshooting tips"""
    print("🔧 Troubleshooting:")
    print()
    print("No Device Found:")
    print("   • Check USB connection")
    print("   • Verify XIAO Sense is powered")
    print("   • Try different USB port")
    print()
    print("Poor Gesture Recognition:")
    print("   • Recalibrate EMG sensors")
    print("   • Check sensor placement")
    print("   • Record more training data")
    print()
    print("Cursor Issues:")
    print("   • Recalibrate IMU")
    print("   • Adjust sensitivity in config")
    print("   • Check mounting position")
    print()

def main():
    """Main demo function"""
    print_banner()
    
    while True:
        print("Choose what you'd like to see:")
        print()
        print("1. Feature Overview")
        print("2. Hardware Requirements")
        print("3. Usage Instructions")
        print("4. Tips for Best Results")
        print("5. Troubleshooting")
        print("6. Run Enhanced Demo")
        print("7. Run Cursor Test")
        print("8. Exit")
        print()
        
        try:
            choice = input("Enter your choice (1-8): ").strip()
            print()
            
            if choice == "1":
                print_features()
            elif choice == "2":
                print_requirements()
            elif choice == "3":
                print_usage()
            elif choice == "4":
                print_tips()
            elif choice == "5":
                print_troubleshooting()
            elif choice == "6":
                print("🚀 Starting Enhanced Demo...")
                print("Press Ctrl+C to stop the demo")
                print()
                try:
                    from enhanced_emg_control import EnhancedEMGController
                    controller = EnhancedEMGController()
                    controller.run()
                except KeyboardInterrupt:
                    print("\n🛑 Demo stopped by user")
                except Exception as e:
                    print(f"❌ Error running demo: {e}")
            elif choice == "7":
                print("🎯 Starting Cursor Test...")
                print("Press Ctrl+C to stop the test")
                print()
                try:
                    from test_cursor_control import CursorControlTester
                    tester = CursorControlTester()
                    tester.run_test()
                except KeyboardInterrupt:
                    print("\n🛑 Test stopped by user")
                except Exception as e:
                    print(f"❌ Error running test: {e}")
            elif choice == "8":
                print("👋 Thanks for trying Ctrl-ARM!")
                print("Visit our GitHub for more information:")
                print("https://github.com/yourusername/ctrl-arm")
                break
            else:
                print("❌ Invalid choice. Please enter 1-8.")
            
            print("\n" + "-"*70)
            input("Press Enter to continue...")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Demo ended. Thanks for trying Ctrl-ARM!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break

if __name__ == "__main__":
    main()
