# EMG Gesture Recognition

## The Full Process (Super Simple)

### 1. Record Your Gestures
```bash
# First activate your python environment
.\venv\Scripts\activate

# Then start recording data
cd hardware
python quick_collect.py
```
- This pops up a little tool where you record yourself doing different hand gestures
- Do each gesture for like 3-5 seconds (don't rush it)
- It saves everything to `data/raw/` as CSV files

### 2. Turn Raw Data Into Features
```bash
# Switch to the ML folder
cd backend/ml

# Process all your recorded data
python feature_extraction.py --input ../../hardware/data/raw/ --output ../../data/features/
```
- This takes your raw muscle data and extracts useful patterns from it
- It looks at 15 different features per muscle sensor (stuff like average power, frequency, etc.)
- Outputs processed data to `data/features/`

### 3. Auto-Label Your Data
```bash
# This automatically labels your data based on the filenames
python labeling_tool.py --input ../../data/features/ --batch --output ../../data/labeled/combined_labeled.csv
```
- It figures out what gesture each file represents from the filename
- Combines everything into one big labeled dataset
- Saves as `data/labeled/combined_labeled.csv`

### 4. Train The Neural Network
```bash
# This is where the magic happens
python neural_network.py
```
- Feeds all your labeled data into a neural network
- It learns to recognize your specific muscle patterns
- Saves the trained model to `models/emg_model.pth`
- Shows you accuracy for each gesture

### 5. Test It Out
```bash
# The training script also tests the model automatically
python neural_network.py
```
- It runs the model on your training data to see how well it performs
## The 9 Gestures It Learns
- `rest` - Just chillin', hand relaxed
- `flex` - Squeeze those fingers
- `hold` - Keep that position steady
- `click` - Single click motion
- `double_click` - Double click motion
- `wrist_up` - Twist wrist up
- `wrist_down` - Twist wrist down
- `pinch` - Pinch your fingers together
- `fist` - Make a fist

## Your Setup
- 2 MyoWare EMG sensors strapped to your biceps
- Seeed Studio XIAO Sense board (has the IMU and brain)
- Plugged in via USB at 115200 speed

## Pro Tips
- Record 20-30 examples of each gesture for solid accuracy
- Try to do the same motion consistently each time
- The auto-labeling saves a ton of time vs doing it manually
- GPU training is way faster (your RTX 5070 works great with this)
- All ML stuff is in `backend/ml/` now - keeps things organized
- Voice recognition is separate in `backend/voice/` for future features

That's it! Follow these steps and you'll have an AI that can read your muscle signals. Pretty futuristic stuff.



