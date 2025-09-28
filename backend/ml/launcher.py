#!/usr/bin/env python3
"""
Ctrl-ARM Launcher
Choose between EMG-only control or enhanced EMG+IMU control
"""

import sys
import os
from pathlib import Path

def main():
    print("\n" + "="*60)
    print(" "*20 + "CTRL-ARM LAUNCHER")
    print("="*60)
    print()
    print("Choose your control mode:")
    print()
    print("1. EMG Gestures Only")
    print("   - Muscle flexes for clicks and scrolls")
    print("   - Uses decision tree ML model")
    print("   - 89.87% accuracy")
    print()
    print("2. Enhanced EMG + IMU Cursor Control")
    print("   - Muscle flexes for clicks and scrolls")
    print("   - Lean to move cursor (chest-mounted)")
    print("   - Smooth, responsive cursor movement")
    print("   - Perfect for hands-free computing")
    print()
    print("3. Exit")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                print("\n🚀 Starting EMG Gestures Only...")
                from emg_control import SmartEMGController
                controller = SmartEMGController()
                controller.run()
                break
                
            elif choice == "2":
                print("\n🚀 Starting Enhanced EMG + IMU Control...")
                from enhanced_emg_control import EnhancedEMGController
                controller = EnhancedEMGController()
                controller.run()
                break
                
            elif choice == "3":
                print("\n👋 Goodbye!")
                sys.exit(0)
                
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please check your setup and try again.")
            break

if __name__ == "__main__":
    main()
