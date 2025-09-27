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

  return null
}

export default Visualizer
