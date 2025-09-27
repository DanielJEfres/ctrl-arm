import React, { useRef, useEffect, useState } from 'react'
import './LogViewer.css'

interface LogViewerProps {
  logs: string[]
}

const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
  const logContainerRef = useRef<HTMLDivElement>(null)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="log-viewer">
      <div className="log-header">
        <h3>Logs</h3>
        <div className="log-controls">
          <span className="log-count">{logs.length} entries</span>
          <button 
            className="expand-btn"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
      </div>
      
      {isExpanded && (
        <div className="log-content">
          <div className="log-container" ref={logContainerRef}>
            {logs.length === 0 ? (
              <div className="no-logs">No logs yet...</div>
            ) : (
              logs.map((log, index) => (
                <div 
                  key={index} 
                  className={`log-entry ${log.includes('ERROR') ? 'error' : ''}`}
                >
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default LogViewer
