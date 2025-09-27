import React from 'react'
import './StatusBar.css'

interface BackendStatus {
  isRunning: boolean
  lastOutput: string
  error: string | null
}

interface StatusBarProps {
  status: BackendStatus
  onRestart: () => void
}

const StatusBar: React.FC<StatusBarProps> = ({ status, onRestart }) => {
  return (
    <div className="status-bar">
      <div className="status-indicator">
        <div className={`status-dot ${status.isRunning ? 'running' : 'stopped'}`} />
        <span className="status-text">
          {status.isRunning ? 'Backend Running' : 'Backend Stopped'}
        </span>
      </div>
      
      <div className="status-actions">
        <button 
          className="action-btn restart-btn"
          onClick={onRestart}
          title="Restart Backend"
        >
          🔄
        </button>
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
