import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    try:
        import serial
        import numpy
        import yaml
        return True
    except ImportError:
        print("Missing dependencies. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def run_basic_session():
    print("\n" + "="*60)
    print("EMG + IMU Quick Data Collection")
    print("="*60)
    print("\nThis will collect data for basic mouse control gestures.")
    print("Make sure your XIAO Sense is connected with EMG sensors attached.\n")

    data_dir = Path("data/raw")
    if data_dir.exists() and list(data_dir.glob("*.csv")):
        print(f"Found existing data in {data_dir}")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            return

    print("\nSession Plan:")
    print("  1. Rest (5s) - Keep arm relaxed")
    print("  2. Flex (5s) - Moderate muscle flexion")
    print("  3. Click (5s) - Quick flex-release motions")
    print("  4. Hold (8s) - Sustained flexion")
    print("  5. Wrist movements (20s) - Up, down, left, right")

    input("\nPress Enter when ready to start...")

    subprocess.run([sys.executable, "data_logger.py", "--interactive"])

def run_auto_session():
    print("\nRunning automated data collection...")
    print("Follow the on-screen prompts for each gesture.\n")

    commands = [
        "echo 'Starting automated collection...'",
        f"{sys.executable} data_logger.py --label rest --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label flex --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label click --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label hold --duration 8",
    ]

    for cmd in commands:
        if "echo" in cmd or "timeout" in cmd or "sleep" in cmd:
            os.system(cmd)
        else:
            subprocess.run(cmd.split())

def view_collected_data():
    data_dir = Path("data/raw")
    if not data_dir.exists():
        print("No data directory found.")
        return

    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        print("No data files found.")
        return

    print(f"\nFound {len(csv_files)} data files:")
    for f in sorted(csv_files)[-10:]:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")

    if len(csv_files) > 10:
        print(f"  ... and {len(csv_files)-10} more files")

def main():
    print("\nXIAO Sense EMG+IMU Data Collection Tool")
    print("-" * 45)

    if not check_dependencies():
        print("Failed to install dependencies.")
        return

    if len(sys.argv) > 1:
        if "--auto" in sys.argv:
            run_auto_session()
        elif "--view" in sys.argv:
            view_collected_data()
        else:
            print("Unknown argument. Use --auto for automated session or --view to see collected data.")
    else:
        while True:
            print("\nOptions:")
            print("  1. Start interactive collection")
            print("  2. Run automated basic session")
            print("  3. View collected data")
            print("  4. Test serial connection")
            print("  5. Exit")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == '1':
                run_basic_session()
            elif choice == '2':
                run_auto_session()
            elif choice == '3':
                view_collected_data()
            elif choice == '4':
                import serial.tools.list_ports
                print("\nAvailable serial ports:")
                for port in serial.tools.list_ports.comports():
                    print(f"  {port.device}: {port.description}")
                print("\nRun 'python data_logger.py --list-ports' for more details")
            elif choice == '5':
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")

if __name__ == "__main__":
    main()
