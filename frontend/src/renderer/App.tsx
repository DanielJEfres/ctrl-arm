import { useState } from 'react'
import StatusBar from './components/StatusBar'
import logo from '../assets/images/Ctrl-arm-01.svg?url'
import './styles/App.css'

declare global {
  interface Window {
    electronAPI: {
      closeWindow: () => void
      minimizeWindow: () => void
      toggleWindow: () => void
      sendCommand: (command: string) => Promise<any>
    }
  }
}

interface BackendStatus {
  isRunning: boolean
  lastOutput: string
  error: string | null
}

function App() {
  const [backendStatus] = useState<BackendStatus>({
    isRunning: true,
    lastOutput: 'System initialized successfully',
    error: null
  })


  const handleClose = () => {
    if (window.electronAPI) {
      window.electronAPI.closeWindow()
    }
  }


  return (
    <div className="app w-full" style={{width: '100vw'}}>
      <div className="taskbar w-full" style={{width: '100%'}}>
        <div className="taskbar-left">
          <div className="app-title">
            <img 
              src={logo} 
              alt="Ctrl-Arm" 
              style={{ width: '120px', height: '40px' }}
              draggable={false}
              onLoad={() => console.log('Image loaded successfully')}
              onError={(e) => console.log('Image failed to load:', e)}
            />
          </div>
          <StatusBar 
            status={backendStatus} 
          />
        </div>
        
        <div className="taskbar-center w-full">
          {/* Empty center to fill space */}
        </div>
        
        <div className="taskbar-right">
          <button 
            className="control-btn close-btn" 
            onClick={handleClose}
            title="Close"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
