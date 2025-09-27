import { useState } from 'react'
import Mainbar from './components/Mainbar'
import Visualizer from './components/Visualizer'
import ConfigPopup from './components/ConfigPopup'
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
      showConfig: () => Promise<void>
      hideConfig: () => Promise<void>
      getConfig: () => Promise<any>
      onBackendOutput: (callback: (data: string) => void) => void
      onBackendError: (callback: (data: string) => void) => void
      onBackendClosed: (callback: (code: number) => void) => void
      onVisualizerClosed: (callback: () => void) => void
      onConfigClosed: (callback: () => void) => void
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
  const [isConfigVisible, setIsConfigVisible] = useState(false)

  const handleCloseVisualizer = () => {
    setIsVisualizerVisible(false)
  }

  const handleToggleVisualizer = () => {
    setIsVisualizerVisible(!isVisualizerVisible)
  }

  const handleCloseConfig = () => {
    setIsConfigVisible(false)
  }

  const handleToggleConfig = () => {
    console.log('handleToggleConfig called, current state:', isConfigVisible)
    setIsConfigVisible(!isConfigVisible)
  }

  return (
    <>
      <Mainbar 
        backendStatus={backendStatus}
        onToggleVisualizer={handleToggleVisualizer}
        onToggleConfig={handleToggleConfig}
      />
      
      <Visualizer 
        isVisible={isVisualizerVisible}
        onClose={handleCloseVisualizer}
      />
      
      <ConfigPopup 
        isVisible={isConfigVisible}
        onClose={handleCloseConfig}
      />
      
    </>
  )
}

export default App
