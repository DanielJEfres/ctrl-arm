# EMG Gesture Recognition

## The Full Process (Super Simple)

### 1. Run Calibration (First Time Only)
```bash
# First activate your python environment
.\venv\Scripts\activate

# Run calibration to determine personalized thresholds
cd hardware
python quick_collect.py

# Select option 3: "Run calibration (personalized thresholds)"
# Follow the 9-step calibration process
```
- This determines your personalized muscle thresholds
- Required for accurate gesture recognition
- Saves calibration to `data/raw/calibration_thresholds.json`

### 2. Record Your Gestures
```bash
# Continue with data collection
# Select option 1 or 2 from the menu
```
- Now collect training data using your calibrated thresholds
- Each gesture should be recorded for 3-8 seconds
- Saves raw data to `data/raw/` as CSV files

### 3. Turn Raw Data Into Features
```bash
# Switch to the ML folder
cd backend/ml

# Process all your recorded data
python feature_extraction.py --input ../../hardware/data/raw/ --output ../../data/features/
```
- This takes your raw muscle data and extracts useful patterns from it
- It looks at 15 different features per muscle sensor (stuff like average power, frequency, etc.)
- Outputs processed data to `data/features/`

### 4. Auto-Label Your Data
```bash
# This automatically labels your data based on the filenames
python labeling_tool.py --input ../../data/features/ --batch --output ../../data/labeled/combined_labeled.csv
```
- It figures out what gesture each file represents from the filename
- Combines everything into one big labeled dataset
- Saves as `data/labeled/combined_labeled.csv`

### 5. Train The Neural Network
```bash
# This is where the magic happens
python neural_network.py
```
- Feeds all your labeled data into a neural network
- It learns to recognize your specific muscle patterns
- Saves the trained model to `models/emg_model.pth`
- Shows you accuracy for each gesture

### 6. Test It Out
```bash
# The training script also tests the model automatically
python neural_network.py
```
- It runs the model on your training data to see how well it performs
## The 12 Gestures It Learns
- `rest` - Just chillin', hand relaxed
- `left_single` - Quick tap flex on left bicep
- `right_single` - Quick tap flex on right bicep
- `left_double` - Two quick taps on left
- `right_double` - Two quick taps on right
- `left_hold` - Sustained flex (>300–500 ms) on left
- `right_hold` - Sustained flex on right
- `both_flex` - Simultaneous flex (within ~150 ms)
- `left_then_right` - Left tap then right within ~300 ms
- `right_then_left` - Right tap then left within ~300 ms
- `left_hard` - High intensity flex on left
- `right_hard` - High intensity flex on right

## Your Setup
- 2 MyoWare EMG sensors strapped to your biceps
- Seeed Studio XIAO Sense board (has the IMU and brain)
- Plugged in via USB at 115200 speed

## Pro Tips
- **Calibration is crucial!** - Run it first to get personalized thresholds
- Record 20-30 examples of each gesture for solid accuracy
- Try to do the same motion consistently each time
- The auto-labeling saves a ton of time vs doing it manually
- GPU training is way faster (your RTX 5070 works great with this)
- All ML stuff is in `backend/ml/` now - keeps things organized
- Voice recognition is separate in `backend/voice/` for future features
- Recalibrate if you notice accuracy dropping (muscles fatigue over time)



