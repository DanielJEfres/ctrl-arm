import { useState, useCallback } from 'react'
import Mainbar from './components/Mainbar'
import Visualizer from './components/Visualizer'
import './styles/App.css'


declare global {
  interface Window {
    electronAPI: {
      toggleWindow: () => Promise<void>
      closeWindow: () => Promise<void>
      minimizeWindow: () => Promise<void>
      restartBackend: () => Promise<void>
      sendCommand: (command: string) => Promise<any>
      toggleAutoHide: () => Promise<boolean>
      getAutoHideStatus: () => Promise<boolean>
      showVisualizer: () => Promise<void>
      hideVisualizer: () => Promise<void>
      onBackendOutput: (callback: (data: string) => void) => void
      onBackendError: (callback: (data: string) => void) => void
      onBackendClosed: (callback: (code: number) => void) => void
      onVisualizerClosed: (callback: () => void) => void
      removeAllListeners: (channel: string) => void
    }
  }
}

interface BackendStatus {
  isRunning: boolean
  lastOutput: string
  error: string | null
}

function App() {
  const [backendStatus] = useState<BackendStatus>({
    isRunning: true,
    lastOutput: 'System initialized successfully',
    error: null
  })

  const [isVisualizerVisible, setIsVisualizerVisible] = useState(false)

  const handleCloseVisualizer = () => {
    setIsVisualizerVisible(false)
  }

  const handleToggleVisualizer = () => {
    setIsVisualizerVisible(!isVisualizerVisible)
  }

  return (
    <>
      <Mainbar 
        backendStatus={backendStatus}
        onToggleVisualizer={handleToggleVisualizer}
      />
      
      <Visualizer 
        isVisible={isVisualizerVisible}
        onClose={handleCloseVisualizer}
      />
      
    </>
  )
}

export default App
