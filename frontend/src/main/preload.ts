import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  toggleWindow: () => ipcRenderer.invoke('toggle-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  restartBackend: () => ipcRenderer.invoke('restart-backend'),
  sendCommand: (command: string) => ipcRenderer.invoke('send-command', command),
  toggleAutoHide: () => ipcRenderer.invoke('toggle-auto-hide'),
  getAutoHideStatus: () => ipcRenderer.invoke('get-auto-hide-status'),
  showVisualizer: () => ipcRenderer.invoke('show-visualizer'),
  hideVisualizer: () => ipcRenderer.invoke('hide-visualizer'),
  
  onBackendOutput: (callback: (data: string) => void) => {
    ipcRenderer.on('backend-output', (event, data) => callback(data))
  },
  onBackendError: (callback: (data: string) => void) => {
    ipcRenderer.on('backend-error', (event, data) => callback(data))
  },
  onBackendClosed: (callback: (code: number) => void) => {
    ipcRenderer.on('backend-closed', (event, code) => callback(code))
  },
  onVisualizerClosed: (callback: () => void) => {
    ipcRenderer.on('visualizer-closed', () => callback())
  },
  
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel)
  }
})

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
