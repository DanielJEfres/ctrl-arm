import { useEffect, useRef, useState, useCallback } from 'react'
import './Visualizer.css'

// declare electron api for typescript
declare global {
  interface Window {
    electronAPI: {
      showEMGVisualizer: () => Promise<void>
      hideVisualizer: () => Promise<void>
    }
  }
}

interface EMGData {
  timestamp: number
  emg1: number
  emg2: number
  left_activity: number
  right_activity: number
  gesture: string
  baseline_left: number
  baseline_right: number
  activation_threshold: number
  strong_threshold: number
}

type GestureType = 'rest' | 'left_flex' | 'right_flex' | 'both_flex' | 'left_strong' | 'right_strong' | 'both_strong'

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error'

interface VisualizerProps {
  isVisible: boolean
  onClose: () => void
}

function Visualizer({ isVisible, onClose }: VisualizerProps) {
  const [emgData, setEmgData] = useState<EMGData[]>([])
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [currentGesture, setCurrentGesture] = useState<GestureType>('rest')
  const [connectionStatus, setConnectionStatus] = useState<string>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | undefined>(undefined)

  const connectWebSocket = useCallback(() => {
    try {
      setConnectionStatus('connecting')
      wsRef.current = new WebSocket('ws://localhost:8765')
      
      wsRef.current.onopen = () => {
        setIsConnected(true)
        setConnectionStatus('connected')
        console.log('connected to emg data stream')
      }
      
      wsRef.current.onmessage = (event) => {
        try {
          const data: EMGData = JSON.parse(event.data)
          setEmgData(prev => {
            const newData = [...prev, data]
            return newData.slice(-200) // keep only last 200 data points
          })
          setCurrentGesture(data.gesture as GestureType)
        } catch (error) {
          console.error('error parsing emg data:', error)
        }
      }
      
      wsRef.current.onclose = () => {
        setIsConnected(false)
        setConnectionStatus('disconnected')
        console.log('disconnected from emg data stream')
      }
      
      wsRef.current.onerror = (error) => {
        console.error('websocket error:', error)
        setIsConnected(false)
        setConnectionStatus('error')
      }
    } catch (error) {
      console.error('failed to connect to emg data stream:', error)
      setConnectionStatus('error')
    }
  }, [])

  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const drawEMGCharts = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || emgData.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // set canvas size
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight

    const width = canvas.width
    const height = canvas.height
    const padding = 40

    // clear canvas
    ctx.clearRect(0, 0, width, height)

    // draw background grid
    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 1
    for (let i = 0; i <= 10; i++) {
      const y = (height - 2 * padding) * (i / 10) + padding
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(width - padding, y)
      ctx.stroke()
    }

    // draw emg1 signal (left)
    if (emgData.length > 1) {
      ctx.strokeStyle = '#ff6b6b'
      ctx.lineWidth = 2
      ctx.beginPath()
      
      emgData.forEach((data, index) => {
        const x = (index / (emgData.length - 1)) * (width - 2 * padding) + padding
        const normalized_emg1 = (data.emg1 - data.baseline_left) / 100
        const y = height / 2 - normalized_emg1 * 100 + padding
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
    }

    // draw emg2 signal (right)
    if (emgData.length > 1) {
      ctx.strokeStyle = '#4ecdc4'
      ctx.lineWidth = 2
      ctx.beginPath()
      
      emgData.forEach((data, index) => {
        const x = (index / (emgData.length - 1)) * (width - 2 * padding) + padding
        const normalized_emg2 = (data.emg2 - data.baseline_right) / 100
        const y = height / 2 - normalized_emg2 * 100 + padding
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
    }

    // draw baseline line
    ctx.strokeStyle = '#666'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(padding, height / 2)
    ctx.lineTo(width - padding, height / 2)
    ctx.stroke()
    ctx.setLineDash([])

    // draw threshold lines
    if (emgData.length > 0) {
      const latestData = emgData[emgData.length - 1]
      
      // activation threshold
      const activation_y = height / 2 - (latestData.activation_threshold / 100) * 100 + padding
      ctx.strokeStyle = '#ffa500'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.beginPath()
      ctx.moveTo(padding, activation_y)
      ctx.lineTo(width - padding, activation_y)
      ctx.stroke()
      
      // strong threshold
      const strong_y = height / 2 - (latestData.strong_threshold / 100) * 100 + padding
      ctx.strokeStyle = '#ff4444'
      ctx.beginPath()
      ctx.moveTo(padding, strong_y)
      ctx.lineTo(width - padding, strong_y)
      ctx.stroke()
      ctx.setLineDash([])
    }

    // draw labels
    ctx.fillStyle = '#333'
    ctx.font = 'bold 24px Arial'
    ctx.textAlign = 'center'
    ctx.fillText(currentGesture.toUpperCase(), width / 2, 30)

    // draw connection status
    ctx.fillStyle = isConnected ? '#4ecdc4' : '#ff6b6b'
    ctx.font = '14px Arial'
    ctx.textAlign = 'left'
    ctx.fillText(`● ${connectionStatus}`, 10, height - 10)

    // draw signal labels
    ctx.fillStyle = '#ff6b6b'
    ctx.font = '12px Arial'
    ctx.fillText('emg1 (left)', 10, 20)
    
    ctx.fillStyle = '#4ecdc4'
    ctx.fillText('emg2 (right)', 10, 35)
  }, [emgData, currentGesture, isConnected, connectionStatus])

  const startVisualization = useCallback(() => {
    const animate = () => {
      drawEMGCharts()
      animationRef.current = requestAnimationFrame(animate)
    }
    animate()
  }, [drawEMGCharts])

  const stopVisualization = useCallback(() => {
    if (animationRef.current !== undefined) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = undefined
    }
  }, [])

  useEffect(() => {
    if (isVisible) {
      // use electron ipc to show system-level window
      if (window.electronAPI) {
        window.electronAPI.showEMGVisualizer()
        onClose() // close the react overlay since we're using electron window
        return
      }
      // fallback for web mode
      connectWebSocket()
      startVisualization()
    } else {
      disconnectWebSocket()
      stopVisualization()
    }
    
    return () => {
      disconnectWebSocket()
      stopVisualization()
    }
  }, [isVisible, connectWebSocket, disconnectWebSocket, startVisualization, stopVisualization, onClose])


  // if electron api is available, don't render react overlay
  // the electron window will handle the visualization
  if (!isVisible || window.electronAPI) return null

  // fallback react overlay for web mode
  return (
    <div className="visualizer-overlay">
      <div className="visualizer-container">
        <div className="visualizer-header">
          <h2>emg real-time visualizer</h2>
          <button className="close-btn" onClick={onClose} aria-label="close visualizer">×</button>
        </div>
        
        <div className="visualizer-content">
          <div className="emg-chart-container">
            <canvas 
              ref={canvasRef}
              className="emg-chart"
              style={{ width: '100%', height: '400px' }}
            />
          </div>
          
          <div className="gesture-info">
            <div className="gesture-display">
              <span className="gesture-label">current gesture:</span>
              <span className={`gesture-value ${currentGesture}`}>
                {currentGesture.replace('_', ' ')}
              </span>
            </div>
            
            <div className="activity-bars">
              <div className="activity-bar">
                <span>left emg</span>
                <div className="bar-container">
                  <div 
                    className="bar left-bar"
                    style={{ 
                      height: `${Math.min(Math.abs(emgData[emgData.length - 1]?.left_activity ?? 0) * 2, 100)}px`,
                      backgroundColor: (emgData[emgData.length - 1]?.left_activity ?? 0) > 0 ? '#ff6b6b' : '#ff9999'
                    }}
                  />
                </div>
                <span className="bar-value">
                  {Math.round(emgData[emgData.length - 1]?.left_activity ?? 0)}
                </span>
              </div>
              
              <div className="activity-bar">
                <span>right emg</span>
                <div className="bar-container">
                  <div 
                    className="bar right-bar"
                    style={{ 
                      height: `${Math.min(Math.abs(emgData[emgData.length - 1]?.right_activity ?? 0) * 2, 100)}px`,
                      backgroundColor: (emgData[emgData.length - 1]?.right_activity ?? 0) > 0 ? '#4ecdc4' : '#7dd3fc'
                    }}
                  />
                </div>
                <span className="bar-value">
                  {Math.round(emgData[emgData.length - 1]?.right_activity ?? 0)}
                </span>
              </div>
            </div>
            
            <div className="connection-status">
              <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
                ●
              </span>
              <span className="status-text">{connectionStatus}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Visualizer
