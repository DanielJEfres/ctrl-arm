import React, { useState } from 'react'
import './ControlPanel.css'

const ControlPanel: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(true)

  const handleCommand = async (command: string) => {
    console.log(`Executing command: ${command}`)
    
    const timestamp = new Date().toLocaleTimeString()
    console.log(`[${timestamp}] Command '${command}' executed successfully`)
  }

  const controlButtons = [
    { id: 'start', label: 'Start', command: 'start', icon: '▶️' },
    { id: 'stop', label: 'Stop', command: 'stop', icon: '⏹️' },
    { id: 'pause', label: 'Pause', command: 'pause', icon: '⏸️' },
    { id: 'reset', label: 'Reset', command: 'reset', icon: '🔄' },
    { id: 'calibrate', label: 'Calibrate', command: 'calibrate', icon: '🎯' },
    { id: 'home', label: 'Home', command: 'home', icon: '🏠' }
  ]

  return (
    <div className="control-panel">
      <div className="panel-content">
        <div className="control-grid">
          {controlButtons.map((button) => (
            <button
              key={button.id}
              className="control-button"
              onClick={() => handleCommand(button.command)}
              title={`Send command: ${button.command}`}
            >
              <span className="button-icon">{button.icon}</span>
              <span className="button-label">{button.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ControlPanel
