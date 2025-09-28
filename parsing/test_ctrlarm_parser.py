

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ctrlarm_parser import CtrlArmDataParser
from ctrlarm_parser_outputer import CtrlArmDataParserOutputer

def main():
    
    
    print("="*60)
    print("CTRL-ARM DATA PARSER SYSTEM TEST")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
    output_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    
    print(f"Data folder: {data_folder}")
    print(f"Output folder: {output_folder}")
    print()
    
    if not os.path.exists(data_folder):
        print(f"ERROR: Data folder '{data_folder}' does not exist!")
        print("Please ensure the data folder contains CSV files with gesture data.")
        return
    
    print("Initializing Ctrl-Arm Data Parser...")
    parser = CtrlArmDataParser(
        folder_locations=[data_folder],
        sqlite_file_path=os.path.join(output_folder, 'ctrlarm_data.db')
    )
    
    print("Initializing Ctrl-Arm Data Parser Outputer...")
    outputer = CtrlArmDataParserOutputer(output_folder)
    
    print("Parser and outputer initialized successfully!")
    print()
    
    print("Parsing gesture data files...")
    try:
        gesture_metadata, failed_files = parser.parse_gesture_data()
        
        if gesture_metadata:
            print(f"Successfully parsed {len(gesture_metadata)} gesture files")
            
            parser.log_parsing_results(gesture_metadata, failed_files)
            
            import pandas as pd
            gesture_metadata_df = pd.DataFrame(gesture_metadata)
            
            print("\nSaving gesture metadata and creating gesture analysis visualizations...")
            outputer.save_to_csv(gesture_metadata_df, 'gesture_metadata.csv', 'gesture_metadata')
            outputer.create_summary_plots(gesture_metadata_df, 'gesture_metadata', 'gesture_metadata')
            print(f"Gesture metadata saved and gesture analysis plots created for {len(gesture_metadata)} records")
            
            print("\nGenerating analysis summary...")
            summary_df = outputer.create_analysis_summary(gesture_metadata_df, failed_files)
            print("Analysis summary created!")
            
        else:
            print("No gesture data was successfully parsed!")
            
    except Exception as e:
        print(f"ERROR during parsing: {e}")
        return
    
    print("\n" + "="*40)
    print("GESTURE ANALYSIS COMPLETE")
    print("="*40)
    print("Generated visualizations:")
    print("Gesture Type Distribution")
    print("Data Quality Analysis") 
    print("Gesture Duration Analysis")
    print("EMG Signal Strength Analysis")
    print("Sampling Rate Consistency")
    print("Gesture Success Rate Analysis")
    print("EMG Signal Waveforms")
    print("3D Accelerometer Trajectories")
    print("3D EMG Signal Space")
    print("3D Gyroscope Trajectories")
    print("3D Multi-Sensor Feature Space")
    print("Gesture Confusion Matrix")
    print("Signal-to-Noise Ratio Analysis")
    print("Temporal Performance Trends")
    
    print("\n" + "="*40)
    print("OUTPUT INFORMATION")
    print("="*40)
    print(f"All output files saved to: {outputer.timestamped_dir}")
    print(f"Timestamp: {outputer.timestamp}")
    print()
    
    print("Directory structure:")
    for dataset_type, dirs in outputer.dataset_dirs.items():
        print(f"  {dataset_type}/")
        for output_type, dir_path in dirs.items():
            print(f"    {output_type}/")
    
    print("\n" + "="*60)
    print("CTRL-ARM GESTURE ANALYSIS COMPLETED")
    print("="*60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Analysis outputs created:")
    print("Professional visualization plots")
    print("Comprehensive data quality metrics")
    print("Gesture recognition success rates")
    print("Technical performance statistics")
    print("EMG signal waveform analysis")
    print("3D accelerometer trajectory visualization")
    print("3D EMG signal space analysis")
    print("3D gyroscope movement visualization")
    print("3D multi-sensor feature space analysis")
    print("Gesture confusion matrix analysis")
    print("Signal-to-noise ratio analysis")
    print("Temporal performance trends")
    print("Gesture analysis summary CSV")
    print()
    print("Ready for presentation!")

if __name__ == "__main__":
    main()
