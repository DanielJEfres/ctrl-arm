import { useState } from 'react'
import StatusBar from './StatusBar'
import logo from '../../assets/images/Ctrl-arm-01.svg?url'
import { Eye } from 'lucide-react';
import { EyeClosed } from 'lucide-react';
import { Brain } from 'lucide-react';

interface BackendStatus {
  isRunning: boolean
  lastOutput: string
  error: string | null
}

interface MainbarProps {
  backendStatus: BackendStatus
  onToggleVisualizer: () => void
}

function Mainbar({ backendStatus, onToggleVisualizer }: MainbarProps) {
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
          className="control-btn visualizer-btn" 
          onClick={onToggleVisualizer}
          title="Toggle Neural Network Visualizer"
        >
          <Brain size={16} />
        </button>
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
  )
}

export default Mainbar
