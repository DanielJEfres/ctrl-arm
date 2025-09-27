const { app, BrowserWindow } = require('electron')
const path = require('path')

let mainWindow = null

function createWindow() {
  const { screen } = require('electron')
  const primaryDisplay = screen.getPrimaryDisplay()
  const { width: screenWidth } = primaryDisplay.workAreaSize
  
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
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    titleBarStyle: 'hidden',
    vibrancy: 'under-window',
    visualEffectState: 'active'
  })

  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    mainWindow.loadURL('http://localhost:5179')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
