import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

class CtrlArmDataParserPlotter:
    def __init__(self, output_dir, timestamp, dataset_dirs):
        self.output_dir = output_dir
        self.timestamp = timestamp
        self.dataset_dirs = dataset_dirs
        self.plots = {}
        
        plt.style.use('default')
        sns.set_palette("husl")
        
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10

    def _sanitize_filename(self, filename):
        
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        filename = filename.replace(' ', '_')
        return filename

    def _get_timestamped_filename(self, base_filename):
        
        base, ext = os.path.splitext(base_filename)
        return f"{base}_{self.timestamp}{ext}"

    def _save_plot(self, plot_type, dataset_type, filename):
        
        try:
            plot_dir = self.dataset_dirs[dataset_type][plot_type]
            timestamped_filename = self._get_timestamped_filename(filename)
            plot_path = os.path.join(plot_dir, timestamped_filename)
            
            plt.tight_layout()
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            if dataset_type not in self.plots:
                self.plots[dataset_type] = {}
            if plot_type not in self.plots[dataset_type]:
                self.plots[dataset_type][plot_type] = []
            self.plots[dataset_type][plot_type].append(plot_path)
            
            print(f"Saved plot: {plot_path}")
            return plot_path
            
        except Exception as e:
            print(f"Error saving plot {filename}: {e}")
            plt.close()
            return None

    def create_numeric_histograms(self, df, filename_prefix, dataset_type):
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_columns) == 0:
            print(f"No numeric columns found for histograms in {dataset_type}")
            return
        
        for col in numeric_columns:
            unique_values = df[col].nunique()
            if unique_values <= 1:
                print(f"Skipping histogram for {col} - only {unique_values} unique value(s)")
                continue
            
            plt.figure(figsize=(10, 6))
            plt.hist(df[col].dropna(), bins=30, alpha=0.7, edgecolor='black')
            plt.title(f'{col} Distribution - {filename_prefix}', fontsize=14)
            plt.xlabel(col)
            plt.ylabel('Frequency')
            plt.grid(True, alpha=0.3)
            
            self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_{col}_histogram.png')

    def create_correlation_heatmap(self, df, filename_prefix, dataset_type):
        
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) < 2:
            print(f"Not enough numeric columns for correlation heatmap in {dataset_type} (need at least 2, found {len(numeric_df.columns)})")
            return
        
        corr_matrix = numeric_df.corr()
        
        if corr_matrix.isnull().all().all() or (corr_matrix == corr_matrix.iloc[0,0]).all().all():
            print(f"Skipping correlation heatmap for {dataset_type} - no meaningful correlations found")
            return
        
        plt.figure(figsize=(12, 10))
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='coolwarm', center=0,
                   square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
        plt.title(f'Correlation Heatmap - {filename_prefix}', fontsize=16)
        plt.tight_layout()
        
        self._save_plot('correlations', dataset_type, f'{filename_prefix}_correlation_heatmap.png')

    def create_categorical_plots(self, df, filename_prefix, dataset_type):
        
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns
        
        if len(categorical_columns) == 0:
            print(f"No categorical columns found for plots in {dataset_type}")
            return
        
        for col in categorical_columns:
            unique_values = df[col].nunique()
            if unique_values <= 1:
                print(f"Skipping categorical plot for {col} - only {unique_values} unique value(s)")
                continue
            
            plt.figure(figsize=(12, 6))
            value_counts = df[col].value_counts()
            
            if len(value_counts) > 20:
                value_counts = value_counts.head(20)
                plt.title(f'{col} Distribution (Top 20) - {filename_prefix}', fontsize=14)
            else:
                plt.title(f'{col} Distribution - {filename_prefix}', fontsize=14)
            
            bars = plt.bar(range(len(value_counts)), value_counts.values)
            plt.xlabel(col)
            plt.ylabel('Count')
            plt.xticks(range(len(value_counts)), value_counts.index, rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            self._save_plot('categorical', dataset_type, f'{filename_prefix}_{col}_distribution.png')

    def create_scatter_matrix(self, df, filename_prefix, dataset_type):
        
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) < 2:
            print(f"Not enough numeric columns for scatter matrix in {dataset_type} (need at least 2, found {len(numeric_df.columns)})")
            return
        
        has_variation = False
        for col in numeric_df.columns:
            if numeric_df[col].nunique() > 1:
                has_variation = True
                break
        
        if not has_variation:
            print(f"Skipping scatter matrix for {dataset_type} - no variation in numeric data")
            return
        
        if len(numeric_df.columns) > 6:
            numeric_df = numeric_df.iloc[:, :6]
        
        fig = plt.figure(figsize=(15, 15))
        pd.plotting.scatter_matrix(numeric_df, alpha=0.6, figsize=(15, 15), diagonal='hist')
        plt.suptitle(f'Scatter Matrix - {filename_prefix}', fontsize=16)
        
        plot_type = 'scatter_matrix' if 'scatter_matrix' in self.dataset_dirs[dataset_type] else 'correlations'
        self._save_plot(plot_type, dataset_type, f'{filename_prefix}_scatter_matrix.png')

    def create_time_series_plots(self, df, filename_prefix, dataset_type):
        
        time_columns = ['timestamp', 'date', 'time']
        available_time_cols = [col for col in time_columns if col in df.columns]
        
        if not available_time_cols:
            print(f"No time columns found for time series plots in {dataset_type}")
            return
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        time_col = available_time_cols[0]
        
        if len(numeric_columns) == 0:
            print(f"No numeric columns found for time series plots in {dataset_type}")
            return
        
        for col in numeric_columns:
            unique_values = df[col].nunique()
            if unique_values <= 1:
                print(f"Skipping time series plot for {col} - only {unique_values} unique value(s)")
                continue
            
            plt.figure(figsize=(12, 6))
            plt.plot(df[time_col], df[col], alpha=0.7, linewidth=1)
            plt.title(f'{col} over {time_col} - {filename_prefix}', fontsize=14)
            plt.xlabel(time_col)
            plt.ylabel(col)
            plt.grid(True, alpha=0.3)
            
            if len(df[time_col].unique()) > 10:
                plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            
            self._save_plot('time_series', dataset_type, f'{filename_prefix}_{col}_timeseries.png')

    def create_gesture_specific_plots(self, df, filename_prefix, dataset_type):
        
        if 'gesture_type' not in df.columns:
            print("No gesture_type column found for gesture-specific plots")
            return
        
        gesture_counts = df['gesture_type'].value_counts()
        if len(gesture_counts) > 1:
            plt.figure(figsize=(12, 6))
            bars = plt.bar(range(len(gesture_counts)), gesture_counts.values)
            plt.title(f'Gesture Type Distribution - {filename_prefix}', fontsize=14)
            plt.xlabel('Gesture Type')
            plt.ylabel('Count')
            plt.xticks(range(len(gesture_counts)), gesture_counts.index, rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            self._save_plot('categorical', dataset_type, f'{filename_prefix}_gesture_type_distribution.png')
        
        if 'gesture_category' in df.columns:
            category_counts = df['gesture_category'].value_counts()
            if len(category_counts) > 1:
                plt.figure(figsize=(10, 8))
                plt.pie(category_counts.values, labels=category_counts.index, autopct='%1.1f%%', startangle=90)
                plt.title(f'Gesture Category Distribution - {filename_prefix}', fontsize=14)
                plt.axis('equal')
                plt.tight_layout()
                self._save_plot('categorical', dataset_type, f'{filename_prefix}_gesture_category_pie.png')
        
        if 'data_quality_score' in df.columns:
            unique_values = df['data_quality_score'].nunique()
            if unique_values > 1:
                plt.figure(figsize=(10, 6))
                plt.hist(df['data_quality_score'], bins=20, alpha=0.7, edgecolor='black')
                plt.title(f'Data Quality Score Distribution - {filename_prefix}', fontsize=14)
                plt.xlabel('Quality Score')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_data_quality_histogram.png')
        
        if 'duration_ms' in df.columns:
            unique_values = df['duration_ms'].nunique()
            if unique_values > 1:
                plt.figure(figsize=(10, 6))
                plt.hist(df['duration_ms'], bins=20, alpha=0.7, edgecolor='black')
                plt.title(f'Duration Distribution - {filename_prefix}', fontsize=14)
                plt.xlabel('Duration (ms)')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_duration_histogram.png')

    def create_gesture_analysis_plots(self, df, filename_prefix, dataset_type):
        
        print(f"Creating gesture analysis plots for {dataset_type} dataset...")
        
        if 'gesture_type' in df.columns:
            gesture_counts = df['gesture_type'].value_counts()
            if len(gesture_counts) > 1:
                plt.figure(figsize=(14, 8))
                bars = plt.bar(range(len(gesture_counts)), gesture_counts.values, 
                             color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'])
                plt.title('Gesture Type Distribution\n(Total Gestures Recorded)', fontsize=16, fontweight='bold', pad=20)
                plt.xlabel('Gesture Type', fontsize=12, fontweight='bold')
                plt.ylabel('Number of Recordings', fontsize=12, fontweight='bold')
                plt.xticks(range(len(gesture_counts)), gesture_counts.index, rotation=45, ha='right')
                plt.grid(True, alpha=0.3, axis='y')
                
                for i, bar in enumerate(bars):
                    height = bar.get_height()
                    plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                            f'{int(height)}', ha='center', va='bottom', fontweight='bold')
                
                plt.tight_layout()
                self._save_plot('categorical', dataset_type, f'{filename_prefix}_gesture_distribution.png')
        
        if 'data_quality_score' in df.columns:
            unique_values = df['data_quality_score'].nunique()
            if unique_values > 1:
                plt.figure(figsize=(12, 8))
                plt.hist(df['data_quality_score'], bins=20, alpha=0.7, color='#2ca02c', edgecolor='black')
                plt.title('Data Quality Score Distribution\n(Higher scores indicate better data quality)', 
                         fontsize=16, fontweight='bold', pad=20)
                plt.xlabel('Quality Score (0-100)', fontsize=12, fontweight='bold')
                plt.ylabel('Number of Recordings', fontsize=12, fontweight='bold')
                plt.grid(True, alpha=0.3)
                
                mean_score = df['data_quality_score'].mean()
                plt.axvline(mean_score, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_score:.1f}')
                plt.legend()
                plt.tight_layout()
                self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_data_quality.png')
        
        if 'duration_ms' in df.columns and 'gesture_type' in df.columns:
            unique_values = df['duration_ms'].nunique()
            if unique_values > 1:
                plt.figure(figsize=(14, 8))
                
                gesture_types = df['gesture_type'].unique()
                durations_by_type = [df[df['gesture_type'] == gt]['duration_ms'].values for gt in gesture_types]
                
                box_plot = plt.boxplot(durations_by_type, labels=gesture_types, patch_artist=True)
                
                colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
                for patch, color in zip(box_plot['boxes'], colors[:len(gesture_types)]):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                
                plt.title('Gesture Duration Analysis\n(Box plots show duration distribution by gesture type)', 
                         fontsize=16, fontweight='bold', pad=20)
                plt.xlabel('Gesture Type', fontsize=12, fontweight='bold')
                plt.ylabel('Duration (milliseconds)', fontsize=12, fontweight='bold')
                plt.xticks(rotation=45, ha='right')
                plt.grid(True, alpha=0.3, axis='y')
                plt.tight_layout()
                self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_duration_analysis.png')
        
        emg_columns = [col for col in df.columns if 'emg' in col.lower()]
        if emg_columns:
            plt.figure(figsize=(14, 8))
            
            for i, col in enumerate(emg_columns[:2]):
                if df[col].nunique() > 1:
                    plt.subplot(1, 2, i+1)
                    plt.hist(df[col], bins=30, alpha=0.7, edgecolor='black')
                    plt.title(f'{col.replace("_", " ").title()} Distribution', fontsize=14, fontweight='bold')
                    plt.xlabel('Signal Strength', fontsize=12, fontweight='bold')
                    plt.ylabel('Frequency', fontsize=12, fontweight='bold')
                    plt.grid(True, alpha=0.3)
            
            plt.suptitle('EMG Signal Strength Analysis\n(Electromyography sensor readings)', 
                        fontsize=16, fontweight='bold', y=0.98)
            plt.tight_layout()
            self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_emg_analysis.png')
        
        if 'sampling_rate' in df.columns:
            unique_values = df['sampling_rate'].nunique()
            if unique_values > 1:
                plt.figure(figsize=(12, 8))
                plt.hist(df['sampling_rate'], bins=20, alpha=0.7, color='#9467bd', edgecolor='black')
                plt.title('Sampling Rate Distribution\n(Consistency of data collection frequency)', 
                         fontsize=16, fontweight='bold', pad=20)
                plt.xlabel('Sampling Rate (Hz)', fontsize=12, fontweight='bold')
                plt.ylabel('Number of Recordings', fontsize=12, fontweight='bold')
                plt.grid(True, alpha=0.3)
                
                mean_rate = df['sampling_rate'].mean()
                plt.axvline(mean_rate, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_rate:.1f} Hz')
                plt.legend()
                plt.tight_layout()
                self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_sampling_rate.png')
        
        if 'data_quality_score' in df.columns and 'gesture_type' in df.columns:
            plt.figure(figsize=(14, 8))
            
            success_threshold = 80
            gesture_success = df.groupby('gesture_type').apply(
                lambda x: (x['data_quality_score'] > success_threshold).sum() / len(x) * 100
            ).sort_values(ascending=False)
            
            bars = plt.bar(range(len(gesture_success)), gesture_success.values, 
                         color=['#2ca02c' if x > 90 else '#ff7f0e' if x > 80 else '#d62728' for x in gesture_success.values])
            plt.title(f'Gesture Recognition Success Rate\n(Quality Score > {success_threshold})', 
                     fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('Gesture Type', fontsize=12, fontweight='bold')
            plt.ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
            plt.xticks(range(len(gesture_success)), gesture_success.index, rotation=45, ha='right')
            plt.grid(True, alpha=0.3, axis='y')
            plt.ylim(0, 100)
            
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            self._save_plot('categorical', dataset_type, f'{filename_prefix}_success_rate.png')
        
        print("Creating EMG waveform plots...")
        self.create_emg_waveform_plots(df, filename_prefix, dataset_type)
        
        print("Creating 3D trajectory plots...")
        self.create_3d_trajectory_plots(df, filename_prefix, dataset_type)
        
        print("Creating 3D EMG signal space plots...")
        self.create_3d_emg_space_plots(df, filename_prefix, dataset_type)
        
        print("Creating 3D gyroscope plots...")
        self.create_3d_gyroscope_plots(df, filename_prefix, dataset_type)
        
        print("Creating 3D feature space plots...")
        self.create_3d_feature_space_plots(df, filename_prefix, dataset_type)
        
        print("Creating confusion matrix plots...")
        self.create_confusion_matrix_plots(df, filename_prefix, dataset_type)
        
        print("Creating SNR analysis plots...")
        self.create_snr_analysis_plots(df, filename_prefix, dataset_type)
        
        print("Creating temporal trends plots...")
        self.create_temporal_trends_plots(df, filename_prefix, dataset_type)
        
        print(f"Gesture analysis plots created for {dataset_type} dataset")

    def create_emg_waveform_plots(self, df, filename_prefix, dataset_type):
        
        emg_columns = [col for col in df.columns if 'emg' in col.lower()]
        
        if not emg_columns or 'gesture_type' not in df.columns:
            print("Skipping EMG waveform plots - no EMG data or gesture types available")
            return
        
        gesture_types = df['gesture_type'].unique()
        
        for gesture_type in gesture_types[:4]:
            gesture_data = df[df['gesture_type'] == gesture_type]
            if len(gesture_data) < 5:
                continue
                
            plt.figure(figsize=(15, 8))
            
            for i, emg_col in enumerate(emg_columns[:2]):
                plt.subplot(2, 1, i+1)
                
                sample_indices = gesture_data.index[:3]
                
                for j, idx in enumerate(sample_indices):
                    if 'timestamp_ms' in df.columns:
                        time_data = df.loc[idx:idx+99, 'timestamp_ms']
                        emg_data = df.loc[idx:idx+99, emg_col]
                    else:
                        time_data = range(100)
                        emg_data = df.loc[idx:idx+99, emg_col]
                    
                    min_len = min(len(time_data), len(emg_data))
                    time_data = time_data[:min_len]
                    emg_data = emg_data[:min_len]
                    
                    plt.plot(time_data, emg_data, alpha=0.7, linewidth=1, 
                            label=f'Sample {j+1}' if j < 3 else '')
                
                plt.title(f'{emg_col.replace("_", " ").title()} - {gesture_type}', 
                         fontsize=14, fontweight='bold')
                plt.xlabel('Time (ms)' if 'timestamp_ms' in df.columns else 'Sample Index')
                plt.ylabel('EMG Signal Strength')
                plt.grid(True, alpha=0.3)
                if i == 0:
                    plt.legend()
            
            plt.suptitle(f'EMG Signal Waveforms - {gesture_type}', fontsize=16, fontweight='bold')
            plt.tight_layout()
            self._save_plot('time_series', dataset_type, f'{filename_prefix}_emg_waveforms_{gesture_type}.png')

    def create_3d_trajectory_plots(self, df, filename_prefix, dataset_type):
        
        accel_cols = [col for col in df.columns if 'accel' in col.lower()]
        gyro_cols = [col for col in df.columns if 'gyro' in col.lower()]
        
        if not accel_cols or 'gesture_type' not in df.columns:
            print("Skipping 3D trajectory plots - no accelerometer data available")
            return
        
        gesture_types = df['gesture_type'].unique()
        
        fig = plt.figure(figsize=(15, 10))
        
        for i, gesture_type in enumerate(gesture_types[:4]):
            gesture_data = df[df['gesture_type'] == gesture_type]
            if len(gesture_data) < 10:
                continue
                
            ax = fig.add_subplot(2, 2, i+1, projection='3d')
            
            sample_data = gesture_data.sample(min(100, len(gesture_data)))
            
            scatter = ax.scatter(sample_data[accel_cols[0]], 
                               sample_data[accel_cols[1]], 
                               sample_data[accel_cols[2]], 
                               c=sample_data.index, 
                               cmap='viridis', 
                               alpha=0.6,
                               s=20)
            
            ax.set_xlabel(f'{accel_cols[0].replace("_", " ").title()}')
            ax.set_ylabel(f'{accel_cols[1].replace("_", " ").title()}')
            ax.set_zlabel(f'{accel_cols[2].replace("_", " ").title()}')
            ax.set_title(f'3D Movement Trajectory - {gesture_type}', fontweight='bold')
            
            plt.colorbar(scatter, ax=ax, shrink=0.5)
        
        plt.suptitle('3D Accelerometer Movement Trajectories by Gesture Type', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        self._save_plot('correlations', dataset_type, f'{filename_prefix}_3d_trajectories.png')

    def create_3d_emg_space_plots(self, df, filename_prefix, dataset_type):
        
        emg_columns = [col for col in df.columns if 'emg' in col.lower()]
        
        if len(emg_columns) < 2 or 'gesture_type' not in df.columns:
            print("Skipping 3D EMG space plots - need at least 2 EMG channels")
            return
        
        fig = plt.figure(figsize=(15, 10))
        
        gesture_types = df['gesture_type'].unique()
        
        for i, gesture_type in enumerate(gesture_types[:4]):
            gesture_data = df[df['gesture_type'] == gesture_type]
            if len(gesture_data) < 10:
                continue
                
            ax = fig.add_subplot(2, 2, i+1, projection='3d')
            
            sample_data = gesture_data.sample(min(200, len(gesture_data)))
            
            scatter = ax.scatter(sample_data[emg_columns[0]], 
                               sample_data[emg_columns[1]], 
                               sample_data.get(emg_columns[2], sample_data[emg_columns[0]]) if len(emg_columns) > 2 else sample_data[emg_columns[0]], 
                               c=sample_data.index, 
                               cmap='plasma', 
                               alpha=0.6,
                               s=15)
            
            ax.set_xlabel(f'{emg_columns[0].replace("_", " ").title()}')
            ax.set_ylabel(f'{emg_columns[1].replace("_", " ").title()}')
            if len(emg_columns) > 2:
                ax.set_zlabel(f'{emg_columns[2].replace("_", " ").title()}')
            else:
                ax.set_zlabel(f'{emg_columns[0].replace("_", " ").title()} (duplicate)')
            ax.set_title(f'3D EMG Signal Space - {gesture_type}', fontweight='bold')
            
            plt.colorbar(scatter, ax=ax, shrink=0.5)
        
        plt.suptitle('3D EMG Signal Space Visualization by Gesture Type', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        self._save_plot('correlations', dataset_type, f'{filename_prefix}_3d_emg_space.png')

    def create_3d_gyroscope_plots(self, df, filename_prefix, dataset_type):
        
        gyro_cols = [col for col in df.columns if 'gyro' in col.lower()]
        
        if len(gyro_cols) < 3 or 'gesture_type' not in df.columns:
            print("Skipping 3D gyroscope plots - need 3 gyroscope channels")
            return
        
        fig = plt.figure(figsize=(15, 10))
        
        gesture_types = df['gesture_type'].unique()
        
        for i, gesture_type in enumerate(gesture_types[:4]):
            gesture_data = df[df['gesture_type'] == gesture_type]
            if len(gesture_data) < 10:
                continue
                
            ax = fig.add_subplot(2, 2, i+1, projection='3d')
            
            sample_data = gesture_data.sample(min(150, len(gesture_data)))
            
            scatter = ax.scatter(sample_data[gyro_cols[0]], 
                               sample_data[gyro_cols[1]], 
                               sample_data[gyro_cols[2]], 
                               c=sample_data.index, 
                               cmap='coolwarm', 
                               alpha=0.7,
                               s=20)
            
            ax.set_xlabel(f'{gyro_cols[0].replace("_", " ").title()}')
            ax.set_ylabel(f'{gyro_cols[1].replace("_", " ").title()}')
            ax.set_zlabel(f'{gyro_cols[2].replace("_", " ").title()}')
            ax.set_title(f'3D Gyroscope Trajectory - {gesture_type}', fontweight='bold')
            
            plt.colorbar(scatter, ax=ax, shrink=0.5)
        
        plt.suptitle('3D Gyroscope Movement Trajectories by Gesture Type', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        self._save_plot('correlations', dataset_type, f'{filename_prefix}_3d_gyroscope.png')

    def create_3d_feature_space_plots(self, df, filename_prefix, dataset_type):
        
        emg_cols = [col for col in df.columns if 'emg' in col.lower()]
        accel_cols = [col for col in df.columns if 'accel' in col.lower()]
        gyro_cols = [col for col in df.columns if 'gyro' in col.lower()]
        
        if not emg_cols or not accel_cols or 'gesture_type' not in df.columns:
            print("Skipping 3D feature space plots - missing sensor data")
            return
        
        fig = plt.figure(figsize=(15, 10))
        
        combinations = [
            (emg_cols[0], accel_cols[0], gyro_cols[0] if gyro_cols else accel_cols[1], 'EMG-Accel-Gyro'),
            (emg_cols[1] if len(emg_cols) > 1 else emg_cols[0], accel_cols[1], accel_cols[2], 'EMG-Accel-Accel'),
            (accel_cols[0], accel_cols[1], accel_cols[2], 'Accel-Accel-Accel'),
            (emg_cols[0], emg_cols[1] if len(emg_cols) > 1 else emg_cols[0], accel_cols[0], 'EMG-EMG-Accel')
        ]
        
        for i, (x_col, y_col, z_col, title) in enumerate(combinations):
            ax = fig.add_subplot(2, 2, i+1, projection='3d')
            
            gesture_types = df['gesture_type'].unique()
            colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
            
            for j, gesture_type in enumerate(gesture_types):
                gesture_data = df[df['gesture_type'] == gesture_type]
                if len(gesture_data) < 5:
                    continue
                    
                sample_data = gesture_data.sample(min(50, len(gesture_data)))
                
                ax.scatter(sample_data[x_col], 
                          sample_data[y_col], 
                          sample_data[z_col], 
                          c=colors[j % len(colors)], 
                          label=gesture_type,
                          alpha=0.6,
                          s=15)
            
            ax.set_xlabel(f'{x_col.replace("_", " ").title()}')
            ax.set_ylabel(f'{y_col.replace("_", " ").title()}')
            ax.set_zlabel(f'{z_col.replace("_", " ").title()}')
            ax.set_title(f'3D Feature Space - {title}', fontweight='bold')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.suptitle('3D Multi-Sensor Feature Space Visualization', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        self._save_plot('correlations', dataset_type, f'{filename_prefix}_3d_feature_space.png')

    def create_confusion_matrix_plots(self, df, filename_prefix, dataset_type):
        
        if 'gesture_type' not in df.columns or 'data_quality_score' not in df.columns:
            print("Skipping confusion matrix - missing gesture_type or quality_score")
            return
        
        gesture_types = df['gesture_type'].unique()
        confusion_matrix = np.zeros((len(gesture_types), len(gesture_types)))
        
        for i, true_gesture in enumerate(gesture_types):
            gesture_data = df[df['gesture_type'] == true_gesture]
            high_quality_threshold = gesture_data['data_quality_score'].quantile(0.8)
            
            for j, predicted_gesture in enumerate(gesture_types):
                if i == j:
                    confusion_matrix[i, j] = (gesture_data['data_quality_score'] > high_quality_threshold).sum()
                else:
                    confusion_matrix[i, j] = (gesture_data['data_quality_score'] <= high_quality_threshold).sum() * 0.1
        
        confusion_matrix = confusion_matrix / confusion_matrix.sum(axis=1, keepdims=True)
        
        plt.figure(figsize=(12, 10))
        sns.heatmap(confusion_matrix, 
                   annot=True, 
                   fmt='.2f', 
                   cmap='Blues',
                   xticklabels=gesture_types,
                   yticklabels=gesture_types)
        
        plt.title('Gesture Recognition Confusion Matrix\n(Higher values indicate better recognition)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Predicted Gesture Type', fontsize=12, fontweight='bold')
        plt.ylabel('True Gesture Type', fontsize=12, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        self._save_plot('correlations', dataset_type, f'{filename_prefix}_confusion_matrix.png')

    def create_snr_analysis_plots(self, df, filename_prefix, dataset_type):
        
        emg_columns = [col for col in df.columns if 'emg' in col.lower()]
        
        if not emg_columns or 'gesture_type' not in df.columns:
            print("Skipping SNR analysis - no EMG data available")
            return
        
        plt.figure(figsize=(14, 8))
        
        gesture_types = df['gesture_type'].unique()
        snr_data = []
        
        for gesture_type in gesture_types:
            gesture_data = df[df['gesture_type'] == gesture_type]
            
            for emg_col in emg_columns[:2]:
                if gesture_data[emg_col].std() > 0:
                    snr = gesture_data[emg_col].mean() / gesture_data[emg_col].std()
                    snr_data.append({
                        'gesture_type': gesture_type,
                        'emg_channel': emg_col,
                        'snr': snr
                    })
        
        if snr_data:
            snr_df = pd.DataFrame(snr_data)
            
            plt.subplot(1, 2, 1)
            snr_pivot = snr_df.pivot(index='gesture_type', columns='emg_channel', values='snr')
            snr_pivot.plot(kind='bar', ax=plt.gca())
            plt.title('Signal-to-Noise Ratio by Gesture Type', fontsize=14, fontweight='bold')
            plt.xlabel('Gesture Type')
            plt.ylabel('SNR (Mean/Std)')
            plt.xticks(rotation=45, ha='right')
            plt.legend(title='EMG Channel')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(1, 2, 2)
            if 'data_quality_score' in df.columns:
                quality_snr = df.groupby('gesture_type').agg({
                    'data_quality_score': 'mean',
                    emg_columns[0]: lambda x: x.mean() / x.std() if x.std() > 0 else 0
                }).reset_index()
                
                plt.scatter(quality_snr['data_quality_score'], quality_snr[emg_columns[0]], 
                           s=100, alpha=0.7)
                
                for i, gesture_type in enumerate(quality_snr['gesture_type']):
                    plt.annotate(gesture_type, 
                               (quality_snr['data_quality_score'].iloc[i], 
                                quality_snr[emg_columns[0]].iloc[i]),
                               xytext=(5, 5), textcoords='offset points')
                
                plt.title('SNR vs Data Quality Score', fontsize=14, fontweight='bold')
                plt.xlabel('Average Data Quality Score')
                plt.ylabel(f'SNR ({emg_columns[0]})')
                plt.grid(True, alpha=0.3)
        
        plt.suptitle('Signal-to-Noise Ratio Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        self._save_plot('numeric_histograms', dataset_type, f'{filename_prefix}_snr_analysis.png')

    def create_temporal_trends_plots(self, df, filename_prefix, dataset_type):
        
        if 'date' not in df.columns or 'data_quality_score' not in df.columns:
            print("Skipping temporal trends - missing date or quality_score data")
            return
        
        plt.figure(figsize=(15, 10))
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        
        plt.subplot(2, 2, 1)
        daily_quality = df.groupby('date')['data_quality_score'].agg(['mean', 'std']).reset_index()
        plt.errorbar(daily_quality['date'], daily_quality['mean'], 
                    yerr=daily_quality['std'], capsize=5, capthick=2)
        plt.title('Data Quality Trends Over Time', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Average Quality Score')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        plt.subplot(2, 2, 2)
        daily_counts = df.groupby('date').size()
        plt.bar(daily_counts.index, daily_counts.values, alpha=0.7)
        plt.title('Recording Count Per Day', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Number of Recordings')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        plt.subplot(2, 2, 3)
        if 'gesture_type' in df.columns:
            gesture_trends = df.groupby(['date', 'gesture_type']).size().unstack(fill_value=0)
            gesture_trends.plot(kind='bar', stacked=True, ax=plt.gca())
            plt.title('Gesture Type Distribution Over Time', fontsize=14, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Number of Recordings')
            plt.xticks(rotation=45)
            plt.legend(title='Gesture Type', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.subplot(2, 2, 4)
        if 'duration_ms' in df.columns:
            daily_performance = df.groupby('date').agg({
                'data_quality_score': 'mean',
                'duration_ms': 'mean'
            }).reset_index()
            
            daily_performance['performance_score'] = (
                daily_performance['data_quality_score'] / 100 * 
                (1 / (daily_performance['duration_ms'] / 1000))
            )
            
            plt.plot(daily_performance['date'], daily_performance['performance_score'], 
                    marker='o', linewidth=2, markersize=6)
            plt.title('Performance Improvement Trend', fontsize=14, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Composite Performance Score')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
        
        plt.suptitle('Temporal Performance Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        self._save_plot('time_series', dataset_type, f'{filename_prefix}_temporal_trends.png')

    def create_summary_plots(self, df, filename_prefix, dataset_type):
        
        print(f"Creating plots for {dataset_type} dataset...")
        
        self.create_gesture_analysis_plots(df, filename_prefix, dataset_type)
        
        print(f"All plots created for {dataset_type} dataset")

    def get_plots(self, dataset_type, plot_type=None):
        
        if dataset_type not in self.plots:
            return []
        
        if plot_type:
            return self.plots[dataset_type].get(plot_type, [])
        else:
            all_plots = []
            for plots in self.plots[dataset_type].values():
                all_plots.extend(plots)
            return all_plots
