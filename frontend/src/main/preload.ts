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
  showConfig: () => ipcRenderer.invoke('show-config'),
  hideConfig: () => ipcRenderer.invoke('hide-config'),
  getConfig: () => ipcRenderer.invoke('get-config'),
  sendVoiceData: (voiceData: any) => ipcRenderer.invoke('send-voice-data', voiceData),
  sendVoiceStatus: (status: any) => ipcRenderer.invoke('send-voice-status', status),
  
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
  onConfigClosed: (callback: () => void) => {
    ipcRenderer.on('config-closed', () => callback())
  },
  onVoiceData: (callback: (data: any) => void) => {
    ipcRenderer.on('voice-data', (event, data) => callback(data))
  },
  onVoiceStatus: (callback: (status: any) => void) => {
    ipcRenderer.on('voice-status', (event, status) => callback(status))
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
      showConfig: () => Promise<void>
      hideConfig: () => Promise<void>
      getConfig: () => Promise<any>
      sendVoiceData: (voiceData: any) => Promise<any>
      sendVoiceStatus: (status: any) => Promise<any>
      onBackendOutput: (callback: (data: string) => void) => void
      onBackendError: (callback: (data: string) => void) => void
      onBackendClosed: (callback: (code: number) => void) => void
      onVisualizerClosed: (callback: () => void) => void
      onConfigClosed: (callback: () => void) => void
      onVoiceData: (callback: (data: any) => void) => void
      onVoiceStatus: (callback: (status: any) => void) => void
      removeAllListeners: (channel: string) => void
    }
  }
}
