import React, { useState, useEffect } from 'react'
import ControlPanel from './components/ControlPanel'
import StatusBar from './components/StatusBar'
import LogViewer from './components/LogViewer'
import './styles/App.css'

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
  const [logs, setLogs] = useState<string[]>([
    '[09:12:34] System startup complete',
    '[09:12:35] Hardware initialized',
    '[09:12:36] Calibration data loaded',
    '[09:12:37] Ready for commands'
  ])
  const [isMinimized, setIsMinimized] = useState(false)

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
      const timestamp = new Date().toLocaleTimeString()
      
      setLogs(prev => [...prev.slice(-19), `[${timestamp}] ${randomMessage}`])
      setBackendStatus(prev => ({ ...prev, lastOutput: randomMessage }))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const handleToggleMinimize = () => {
    setIsMinimized(!isMinimized)
  }

  const handleClose = () => {
    if (window.electronAPI) {
      window.electronAPI.closeWindow()
    }
  }

  const handleRestartBackend = () => {
    setLogs(prev => [...prev.slice(-19), `[${new Date().toLocaleTimeString()}] Backend restart requested`])
    setBackendStatus(prev => ({ ...prev, lastOutput: 'Backend restarting...' }))
    
    setTimeout(() => {
      setLogs(prev => [...prev.slice(-19), `[${new Date().toLocaleTimeString()}] Backend restart complete`])
      setBackendStatus(prev => ({ ...prev, lastOutput: 'Backend online', isRunning: true }))
    }, 2000)
  }

  return (
    <div className="app">
      <div className="taskbar">
        <div className="taskbar-left">
          <div className="app-title">Ctrl-Arm</div>
          <StatusBar 
            status={backendStatus} 
            onRestart={handleRestartBackend}
          />
        </div>
        
        <div className="taskbar-center">
          <ControlPanel />
        </div>
        
        <div className="taskbar-right">
          <button 
            className="control-btn minimize-btn" 
            onClick={handleToggleMinimize}
            title={isMinimized ? "Expand" : "Minimize"}
          >
            {isMinimized ? "▲" : "▼"}
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
      
      {!isMinimized && (
        <div className="dropdown-panel">
          <LogViewer logs={logs} />
        </div>
      )}
    </div>
  )
}

export default App
