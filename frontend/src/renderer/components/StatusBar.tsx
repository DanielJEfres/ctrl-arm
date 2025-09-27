import React from 'react'
import './StatusBar.css'

interface BackendStatus {
  isRunning: boolean
  lastOutput: string
  error: string | null
}

interface StatusBarProps {
  status: BackendStatus
}

const StatusBar: React.FC<StatusBarProps> = ({ status }) => {
  return (
    <div className="status-bar">
      <div className="status-indicator">
        <div className={`status-dot ${status.isRunning ? 'running' : 'stopped'}`} />
        <span className="status-text">
          {status.isRunning ? 'Running' : 'Stopped'}
        </span>
      </div>
      
      {status.error && (
        <div className="error-message">
          ⚠️ {status.error}
        </div>
      )}
    </div>
  )
}

export default StatusBar
