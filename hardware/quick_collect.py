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
    print("\nQuick Data Collection")
    print("-" * 25)
    print("\nThis will collect data for basic mouse control gestures.")
    print("Make sure your XIAO Sense is connected with sensors attached.\n")

    data_dir = Path("data/raw")
    if data_dir.exists() and list(data_dir.glob("*.csv")):
        print(f"Found existing data in {data_dir}")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            return

    print("\nSession Plan:")
    print("  1. Rest (5s) - Keep arm relaxed")
    print("  2. Left single (5s) - Quick tap on left bicep")
    print("  3. Right single (5s) - Quick tap on right bicep")
    print("  4. Left double (5s) - Two quick taps on left")
    print("  5. Right double (5s) - Two quick taps on right")
    print("  6. Left hold (8s) - Sustained left flex")
    print("  7. Right hold (8s) - Sustained right flex")
    print("  8. Both flex (8s) - Simultaneous left+right flex")
    print("  9. Left then right (8s) - Left tap then right tap")
    print("  10. Right then left (8s) - Right tap then left tap")
    print("  11. Left hard (8s) - High intensity left flex")
    print("  12. Right hard (8s) - High intensity right flex")

    input("\nPress Enter when ready to start...")

    subprocess.run([sys.executable, "data_logger.py", "--interactive"])

def run_calibration():
    from data_logger import DataLogger, interactive_mode

    print("CALIBRATION MODE")
    print("-" * 16)
    print("This will set up your personalized muscle thresholds.")
    print("Make sure you're connected to the XIAO Sense device.\n")

    # Auto-detect port
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())

    if not ports:
        print("No serial ports found! Connect your XIAO Sense device.")
        return False

    # Find XIAO device
    port = None
    for p in ports:
        if 'XIAO' in p.description or 'Arduino' in p.description or 'USB Serial' in p.description:
            port = p.device
            break

    if not port:
        print("XIAO device not found. Available ports:")
        for i, p in enumerate(ports):
            print(f"  {i+1}. {p.device}: {p.description}")
        choice = input("Select port number: ").strip()
        try:
            port = ports[int(choice)-1].device
        except:
            print("Invalid selection")
            return False

    logger = DataLogger(port, output_dir='data/raw')

    if not logger.connect():
        print("Failed to connect to device")
        return False

    try:
        success = logger.run_calibration_sequence()
        return success
    finally:
        logger.close()

def run_auto_session():
    print("\nRunning automated data collection...")
    print("Follow the on-screen prompts for each gesture.\n")

    commands = [
        "echo 'Starting automated collection...'",
        f"{sys.executable} data_logger.py --label rest --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label left_single --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label right_single --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label left_double --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label right_double --duration 5",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label left_hold --duration 8",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label right_hold --duration 8",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label both_flex --duration 8",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label left_then_right --duration 8",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label right_then_left --duration 8",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label left_hard --duration 8",
        "timeout /t 2 >nul" if os.name == 'nt' else "sleep 2",
        f"{sys.executable} data_logger.py --label right_hard --duration 8",
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
    print("\nData Collection Tool")
    print("-" * 20)

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
            print("  3. Run calibration (personalized thresholds)")
            print("  4. View collected data")
            print("  5. Test serial connection")
            print("  6. Exit")

            choice = input("\nSelect option (1-6): ").strip()

            if choice == '1':
                run_basic_session()
            elif choice == '2':
                run_auto_session()
            elif choice == '3':
                if run_calibration():
                    print("Calibration complete! You can now collect training data.")
                else:
                    print("Calibration failed. Please try again.")
            elif choice == '4':
                view_collected_data()
            elif choice == '5':
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
