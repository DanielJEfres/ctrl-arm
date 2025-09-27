import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from scipy import signal
from scipy.stats import skew, kurtosis
import warnings
warnings.filterwarnings('ignore')

class FeatureExtractor:
    def __init__(self, window_size_ms=500, overlap_pct=0.5):
        self.window_size = window_size_ms
        self.overlap = overlap_pct

        self.emg_features = [
            'mav', 'rms', 'var', 'std', 'mad', 'zc', 'wl', 'iemg', 'msr', 'wamp',
            'skew', 'kurtosis', 'median_freq', 'mean_freq', 'freq_ratio'
        ]

        self.imu_features = [
            'mean', 'std', 'var', 'mad', 'skew', 'kurtosis', 'min', 'max', 'range',
            'rms', 'peak_freq', 'energy', 'spectral_centroid'
        ]

        self.butter_b, self.butter_a = signal.butter(4, [20, 90], btype='band', fs=200)

    def load_data(self, file_path):
        print(f"loading {file_path}")

        df = pd.read_csv(file_path)

        required_cols = ['timestamp_ms', 'emg1_left', 'emg2_right']
        imu_cols = ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']

        missing_cols = [col for col in required_cols + imu_cols if col not in df.columns]
        if missing_cols:
            print(f"missing: {missing_cols}")

        df['timestamp_ms'] = df['timestamp_ms'] - df['timestamp_ms'].iloc[0]
        df['time_s'] = df['timestamp_ms'] / 1000.0

        for col in ['emg1_left', 'emg2_right']:
            if col in df.columns:
                df[col] = df[col] - df[col].mean()
                df[col + '_filtered'] = signal.filtfilt(self.butter_b, self.butter_a, df[col])
                df[col + '_rectified'] = np.abs(df[col + '_filtered'])

        for col in imu_cols:
            if col in df.columns:
                df[col + '_smoothed'] = signal.savgol_filter(df[col], 11, 3)

        return df

    def extract_emg_features(self, emg_signal):
        features = {}

        features['mav'] = np.mean(np.abs(emg_signal))
        features['rms'] = np.sqrt(np.mean(emg_signal**2))
        features['var'] = np.var(emg_signal)
        features['std'] = np.std(emg_signal)
        features['mad'] = np.mean(np.abs(emg_signal - np.mean(emg_signal)))

        zero_crossings = np.where(np.diff(np.sign(emg_signal)))[0]
        features['zc'] = len(zero_crossings)

        features['wl'] = np.sum(np.abs(np.diff(emg_signal)))
        features['iemg'] = np.sum(np.abs(emg_signal))

        if len(emg_signal) > 1:
            power_spectrum = np.abs(np.fft.fft(emg_signal))**2
            freqs = np.fft.fftfreq(len(emg_signal), d=1/200)
            features['mean_freq'] = np.sum(freqs * power_spectrum) / np.sum(power_spectrum)
            features['median_freq'] = freqs[np.argsort(power_spectrum)][len(power_spectrum)//2]
            features['freq_ratio'] = features['median_freq'] / features['mean_freq']

        features['skew'] = skew(emg_signal)
        features['kurtosis'] = kurtosis(emg_signal)

        threshold = np.std(emg_signal)
        features['wamp'] = np.sum(np.abs(np.diff(emg_signal)) > threshold)

        features['msr'] = np.sqrt(np.mean(emg_signal**2))

        return features

    def extract_imu_features(self, imu_signal):
        features = {}

        features['mean'] = np.mean(imu_signal)
        features['std'] = np.std(imu_signal)
        features['var'] = np.var(imu_signal)
        features['mad'] = np.mean(np.abs(imu_signal - np.mean(imu_signal)))
        features['min'] = np.min(imu_signal)
        features['max'] = np.max(imu_signal)
        features['range'] = features['max'] - features['min']
        features['rms'] = np.sqrt(np.mean(imu_signal**2))

        features['skew'] = skew(imu_signal)
        features['kurtosis'] = kurtosis(imu_signal)

        if len(imu_signal) > 10:
            try:
                fft_vals = np.abs(np.fft.fft(imu_signal))
                fft_freqs = np.fft.fftfreq(len(imu_signal), d=1/200)
                fft_power = fft_vals**2

                peak_idx = np.argmax(fft_power[1:]) + 1
                features['peak_freq'] = abs(fft_freqs[peak_idx])

                features['spectral_centroid'] = np.sum(fft_freqs * fft_power) / np.sum(fft_power)
                features['energy'] = np.sum(fft_power)
            except:
                features['peak_freq'] = 0
                features['spectral_centroid'] = 0
                features['energy'] = 0

        return features

    def create_windows(self, df, window_size_ms=500, overlap_pct=0.5):
        window_size_samples = int(window_size_ms / 1000 * 200)
        step_size = int(window_size_samples * (1 - overlap_pct))

        windows = []

        emg_cols = [col for col in df.columns if col.startswith('emg') and col.endswith('_rectified')]
        available_emg = [col for col in emg_cols if col in df.columns]

        if not available_emg:
            print("no emg data")
            return []

        print(f"windows: {window_size_samples} samples ({window_size_ms}ms) {overlap_pct*100}% overlap")
        print(f"emg channels: {len(available_emg)}")

        start_idx = 0
        while start_idx + window_size_samples <= len(df):
            window_data = {
                'start_time': df.iloc[start_idx]['time_s'],
                'end_time': df.iloc[start_idx + window_size_samples - 1]['time_s'],
                'window_size_samples': window_size_samples
            }

            for i, col in enumerate(available_emg):
                emg_data = df[col].iloc[start_idx:start_idx + window_size_samples].values
                emg_features = self.extract_emg_features(emg_data)
                for feat_name, feat_value in emg_features.items():
                    window_data[f'emg{i+1}_{feat_name}'] = feat_value

            windows.append(window_data)
            start_idx += step_size

        print(f"created {len(windows)} windows")
        return windows

    def process_file(self, input_file, output_dir=None):
        print(f"processing {input_file}")

        df = self.load_data(input_file)
        windows = self.create_windows(df)

        if not windows:
            print("no windows")
            return None

        features_df = pd.DataFrame(windows)
        features_df['label'] = 'unknown'

        if output_dir:
            output_file = Path(output_dir) / f"{Path(input_file).stem}_features.csv"
            features_df.to_csv(output_file, index=False)
            print(f"saved {output_file}")
        else:
            print("features:")
            print(features_df.head())

        return features_df

    def process_directory(self, input_dir, output_dir):
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        csv_files = list(input_path.glob("*.csv"))
        print(f"found {len(csv_files)} csv files")

        all_features = []

        for csv_file in csv_files:
            try:
                features_df = self.process_file(csv_file, output_path)
                if features_df is not None:
                    all_features.append(features_df)
            except Exception as e:
                print(f"error {csv_file}: {e}")

        if all_features:
            combined_features = pd.concat(all_features, ignore_index=True)
            output_file = output_path / "all_features.csv"
            combined_features.to_csv(output_file, index=False)
            print(f"saved combined {output_file}")

            summary_file = output_path / "feature_summary.txt"
            with open(summary_file, 'w') as f:
                f.write("Feature Extraction Summary\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total windows: {len(combined_features)}\n")
                f.write(f"EMG features per channel: {len(self.emg_features)}\n")
                f.write(f"IMU features per channel: {len(self.imu_features)}\n")
                f.write(f"Total feature columns: {len(combined_features.columns) - 1}\n")
                f.write(f"Unique labels: {combined_features['label'].unique()}\n")

            print(f"summary {summary_file}")

def main():
    parser = argparse.ArgumentParser(description='extract features')
    parser.add_argument('--input', '-i', type=str, required=True)
    parser.add_argument('--output', '-o', type=str, default='data/features')
    parser.add_argument('--window-size-ms', type=float, default=500)
    parser.add_argument('--overlap-pct', type=float, default=0.5)

    args = parser.parse_args()

    extractor = FeatureExtractor(window_size_ms=args.window_size_ms, overlap_pct=args.overlap_pct)

    if Path(args.input).is_file():
        extractor.process_file(args.input, args.output)
    elif Path(args.input).is_dir():
        extractor.process_directory(args.input, args.output)
    else:
        print(f"error: {args.input} not valid")
        return

if __name__ == '__main__':
    main()
