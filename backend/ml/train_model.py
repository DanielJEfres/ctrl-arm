import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pickle

def extract_features(filepath):
    # extract features from a csv file
    try:
        df = pd.read_csv(filepath)
        
        # get emg columns
        emg_cols = [col for col in df.columns if 'emg' in col.lower()]
        
        if len(emg_cols) < 2:
            return None
        
        emg1_data = df[emg_cols[0]].values
        emg2_data = df[emg_cols[1]].values
        
        # use middle portion for features
        start = int(len(emg1_data) * 0.2)
        end = int(len(emg1_data) * 0.8)
        emg1 = emg1_data[start:end]
        emg2 = emg2_data[start:end]
        
        # calculate baseline from first 20%
        baseline1 = np.mean(emg1_data[:start])
        baseline2 = np.mean(emg2_data[:start])
        
        # extract features
        features = [
            np.mean(emg1),                    # mean
            np.std(emg1),                     # std
            np.max(emg1),                     # max
            np.max(emg1) - np.min(emg1),      # peak to peak
            np.sqrt(np.mean(emg1**2)),        # rms
            np.mean(emg2),
            np.std(emg2),
            np.max(emg2),
            np.max(emg2) - np.min(emg2),
            np.sqrt(np.mean(emg2**2)),
            np.corrcoef(emg1, emg2)[0, 1] if len(emg1) > 1 else 0,  # correlation
            np.mean(emg1) - baseline1,        # activity left
            np.mean(emg2) - baseline2         # activity right
        ]
        
        return features
        
    except Exception as e:
        print(f"error processing {filepath}: {e}")
        return None

def get_label(filename):
    # extract gesture label from filename
    fname = filename.lower()
    
    # map your specific file patterns to gestures
    if 'rest' in fname:
        return 'rest'
    elif 'both_flex' in fname:
        return 'both_flex'
    elif 'left_hard' in fname:
        return 'left_strong'
    elif 'right_hard' in fname:
        return 'right_strong'
    elif 'left_single' in fname or 'left_double' in fname:
        return 'left_flex'
    elif 'right_single' in fname or 'right_double' in fname:
        return 'right_flex'
    elif 'left_hold' in fname:
        return 'left_flex'
    elif 'right_hold' in fname:
        return 'right_flex'
    elif 'left_then_right' in fname or 'right_then_left' in fname:
        return 'both_flex'
    else:
        return None

def train():
    print("training decision tree model")
    print("-"*60)
    
    # find data directory
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
    if not data_dir.exists():
        print("no data directory found!")
        print("please collect gesture data first")
        return
    
    # get csv files
    csv_files = list(data_dir.glob("*.csv"))
    print(f"found {len(csv_files)} csv files")
    
    if len(csv_files) == 0:
        print("no data files found")
        return
    
    # extract features and labels
    X = []
    y = []
    
    print("\nprocessing files...")
    for i, filepath in enumerate(csv_files):
        if i % 20 == 0:
            print(f"  processed {i}/{len(csv_files)} files")
        
        # get label from filename
        label = get_label(filepath.stem)
        if label is None:
            continue
        
        # extract features
        features = extract_features(filepath)
        if features is not None:
            X.append(features)
            y.append(label)
    
    print(f"\nextracted {len(X)} samples")
    
    if len(X) < 10:
        print("not enough data to train (need at least 10 samples)")
        return
    
    # convert to arrays
    X = np.array(X)
    y = np.array(y)
    
    # print class distribution
    unique, counts = np.unique(y, return_counts=True)
    print("\nclass distribution:")
    for label, count in zip(unique, counts):
        print(f"  {label:12s}: {count:3d}")
    
    # split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(unique) > 1 else None
    )
    
    print(f"\ntraining samples: {len(X_train)}")
    print(f"testing samples: {len(X_test)}")
    
    # scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # train decision tree
    print("\ntraining decision tree...")
    model = DecisionTreeClassifier(
        max_depth=4,           # shallow for speed
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )
    
    model.fit(X_train_scaled, y_train)
    
    # evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\nmodel accuracy: {accuracy:.2%}")
    print("\nclassification report:")
    print(classification_report(y_test, y_pred))
    
    # save model
    print("\nsaving model...")
    model_path = Path(__file__).parent / "emg_model.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler
        }, f)
    
    print(f"model saved to {model_path}")
    
    # show feature importances
    print("\nfeature importances:")
    feature_names = [
        'left_mean', 'left_std', 'left_max', 'left_ptp', 'left_rms',
        'right_mean', 'right_std', 'right_max', 'right_ptp', 'right_rms',
        'correlation', 'left_activity', 'right_activity'
    ]
    
    importances = model.feature_importances_
    important_features = [(name, imp) for name, imp in zip(feature_names, importances) if imp > 0.01]
    important_features.sort(key=lambda x: x[1], reverse=True)
    
    for name, importance in important_features:
        print(f"  {name:15s}: {importance:.3f}")
    
    print("\ntraining complete! use smart_control.py to test")

if __name__ == "__main__":
    train()
