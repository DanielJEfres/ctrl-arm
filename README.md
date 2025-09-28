# Ctrl-ARM

**Control your computer with bicep flexes and arm movements. EMG + IMU + decision tree learns your patterns to turn flexes into commands. Hands-free computing for gaming, accessibility & the future.**

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL%20v2.1-blue.svg)](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html)

## 🎯 Inspiration

Traditional input methods like keyboards and mice are limiting, especially for accessibility, gaming, or hands-free computing scenarios. We wanted to create a more natural way to interact with computers using the most intuitive interface of all - our own bodies. The idea of controlling digital systems through muscle flexes and arm movements opens up entirely new possibilities for human-computer interaction, from accessibility applications to immersive gaming experiences.

## 🚀 What it does

Ctrl-ARM is a revolutionary muscle-controlled interface that turns bicep flexes and arm movements into computer commands. Using MyoWare EMG sensors strapped to your biceps and a Seeed Studio XIAO Sense board with built-in IMU and gyroscope, the system detects 12 different muscle gestures including quick taps, sustained holds, and complex combinations. The system tracks both muscle activity and arm movement patterns - detecting acceleration, rotation, and orientation changes to create a comprehensive gesture recognition system. A custom decision tree classifier learns your unique muscle patterns and movement signatures through a personalized calibration process, then translates your flexes and arm motions into precise computer commands. The system also integrates voice control with OpenAI Whisper for speech-to-text transcription and Google Gemini for natural language processing, creating a multi-modal interface that works as a semi-transparent overlay on any application.

## 🏗️ How we built it

We built Ctrl-ARM using a multi-layered architecture combining hardware, AI, and software components:

### Hardware Layer
- **MyoWare EMG sensors** - Capture muscle electrical activity from biceps
- **Seeed Studio XIAO Sense board** - Microcontroller with built-in LSM6DS3 IMU
- **200Hz sampling rate** - Real-time data collection for both EMG and IMU
  <img width="1782" height="1186" alt="image" src="https://github.com/user-attachments/assets/e895beb8-9996-40f0-a773-8ad33e517751" />

- **Serial communication** - USB connection at 115200 baud rate

### AI Layer
- **Scikit-learn Decision Tree Classifier** - 89.87% accuracy gesture recognition
- **Google Gemini** - Natural language processing for voice commands
- **OpenAI Whisper** - Speech-to-text transcription
- **Hybrid detection** - Fast threshold-based + ML-based classification

### Software Layer
- **Python Backend** - Data processing and ML pipelines
- **Electron Frontend** - Semi-transparent overlay UI with React
- **Real-time Communication** - HTTP APIs and serial communication
- **Cross-platform** - Works on Windows, macOS, and Linux

## 🎮 Gesture Recognition

The system recognizes 12 different gestures that can be updated:

| Gesture | Description | Default Key Binding |
|---------|-------------|-------------------|
| `rest` | Relaxed state | None |
| `left_single` | Quick tap on left bicep | Ctrl+C |
| `right_single` | Quick tap on right bicep | Ctrl+V |
| `left_double` | Two quick taps on left | Ctrl+Z |
| `right_double` | Two quick taps on right | Ctrl+Y |
| `left_hold` | Sustained flex on left | Ctrl+S |
| `right_hold` | Sustained flex on right | Ctrl+A |
| `both_flex` | Simultaneous flex | Ctrl+Shift+Z |
| `left_then_right` | Left then right sequence | Custom |
| `right_then_left` | Right then left sequence | Custom |
| `left_hard` | High intensity left flex | Custom |
| `right_hard` | High intensity right flex | Custom |

<img width="1657" height="1486" alt="image" src="https://github.com/user-attachments/assets/fbe2502a-e2e1-4184-8c34-7b25011db13f" />
<img width="2082" height="1186" alt="image" src="https://github.com/user-attachments/assets/328214a4-5d73-4dab-ac3a-ae43117027a4" />


## 🔧 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Hardware      │    │   Backend       │    │   Frontend      │
│                 │    │                 │    │                 │
│ • MyoWare EMG   │◄──►│ • Python ML     │◄──►│ • Electron      │
│ • XIAO Sense    │    │ • Decision Tree │    │ • React UI      │
│ • IMU/Gyro      │    │ • Voice AI      │    │ • Overlay       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

<img width="1811" height="1490" alt="image" src="https://github.com/user-attachments/assets/9d5c856e-c77c-4773-914d-8e61f1500a4b" />


**Made with ❤️ for the future of human-computer interaction**
