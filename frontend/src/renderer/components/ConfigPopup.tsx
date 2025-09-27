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

  return null
}

export default ConfigPopup
