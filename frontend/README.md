# Ctrl-Arm Frontend

A semi-transparent Electron overlay application for controlling the ctrl-arm backend hardware operations.

## Features

- **Semi-transparent overlay**: Always-on-top window with glassmorphism design
- **Real-time backend communication**: HTTP API integration with Python backend
- **Control panel**: Send commands to hardware (start, stop, pause, reset, calibrate, home)
- **Live logging**: View backend output and errors in real-time
- **Draggable interface**: Move the overlay window around your screen
- **Minimizable**: Collapse to just the title bar when not needed

## Development Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Python 3.7+ (for backend)

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

This will:
- Start the Vite dev server for the renderer process
- Compile the main Electron process
- Launch the Electron application

### Building for Production

```bash
npm run build
npm run electron
```

## Project Structure

```
frontend/
├── src/
│   ├── main/           # Electron main process
│   │   ├── main.ts     # Main process entry point
│   │   └── preload.ts  # Preload script for secure IPC
│   └── renderer/       # React renderer process
│       ├── components/ # UI components
│       ├── styles/     # CSS styles
│       ├── App.tsx     # Main React component
│       └── main.tsx    # Renderer entry point
├── dist/               # Built files
└── package.json
```

## Backend Integration

The frontend communicates with the Python backend via HTTP API:

- **Status**: `GET http://localhost:8000/status`
- **Commands**: `POST http://localhost:8000/command`
- **Health**: `GET http://localhost:8000/health`

## Available Commands

- `start` - Start hardware operations
- `stop` - Stop hardware operations  
- `pause` - Pause hardware operations
- `reset` - Reset hardware to initial state
- `calibrate` - Calibrate hardware sensors
- `home` - Move to home position

## Customization

The UI can be customized by modifying the CSS files in `src/renderer/styles/`:

- `global.css` - Global styles and reset
- `App.css` - Main application layout
- `StatusBar.css` - Status indicator styling
- `ControlPanel.css` - Control buttons styling
- `LogViewer.css` - Log display styling

## Keyboard Shortcuts

- `Ctrl+Shift+T` - Toggle window visibility (can be added)
- `Ctrl+Q` - Close application (can be added)

## Troubleshooting

### Backend Connection Issues

1. Ensure the Python backend is running on port 8000
2. Check firewall settings
3. Verify backend logs for errors

### Build Issues

1. Clear node_modules and reinstall: `rm -rf node_modules && npm install`
2. Clear dist folder: `rm -rf dist && npm run build`
3. Check Node.js version compatibility

### Window Not Appearing

1. Check if window is minimized to system tray
2. Try Alt+Tab to find the window
3. Restart the application
