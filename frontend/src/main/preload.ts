import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  toggleWindow: () => ipcRenderer.invoke('toggle-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  restartBackend: () => ipcRenderer.invoke('restart-backend'),
  sendCommand: (command: string) => ipcRenderer.invoke('send-command', command),
  
  onBackendOutput: (callback: (data: string) => void) => {
    ipcRenderer.on('backend-output', (event, data) => callback(data))
  },
  onBackendError: (callback: (data: string) => void) => {
    ipcRenderer.on('backend-error', (event, data) => callback(data))
  },
  onBackendClosed: (callback: (code: number) => void) => {
    ipcRenderer.on('backend-closed', (event, code) => callback(code))
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
      onBackendOutput: (callback: (data: string) => void) => void
      onBackendError: (callback: (data: string) => void) => void
      onBackendClosed: (callback: (code: number) => void) => void
      removeAllListeners: (channel: string) => void
    }
  }
}
