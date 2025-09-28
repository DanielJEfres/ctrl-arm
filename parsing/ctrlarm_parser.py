
import os
import pandas as pd
import numpy as np
import ctrlarm_file_management as cfm
from datetime import datetime

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 100)

class CtrlArmDataParser:
    def __init__(self, folder_locations, sqlite_file_path):
        self.folder_locations = folder_locations
        self.sqlite_file_path = sqlite_file_path
        self.failed_files = {}
        
        self.gesture_types = {
            'rest': {'category': 'baseline', 'duration_range': (1000, 5000)},
            'left_single': {'category': 'single', 'duration_range': (200, 800)},
            'right_single': {'category': 'single', 'duration_range': (200, 800)},
            'left_double': {'category': 'double', 'duration_range': (400, 1500)},
            'right_double': {'category': 'double', 'duration_range': (400, 1500)},
            'left_hold': {'category': 'hold', 'duration_range': (1000, 3000)},
            'right_hold': {'category': 'hold', 'duration_range': (1000, 3000)},
            'left_hard': {'category': 'hard', 'duration_range': (500, 2000)},
            'right_hard': {'category': 'hard', 'duration_range': (500, 2000)},
            'both_flex': {'category': 'flex', 'duration_range': (800, 2500)},
            'left_then_right': {'category': 'sequential', 'duration_range': (1000, 3000)},
            'right_then_left': {'category': 'sequential', 'duration_range': (1000, 3000)}
        }
        
        self.sensor_columns = {
            'emg': ['emg1_left', 'emg2_right'],
            'accelerometer': ['accel_x', 'accel_y', 'accel_z'],
            'gyroscope': ['gyro_x', 'gyro_y', 'gyro_z'],
            'all_sensors': ['emg1_left', 'emg2_right', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']
        }

    def get_files_from_folders(self, folder_list=None, filetype='csv', filename_only=True):
        
        if folder_list is None:
            folder_list = self.folder_locations
        filetype_folder = []
        for folder in folder_list:
            for dirpath, dirnames, filenames in os.walk(folder):
                for filename in filenames:
                    if filename.endswith(f".{filetype}"):
                        if filename_only:
                            filetype_folder.append(filename.split('.')[0])
                        else:
                            file = os.path.join(dirpath, filename)
                            filetype_folder.append(file)
        return filetype_folder

    def extract_gesture_metadata(self, filepath):
        
        filename = os.path.basename(filepath)
        name_parts = filename.replace('.csv', '').split('_')
        
        metadata = {
            'filename': filename,
            'filepath': filepath,
            'gesture_type': name_parts[0] if len(name_parts) > 0 else 'unknown',
            'date': name_parts[1] if len(name_parts) > 1 else 'unknown',
            'time': name_parts[2] if len(name_parts) > 2 else 'unknown',
            'timestamp': f"{name_parts[1]}_{name_parts[2]}" if len(name_parts) > 2 else 'unknown'
        }
        
        gesture_type = metadata['gesture_type']
        if gesture_type in self.gesture_types:
            metadata['gesture_category'] = self.gesture_types[gesture_type]['category']
            metadata['expected_duration_range'] = self.gesture_types[gesture_type]['duration_range']
        else:
            metadata['gesture_category'] = 'unknown'
            metadata['expected_duration_range'] = (0, 0)
            
        return metadata

    def calculate_sensor_statistics(self, df):
        
        stats = {}
        
        for sensor_group, columns in self.sensor_columns.items():
            if sensor_group == 'all_sensors':
                continue
                
            for col in columns:
                if col in df.columns:
                    stats[f'{col}_mean'] = df[col].mean()
                    stats[f'{col}_std'] = df[col].std()
                    stats[f'{col}_min'] = df[col].min()
                    stats[f'{col}_max'] = df[col].max()
                    stats[f'{col}_range'] = df[col].max() - df[col].min()
                    stats[f'{col}_median'] = df[col].median()
                    stats[f'{col}_q25'] = df[col].quantile(0.25)
                    stats[f'{col}_q75'] = df[col].quantile(0.75)
        
        stats['duration_ms'] = df['timestamp_ms'].max() - df['timestamp_ms'].min()
        stats['sample_count'] = len(df)
        stats['sampling_rate'] = stats['sample_count'] / (stats['duration_ms'] / 1000) if stats['duration_ms'] > 0 else 0
        
        return stats

    def parse_gesture_data(self):
        
        failed_files = []
        csv_filepaths = self.get_files_from_folders(filetype='csv', filename_only=False)
        print(f'{len(csv_filepaths)} CSV files found for processing')
        
        processed_data = []
        
        for index, file in enumerate(csv_filepaths):
            try:
                metadata = self.extract_gesture_metadata(file)
                
                df = pd.read_csv(file)
                
                required_columns = ['timestamp_ms', 'emg1_left', 'emg2_right', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'label']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    raise ValueError(f"Missing required columns: {missing_columns}")
                
                sensor_stats = self.calculate_sensor_statistics(df)
                
                combined_data = {**metadata, **sensor_stats}
                
                combined_data['raw_data_shape'] = df.shape
                combined_data['data_quality_score'] = self.calculate_data_quality_score(df)
                
                processed_data.append(combined_data)
                
            except Exception as e:
                print(f'{file} failed to be processed, please review. {e}')
                failed_files.append(file)
                continue
                
            if (index % 10 == 0):
                print(f'{index} gesture files processed so far...')
        
        print(f'Successfully processed {len(processed_data)} gesture files')
        print(f'Failed to process {len(failed_files)} gesture files')
        return processed_data, failed_files

    def calculate_data_quality_score(self, df):
        
        score = 100.0
        
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        score -= missing_ratio * 30
        
        duplicate_timestamps = df['timestamp_ms'].duplicated().sum()
        score -= (duplicate_timestamps / len(df)) * 20
        
        for col in self.sensor_columns['all_sensors']:
            if col in df.columns:
                mean_val = df[col].mean()
                std_val = df[col].std()
                outliers = ((df[col] - mean_val).abs() > 3 * std_val).sum()
                score -= (outliers / len(df)) * 10
        
        for col in self.sensor_columns['all_sensors']:
            if col in df.columns and df[col].std() == 0:
                score -= 5
        
        return max(0, score)

    def parse_gesture_data_by_type(self):
        
        failed_files = []
        csv_filepaths = self.get_files_from_folders(filetype='csv', filename_only=False)
        
        gesture_groups = {}
        for file in csv_filepaths:
            metadata = self.extract_gesture_metadata(file)
            gesture_type = metadata['gesture_type']
            if gesture_type not in gesture_groups:
                gesture_groups[gesture_type] = []
            gesture_groups[gesture_type].append(file)
        
        processed_data_by_type = {}
        
        for gesture_type, files in gesture_groups.items():
            print(f'Processing {len(files)} files for gesture type: {gesture_type}')
            processed_data_by_type[gesture_type] = []
            
            for file in files:
                try:
                    metadata = self.extract_gesture_metadata(file)
                    df = pd.read_csv(file)
                    sensor_stats = self.calculate_sensor_statistics(df)
                    combined_data = {**metadata, **sensor_stats}
                    combined_data['raw_data_shape'] = df.shape
                    combined_data['data_quality_score'] = self.calculate_data_quality_score(df)
                    processed_data_by_type[gesture_type].append(combined_data)
                    
                except Exception as e:
                    print(f'{file} failed to be processed: {e}')
                    failed_files.append(file)
        
        return processed_data_by_type, failed_files

    def log_parsing_results(self, gesture_metadata, failed_files):
        
        if gesture_metadata:
            print(f"\nGesture metadata shape: {len(gesture_metadata)}")
            
            gesture_counts = {}
            for data in gesture_metadata:
                gesture_type = data.get('gesture_type', 'unknown')
                gesture_counts[gesture_type] = gesture_counts.get(gesture_type, 0) + 1
            
            print("\nGesture type distribution:")
            for gesture_type, count in gesture_counts.items():
                print(f"- {gesture_type}: {count} files")
        else:
            print("\nNo gesture metadata found")

        if failed_files:
            print("\nFailed to process the following files:")
            for file in failed_files:
                print(f"- {file}")

