import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import './Visualizer.css'

interface VisualizerProps {
  isVisible: boolean
  onClose: () => void
}

function Visualizer({ isVisible, onClose }: VisualizerProps) {
  useEffect(() => {
    if (isVisible) {
      if (window.electronAPI) {
        window.electronAPI.showVisualizer()
      }
    } else {
      if (window.electronAPI) {
        window.electronAPI.hideVisualizer()
      }
    }
  }, [isVisible])

  // Listen for close events from the visualizer window
  useEffect(() => {
    const handleVisualizerClose = () => {
      onClose()
    }

    if (window.electronAPI) {
      window.electronAPI.onVisualizerClosed(handleVisualizerClose)
    }

    return () => {
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners('visualizer-closed')
      }
    }
  }, [onClose])

  // This component now just handles the IPC communication
  // The actual visualizer is rendered in a separate Electron window
  return null
}

export default Visualizer
