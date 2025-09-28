import { useState, useEffect } from 'react'
import StatusBar from './StatusBar'
import logo from '../../assets/images/Ctrl-arm-01.svg?url'
import { Eye } from 'lucide-react';
import { EyeClosed } from 'lucide-react';

interface BackendStatus {
  isRunning: boolean
  lastOutput: string
  error: string | null
}

interface MainbarProps {
  backendStatus: BackendStatus
}

function Mainbar({ backendStatus }: MainbarProps) {
  const [isAutoHideEnabled, setIsAutoHideEnabled] = useState(true)
  const [currentMode, setCurrentMode] = useState('Default')

  useEffect(() => {
    const loadConfig = async () => {
      if (window.electronAPI) {
        try {
          const config = await window.electronAPI.getConfig()
          if (config && config.active_profile) {
            const modeName = config.active_profile.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
            setCurrentMode(modeName)
          }
        } catch (error) {
          console.error('Failed to load config:', error)
        }
      }
    }

    loadConfig()
    
    // Poll for config changes every 5 seconds
    const interval = setInterval(loadConfig, 5000)
    
    return () => clearInterval(interval)
  }, [])

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
          <span style={{ fontSize: '20px', fontWeight: '600' }}>{currentMode}</span>
        </div>
      </div>
      
      <div className="taskbar-right">
        <button 
          className="control-btn auto-hide-btn" 
          onClick={handleToggleAutoHide}
          title={isAutoHideEnabled ? "Disable Auto-Hide" : "Enable Auto-Hide"}
        >
          {isAutoHideEnabled ? <EyeClosed size={16} /> : <Eye size={16} />}
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
  )
}

export default Mainbar
