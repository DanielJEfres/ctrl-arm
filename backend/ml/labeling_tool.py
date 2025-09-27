import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import os
import sys

class LabelingTool:
    def __init__(self, input_file, output_file=None):
        self.input_file = input_file
        self.output_file = output_file or f"{Path(input_file).stem}_labeled.csv"

        self.gesture_labels = {
            '0': 'rest',
            '1': 'flex',
            '2': 'hold',
            '3': 'click',
            '4': 'double_click',
            '5': 'wrist_up',
            '6': 'wrist_down',
            '7': 'wrist_left',
            '8': 'wrist_right',
            '9': 'pinch',
            'a': 'fist',
            'b': 'wave',
            'c': 'scroll_up',
            'd': 'scroll_down',
            'e': 'unknown'
        }

        self.reverse_labels = {v: k for k, v in self.gesture_labels.items()}

    def load_data(self):
        print(f"loading {self.input_file}")

        if not os.path.exists(self.input_file):
            print(f"error: {self.input_file} not found")
            return None

        df = pd.read_csv(self.input_file)

        if 'label' not in df.columns:
            print("error: no label column")
            return None

        label_counts = df['label'].value_counts()
        print(f"labels: {label_counts}")

        return df

    def display_gesture_options(self):
        print("\n" + "="*60)
        print("gesture labels:")
        print("="*60)

        for key, gesture in self.gesture_labels.items():
            print(f"  {key}: {gesture}")

        print("\n" + "="*60)
        print("commands:")
        print("  [number/letter]: label window")
        print("  s: skip window")
        print("  q: quit")
        print("  h: help")
        print("  stats: show stats")
        print("="*60)

    def auto_label_from_filename(self, df):
        """Auto-label windows based on original CSV filename"""
        print("auto-labeling based on filenames...")

        labeled_df = df.copy()
        labeled_df['new_label'] = 'unknown'

        # Map filename prefixes to gesture labels
        gesture_map = {
            'rest': 'rest',
            'flex': 'flex',
            'hold': 'hold',
            'click': 'click',
            'double_click': 'double_click',
            'wrist_up': 'wrist_up',
            'wrist_down': 'wrist_down',
            'wrist_left': 'wrist_left',
            'wrist_right': 'wrist_right',
            'pinch': 'pinch',
            'fist': 'fist',
            'wave': 'wave',
            'scroll_up': 'scroll_up',
            'scroll_down': 'scroll_down',
            'scroll': 'scroll_up',  # fallback for scroll files
            'wrist': 'wrist_up'      # fallback for wrist files
        }

        labeled_count = 0

        for filename, group in df.groupby('filename'):
            # Extract gesture from filename (e.g., 'rest_20250926_232229.csv' -> 'rest')
            gesture = filename.split('_')[0]

            if gesture in gesture_map:
                label = gesture_map[gesture]
                labeled_df.loc[group.index, 'new_label'] = label
                labeled_count += len(group)
                print(f"  {filename}: {len(group)} windows -> {label}")
            else:
                print(f"  {filename}: unknown gesture '{gesture}'")

        print(f"auto-labeled: {labeled_count} windows")
        return labeled_df, True

    def auto_label_individual_files(self, input_dir, output_file):
        """Auto-label individual feature files and combine them"""
        import glob
        import os

        print(f"auto-labeling files in {input_dir}")

        # Find all feature files
        pattern = os.path.join(input_dir, '*_features.csv')
        feature_files = glob.glob(pattern)

        if not feature_files:
            print(f"no feature files found in {input_dir}")
            return None

        all_labeled_dfs = []
        total_windows = 0

        # Map filename prefixes to gesture labels
        gesture_map = {
            'rest': 'rest',
            'flex': 'flex',
            'hold': 'hold',
            'click': 'click',
            'double_click': 'double_click',
            'wrist_up': 'wrist_up',
            'wrist_down': 'wrist_down',
            'wrist_left': 'wrist_left',
            'wrist_right': 'wrist_right',
            'pinch': 'pinch',
            'fist': 'fist',
            'wave': 'wave',
            'scroll_up': 'scroll_up',
            'scroll_down': 'scroll_down',
            'scroll': 'scroll_up',  # fallback for scroll files
            'wrist': 'wrist_up'      # fallback for wrist files
        }

        for file_path in feature_files:
            filename = os.path.basename(file_path)
            print(f"processing {filename}")

            # Extract gesture from filename
            gesture = filename.split('_')[0]

            if gesture not in gesture_map:
                print(f"  skipping {filename}: unknown gesture '{gesture}'")
                continue

            # Load the feature file
            try:
                df = pd.read_csv(file_path)
                if 'label' not in df.columns:
                    print(f"  error: no label column in {filename}")
                    continue

                # Add filename column for grouping
                df['filename'] = filename

                # Auto-label based on gesture
                label = gesture_map[gesture]
                df['label'] = label  # Directly update the label column

                all_labeled_dfs.append(df)
                total_windows += len(df)
                print(f"  {filename}: {len(df)} windows -> {label}")

            except Exception as e:
                print(f"  error processing {filename}: {e}")

        if not all_labeled_dfs:
            print("no files processed")
            return None

        # Combine all labeled dataframes
        combined_df = pd.concat(all_labeled_dfs, ignore_index=True)
        combined_df = combined_df.drop('filename', axis=1)

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"created directory: {output_dir}")

        # Save combined result
        combined_df.to_csv(output_file, index=False)
        print(f"saved {output_file} with {total_windows} windows")

        # Show final label distribution
        label_counts = combined_df['label'].value_counts()
        print(f"final label distribution: {label_counts}")

        return combined_df

    def label_windows(self, df):
        print(f"labeling {len(df)} windows")
        print(f"total windows: {len(df)}")

        labeled_df = df.copy()
        labeled_df['new_label'] = 'unknown'

        labeled_count = 0
        skipped_count = 0

        self.display_gesture_options()

        # Add auto-label option
        print("  auto: auto-label based on filenames")

        for idx, row in df.iterrows():
            print(f"\nwindow {idx + 1}/{len(df)}")
            print(f"time: {row['start_time']:.2f}s - {row['end_time']:.2f}s")
            print(f"duration: {row['end_time'] - row['start_time']:.2f}s")

            if 'emg1_mav' in row:
                print(f"emg1: {row['emg1_mav']:.2f}")
            if 'emg2_mav' in row:
                print(f"emg2: {row['emg2_mav']:.2f}")

            while True:
                try:
                    choice = input("label: ").strip().lower()

                    if choice in self.gesture_labels:
                        gesture = self.gesture_labels[choice]
                        labeled_df.at[idx, 'new_label'] = gesture
                        labeled_count += 1
                        print(f"labeled: {gesture}")
                        break

                    elif choice == 's':
                        labeled_df.at[idx, 'new_label'] = 'skipped'
                        skipped_count += 1
                        print("skipped")
                        break

                    elif choice == 'auto':
                        # Auto-label the rest based on filenames
                        auto_df, _ = self.auto_label_from_filename(df.iloc[idx:])
                        labeled_df.update(auto_df)
                        labeled_count += len(df) - idx
                        print(f"auto-labeled remaining {len(df) - idx} windows")
                        return labeled_df, True

                    elif choice == 'q':
                        print("exiting")
                        return labeled_df, False

                    elif choice == 'h':
                        self.display_gesture_options()
                        print("  auto: auto-label based on filenames")

                    elif choice == 'stats':
                        current_stats = labeled_df['new_label'].value_counts()
                        print(f"stats: {current_stats}")

                    else:
                        print("invalid")

                except KeyboardInterrupt:
                    print("interrupted")
                    return labeled_df, False

        print(f"done: {labeled_count} labeled, {skipped_count} skipped")
        return labeled_df, True

    def save_labeled_data(self, df):
        # Update the label column with new_label values
        df['label'] = df['new_label']
        df = df.drop('new_label', axis=1)
        df = df[df['label'] != 'skipped']

        df.to_csv(self.output_file, index=False)
        print(f"saved {self.output_file}")

        final_stats = df['label'].value_counts()
        print(f"final: {final_stats}")

        return df

def main():
    parser = argparse.ArgumentParser(description='label features')
    parser.add_argument('--input', '-i', type=str, required=True)
    parser.add_argument('--output', '-o', type=str)
    parser.add_argument('--auto', action='store_true', help='auto-label based on filenames')
    parser.add_argument('--batch', action='store_true', help='batch process individual feature files')

    args = parser.parse_args()

    if args.batch:
        # Batch process individual files
        tool = LabelingTool(None, args.output)
        result = tool.auto_label_individual_files(args.input, args.output or '../data/labeled/combined_labeled.csv')
        if result is not None:
            print("batch auto-labeling done")
        else:
            print("batch auto-labeling failed")
        return

    tool = LabelingTool(args.input, args.output)
    df = tool.load_data()
    if df is None:
        return

    if args.auto:
        # Auto-label everything
        labeled_df, completed = tool.auto_label_from_filename(df)
        if completed:
            tool.save_labeled_data(labeled_df)
            print("auto-labeling done")
        else:
            print("auto-labeling failed")
    else:
        # Interactive labeling
        labeled_df, completed = tool.label_windows(df)

        if completed:
            tool.save_labeled_data(labeled_df)
            print("labeling done")
        else:
            print("labeling stopped")

if __name__ == '__main__':
    main()
