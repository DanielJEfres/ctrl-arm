import { useState } from 'react'
import StatusBar from './components/StatusBar'
import logo from '../assets/images/Ctrl-arm-01.svg?url'
import './styles/App.css'
import { Eye } from 'lucide-react';
import { EyeClosed } from 'lucide-react';


declare global {
  interface Window {
    electronAPI: {
      toggleWindow: () => Promise<void>
      closeWindow: () => Promise<void>
      minimizeWindow: () => Promise<void>
      restartBackend: () => Promise<void>
      sendCommand: (command: string) => Promise<any>
      toggleAutoHide: () => Promise<boolean>
      getAutoHideStatus: () => Promise<boolean>
      onBackendOutput: (callback: (data: string) => void) => void
      onBackendError: (callback: (data: string) => void) => void
      onBackendClosed: (callback: (code: number) => void) => void
      removeAllListeners: (channel: string) => void
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

  const [isAutoHideEnabled, setIsAutoHideEnabled] = useState(true)

  const handleClose = () => {
    if (window.electronAPI) {
      window.electronAPI.closeWindow()
    }
  }

  const handleToggleAutoHide = async () => {
    if (window.electronAPI) {
      const newStatus = await window.electronAPI.toggleAutoHide()
      setIsAutoHideEnabled(newStatus)
    }
  }


  return (
    <div className="app">
      <div className="taskbar">
        <div className="taskbar-left">
          <div className="app-title">
            <img 
              src={logo} 
              alt="Ctrl-Arm" 
              style={{ width: '120px', height: '40px' }}
              draggable={false}
            />
          </div>
          <StatusBar 
            status={backendStatus} 
          />
        </div>
        
        <div className="taskbar-center">
          <div className="preset-display">
            <span>Preset</span>
            <span>&nbsp;-&nbsp;</span>
            <span style={{ fontSize: '20px', fontWeight: '600' }}>Default</span>
          </div>
        </div>
        
        <div className="taskbar-right">
          <button 
            className="control-btn auto-hide-btn" 
            onClick={handleToggleAutoHide}
            title={isAutoHideEnabled ? "Disable Auto-Hide" : "Enable Auto-Hide"}
          >
            {isAutoHideEnabled ? <Eye size={16} /> : <EyeClosed size={16} />}
          </button>
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
