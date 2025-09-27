import { useEffect } from 'react'

interface ConfigPopupProps {
  isVisible: boolean
  onClose: () => void
}

function ConfigPopup({ isVisible, onClose }: ConfigPopupProps) {
  useEffect(() => {
    if (isVisible) {
      if (window.electronAPI) {
        window.electronAPI.showConfig()
      }
    } else {
      if (window.electronAPI) {
        window.electronAPI.hideConfig()
      }
    }
  }, [isVisible])

  // Listen for close events from the config window
  useEffect(() => {
    const handleConfigClose = () => {
      onClose()
    }

    if (window.electronAPI) {
      window.electronAPI.onConfigClosed(handleConfigClose)
    }

    return () => {
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners('config-closed')
      }
    }
  }, [onClose])

  // This component now just handles the IPC communication
  // The actual config popup is rendered in a separate Electron window
  return null
}

export default ConfigPopup
