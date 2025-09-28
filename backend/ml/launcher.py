#!/usr/bin/env python3
# ctrl-arm launcher
# choose between emg-only control or enhanced emg+imu control

import sys
import os
from pathlib import Path

def main():
    print("\n" + "="*60)
    print(" "*20 + "ctrl-arm launcher")
    print("="*60)
    print()
    print("choose your control mode:")
    print()
    print("1. emg gestures only")
    print("   - muscle flexes for clicks and scrolls")
    print("   - uses decision tree ml model")
    print("   - 89.87 percent accuracy")
    print()
    print("2. enhanced emg + imu cursor control")
    print("   - muscle flexes for clicks and scrolls")
    print("   - lean to move cursor (chest-mounted)")
    print("   - smooth, responsive cursor movement")
    print("   - perfect for hands-free computing")
    print()
    print("3. exit")
    print()
    
    while True:
        try:
            choice = input("enter your choice (1-3): ").strip()
            
            if choice == "1":
                print("\nstarting emg gestures only...")
                from emg_control import SmartEMGController
                controller = SmartEMGController()
                controller.run()
                break
                
            elif choice == "2":
                print("\nstarting enhanced emg + imu control...")
                from enhanced_emg_control import EnhancedEMGController
                controller = EnhancedEMGController()
                controller.run()
                break
                
            elif choice == "3":
                print("\ngoodbye")
                sys.exit(0)
                
            else:
                print("invalid choice. please enter 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n\ngoodbye")
            sys.exit(0)
        except Exception as e:
            print(f"\nerror: {e}")
            print("please check your setup and try again.")
            break

if __name__ == "__main__":
    main()
