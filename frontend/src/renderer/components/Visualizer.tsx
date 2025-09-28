import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import './Visualizer.css'

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

interface VisualizerProps {
  isVisible: boolean
  onClose: () => void
}

function Visualizer({ isVisible, onClose }: VisualizerProps) {
  const [emgData, setEmgData] = useState<EMGData[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [currentGesture, setCurrentGesture] = useState('rest')
  const [connectionStatus, setConnectionStatus] = useState('Disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()

  useEffect(() => {
    if (isVisible) {
      connectWebSocket()
      startVisualization()
    } else {
      disconnectWebSocket()
      stopVisualization()
    }
  }, [isVisible])

  const connectWebSocket = () => {
    try {
      wsRef.current = new WebSocket('ws://localhost:8765')
      
      wsRef.current.onopen = () => {
        setIsConnected(true)
        setConnectionStatus('Connected')
        console.log('Connected to EMG data stream')
      }
      
      wsRef.current.onmessage = (event) => {
        try {
          const data: EMGData = JSON.parse(event.data)
          setEmgData(prev => {
            const newData = [...prev, data]
            // Keep only last 200 data points for performance
            return newData.slice(-200)
          })
          setCurrentGesture(data.gesture)
        } catch (error) {
          console.error('Error parsing EMG data:', error)
        }
      }
      
      wsRef.current.onclose = () => {
        setIsConnected(false)
        setConnectionStatus('Disconnected')
        console.log('Disconnected from EMG data stream')
      }
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
        setConnectionStatus('Connection Error')
      }
    } catch (error) {
      console.error('Failed to connect to EMG data stream:', error)
      setConnectionStatus('Connection Failed')
    }
  }

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }

  const startVisualization = () => {
    const animate = () => {
      drawEMGCharts()
      animationRef.current = requestAnimationFrame(animate)
    }
    animate()
  }

  const stopVisualization = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
    }
  }

  const drawEMGCharts = () => {
    const canvas = canvasRef.current
    if (!canvas || emgData.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight

    const width = canvas.width
    const height = canvas.height
    const padding = 40

    // Clear canvas
    ctx.clearRect(0, 0, width, height)

    // Draw background grid
    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 1
    for (let i = 0; i <= 10; i++) {
      const y = (height - 2 * padding) * (i / 10) + padding
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(width - padding, y)
      ctx.stroke()
    }

    // Draw EMG1 signal (Left)
    if (emgData.length > 1) {
      ctx.strokeStyle = '#ff6b6b'
      ctx.lineWidth = 2
      ctx.beginPath()
      
      emgData.forEach((data, index) => {
        const x = (index / (emgData.length - 1)) * (width - 2 * padding) + padding
        const normalized_emg1 = (data.emg1 - data.baseline_left) / 100 // Normalize for display
        const y = height / 2 - normalized_emg1 * 100 + padding
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
    }

    // Draw EMG2 signal (Right)
    if (emgData.length > 1) {
      ctx.strokeStyle = '#4ecdc4'
      ctx.lineWidth = 2
      ctx.beginPath()
      
      emgData.forEach((data, index) => {
        const x = (index / (emgData.length - 1)) * (width - 2 * padding) + padding
        const normalized_emg2 = (data.emg2 - data.baseline_right) / 100 // Normalize for display
        const y = height / 2 - normalized_emg2 * 100 + padding
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
    }

    // Draw baseline line
    ctx.strokeStyle = '#666'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(padding, height / 2)
    ctx.lineTo(width - padding, height / 2)
    ctx.stroke()
    ctx.setLineDash([])

    // Draw threshold lines
    if (emgData.length > 0) {
      const latestData = emgData[emgData.length - 1]
      
      // Activation threshold
      const activation_y = height / 2 - (latestData.activation_threshold / 100) * 100 + padding
      ctx.strokeStyle = '#ffa500'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.beginPath()
      ctx.moveTo(padding, activation_y)
      ctx.lineTo(width - padding, activation_y)
      ctx.stroke()
      
      // Strong threshold
      const strong_y = height / 2 - (latestData.strong_threshold / 100) * 100 + padding
      ctx.strokeStyle = '#ff4444'
      ctx.beginPath()
      ctx.moveTo(padding, strong_y)
      ctx.lineTo(width - padding, strong_y)
      ctx.stroke()
      ctx.setLineDash([])
    }

    // Draw gesture label
    ctx.fillStyle = '#333'
    ctx.font = 'bold 24px Arial'
    ctx.textAlign = 'center'
    ctx.fillText(currentGesture.toUpperCase(), width / 2, 30)

    // Draw connection status
    ctx.fillStyle = isConnected ? '#4ecdc4' : '#ff6b6b'
    ctx.font = '14px Arial'
    ctx.textAlign = 'left'
    ctx.fillText(`● ${connectionStatus}`, 10, height - 10)

    // Draw signal labels
    ctx.fillStyle = '#ff6b6b'
    ctx.font = '12px Arial'
    ctx.textAlign = 'left'
    ctx.fillText('EMG1 (Left)', 10, 20)
    
    ctx.fillStyle = '#4ecdc4'
    ctx.fillText('EMG2 (Right)', 10, 35)
  }

  if (!isVisible) return null

  return createPortal(
    <div className="visualizer-overlay">
      <div className="visualizer-container">
        <div className="visualizer-header">
          <h2>EMG Real-Time Visualizer</h2>
          <button className="close-btn" onClick={onClose}>×</button>
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
              <span className="gesture-label">Current Gesture:</span>
              <span className={`gesture-value ${currentGesture}`}>
                {currentGesture.toUpperCase()}
              </span>
            </div>
            
            <div className="activity-bars">
              <div className="activity-bar">
                <span>Left EMG</span>
                <div className="bar-container">
                  <div 
                    className="bar left-bar"
                    style={{ 
                      height: `${Math.min(Math.abs(emgData[emgData.length - 1]?.left_activity || 0) * 2, 100)}px`,
                      backgroundColor: (emgData[emgData.length - 1]?.left_activity || 0) > 0 ? '#ff6b6b' : '#ff9999'
                    }}
                  />
                </div>
                <span className="bar-value">
                  {Math.round(emgData[emgData.length - 1]?.left_activity || 0)}
                </span>
              </div>
              
              <div className="activity-bar">
                <span>Right EMG</span>
                <div className="bar-container">
                  <div 
                    className="bar right-bar"
                    style={{ 
                      height: `${Math.min(Math.abs(emgData[emgData.length - 1]?.right_activity || 0) * 2, 100)}px`,
                      backgroundColor: (emgData[emgData.length - 1]?.right_activity || 0) > 0 ? '#4ecdc4' : '#7dd3fc'
                    }}
                  />
                </div>
                <span className="bar-value">
                  {Math.round(emgData[emgData.length - 1]?.right_activity || 0)}
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
    </div>,
    document.body
  )
}

export default Visualizer
