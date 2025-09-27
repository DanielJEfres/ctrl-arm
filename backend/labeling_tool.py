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

    def label_windows(self, df):
        print(f"labeling {len(df)} windows")
        print(f"total windows: {len(df)}")

        labeled_df = df.copy()
        labeled_df['new_label'] = 'unknown'

        labeled_count = 0
        skipped_count = 0

        self.display_gesture_options()

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

                    elif choice == 'q':
                        print("exiting")
                        return labeled_df, False

                    elif choice == 'h':
                        self.display_gesture_options()

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

    args = parser.parse_args()

    tool = LabelingTool(args.input, args.output)
    df = tool.load_data()
    if df is None:
        return

    labeled_df, completed = tool.label_windows(df)

    if completed:
        tool.save_labeled_data(labeled_df)
        print("labeling done")
    else:
        print("labeling stopped")

if __name__ == '__main__':
    main()
