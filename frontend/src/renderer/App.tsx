import { useState, useEffect } from 'react'
import StatusBar from './components/StatusBar'
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
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({
    isRunning: true,
    lastOutput: 'System initialized successfully',
    error: null
  })

  useEffect(() => {
    const interval = setInterval(() => {
      const fillerMessages = [
        'System status: OK',
        'Temperature: 24.5°C',
        'Position updated',
        'Sensor readings nominal',
        'Heartbeat received',
        'Memory usage: 45%'
      ]
      
      const randomMessage = fillerMessages[Math.floor(Math.random() * fillerMessages.length)]
      
      setBackendStatus(prev => ({ ...prev, lastOutput: randomMessage }))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const handleClose = () => {
    if (window.electronAPI) {
      window.electronAPI.closeWindow()
    }
  }

  const handleRestartBackend = () => {
    setBackendStatus(prev => ({ ...prev, lastOutput: 'Backend restarting...' }))
    
    setTimeout(() => {
      setBackendStatus(prev => ({ ...prev, lastOutput: 'Backend online', isRunning: true }))
    }, 2000)
  }

  return (
    <div className="app w-full" style={{width: '100vw'}}>
      <div className="taskbar w-full" style={{width: '100%'}}>
        <div className="taskbar-left">
          <div className="app-title">Ctrl-Arm</div>
          <StatusBar 
            status={backendStatus} 
            onRestart={handleRestartBackend}
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
