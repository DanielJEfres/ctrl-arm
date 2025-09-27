import { app, BrowserWindow, ipcMain, screen } from 'electron'
import { join } from 'path'
import { spawn } from 'child_process'

let mainWindow: any = null
let backendProcess: any = null

const isDev = true

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay()
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize
  
  mainWindow = new BrowserWindow({
    width: screenWidth,
    height: 60,
    x: 0,
    y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: false,
    movable: true,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hidden',
    vibrancy: 'under-window',
    visualEffectState: 'active'
  })

  mainWindow.loadURL('http://localhost:5174')
  mainWindow.webContents.openDevTools()

  mainWindow.setIgnoreMouseEvents(false)
  
  mainWindow.show()

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startBackend() {
  console.log('Backend integration disabled - using filler data')
}

app.whenReady().then(() => {
  createWindow()
  startBackend()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill()
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

ipcMain.handle('toggle-window', () => {
  if (mainWindow) {
    if (mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
    }
  }
})

ipcMain.handle('close-window', () => {
  if (mainWindow) {
    mainWindow.close()
  }
})

ipcMain.handle('minimize-window', () => {
  if (mainWindow) {
    mainWindow.minimize()
  }
})

ipcMain.handle('restart-backend', () => {
  startBackend()
})

ipcMain.handle('send-command', async (event, command: string) => {
  console.log(`Simulating command: ${command}`)
  return { 
    success: true, 
    command, 
    result: `Command '${command}' executed successfully (simulated)`,
    timestamp: Date.now()
  }
})
