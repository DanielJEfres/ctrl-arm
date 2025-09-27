import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from collections import Counter
import joblib
from pathlib import Path
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class EMGNet(nn.Module):
    def __init__(self, input_size, num_classes):
        super(EMGNet, self).__init__()
        # deeper network for better accuracy
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.4),
            
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2),
            
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            
            nn.Linear(32, num_classes)
        )
        
    def forward(self, x):
        return self.network(x)

class EMGDataset(Dataset):
    def __init__(self, features, labels, augment=False):
        self.features = features
        self.labels = labels
        self.augment = augment
        
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        x = self.features[idx].copy()
        
        # data augmentation for training
        if self.augment:
            # add small noise
            x += np.random.normal(0, 0.01, x.shape)
            # random scaling
            x *= np.random.uniform(0.95, 1.05)
            
        return torch.FloatTensor(x), torch.LongTensor([self.labels[idx]])[0]

def train_model():
    # load data
    print("loading data...")
    df = pd.read_csv('../../data/labeled/combined_labeled.csv')
    
    # get features
    feature_cols = [col for col in df.columns if col.startswith('emg') and col != 'emg']
    X = df[feature_cols].values
    
    # encode labels
    labels = df['label'].values
    unique_labels = sorted(df['label'].unique())
    label_to_idx = {label: i for i, label in enumerate(unique_labels)}
    idx_to_label = {i: label for label, i in label_to_idx.items()}
    y = np.array([label_to_idx[label] for label in labels])
    
    print(f"samples: {len(X)}")
    print(f"features: {X.shape[1]}")
    print(f"classes: {len(unique_labels)}")
    
    # show distribution
    counter = Counter(labels)
    for label in unique_labels:
        print(f"  {label}: {counter[label]}")
    
    # split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # normalize
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    
    # handle class imbalance with weighted sampling
    class_counts = np.bincount(y_train)
    weights = 1.0 / class_counts
    sample_weights = weights[y_train]
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(y_train),
        replacement=True
    )
    
    # create datasets
    train_dataset = EMGDataset(X_train, y_train, augment=True)
    test_dataset = EMGDataset(X_test, y_test, augment=False)
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=16, 
        sampler=sampler
    )
    test_loader = DataLoader(
        test_dataset, 
        batch_size=32, 
        shuffle=False
    )
    
    # Use GPU if available
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print(f"using: GPU ({torch.cuda.get_device_name(0)})")
        print(f"cuda version: {torch.version.cuda}")
        print(f"pytorch version: {torch.__version__}")
    else:
        device = torch.device('cpu')
        print("using: CPU (GPU not available)")
    
    model = EMGNet(X_train.shape[1], len(unique_labels)).to(device)
    
    # weighted loss for imbalanced classes
    class_weights = torch.FloatTensor(1.0 / class_counts).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    # optimizer with learning rate scheduling
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=200)
    
    # training
    print("\ntraining...")
    best_acc = 0
    patience = 0
    max_patience = 30
    
    for epoch in range(200):
        # train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
        
        # test
        model.eval()
        test_correct = 0
        test_total = 0
        class_correct = [0] * len(unique_labels)
        class_total = [0] * len(unique_labels)
        
        with torch.no_grad():
            for features, labels in test_loader:
                features, labels = features.to(device), labels.to(device)
                outputs = model(features)
                
                _, predicted = torch.max(outputs, 1)
                test_total += labels.size(0)
                test_correct += (predicted == labels).sum().item()
                
                # per-class accuracy
                for i in range(labels.size(0)):
                    label = labels[i].item()
                    class_total[label] += 1
                    if predicted[i] == labels[i]:
                        class_correct[label] += 1
        
        train_acc = 100 * train_correct / train_total
        test_acc = 100 * test_correct / test_total
        
        scheduler.step()
        
        # print progress
        if (epoch + 1) % 20 == 0:
            print(f"epoch {epoch+1}: train={train_acc:.1f}%, test={test_acc:.1f}%")
        
        # save best model
        if test_acc > best_acc:
            best_acc = test_acc
            patience = 0
            
            # save everything
            Path('models').mkdir(exist_ok=True)
            torch.save({
                'model_state': model.state_dict(),
                'accuracy': best_acc,
                'label_map': label_to_idx,
                'idx_to_label': idx_to_label
            }, 'models/emg_model.pth')
            joblib.dump(scaler, 'models/scaler.pkl')
        else:
            patience += 1
            if patience > max_patience:
                print(f"early stopping at epoch {epoch+1}")
                break
    
    print(f"\nbest accuracy: {best_acc:.1f}%")
    
    # show per-class accuracy
    print("\nper-class accuracy:")
    for i, label in enumerate(unique_labels):
        if class_total[i] > 0:
            acc = 100 * class_correct[i] / class_total[i]
            print(f"  {label}: {acc:.1f}%")
    
    return best_acc

def test_model():
    # load model
    device = torch.device('cpu')
    checkpoint = torch.load('models/emg_model.pth', map_location=device)
    scaler = joblib.load('models/scaler.pkl')
    
    # load test data
    df = pd.read_csv('../../data/labeled/combined_labeled.csv')
    feature_cols = [col for col in df.columns if col.startswith('emg') and col != 'emg']
    X = df[feature_cols].values
    
    # normalize
    X = scaler.transform(X)
    
    # setup model
    model = EMGNet(X.shape[1], len(checkpoint['label_map']))
    model.load_state_dict(checkpoint['model_state'])
    model = model.to(device)
    model.eval()
    
    # predict
    with torch.no_grad():
        outputs = model(torch.FloatTensor(X).to(device))
        _, predicted = torch.max(outputs, 1)
    
    # map back to labels
    idx_to_label = checkpoint['idx_to_label']
    predictions = [idx_to_label[p.item()] for p in predicted.cpu()]
    
    # calculate accuracy
    correct = sum(p == l for p, l in zip(predictions, df['label'].values))
    accuracy = 100 * correct / len(predictions)
    
    print(f"test accuracy: {accuracy:.1f}%")
    return accuracy

if __name__ == '__main__':
    print("emg gesture recognition")
    print("=" * 50)
    
    # check gpu availability
    if torch.cuda.is_available():
        print(f"gpu detected: {torch.cuda.get_device_name(0)}")
        print(f"cuda version: {torch.version.cuda}")
    else:
        print("no gpu detected, using cpu")
    print("=" * 50)
    
    # train
    accuracy = train_model()
    
    # test
    print("\ntesting on full dataset:")
    test_accuracy = test_model()
    
    print("\n" + "=" * 50)
    print("done!")
    print(f"model accuracy: {accuracy:.1f}%")
    print("saved to models/emg_model.pth")