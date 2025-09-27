const { app, BrowserWindow, screen } = require('electron')

function createMainWindow() {
  const display = screen.getPrimaryDisplay()
  const screenWidth = display.workAreaSize.width
  
  const mainWindow = new BrowserWindow({
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
      nodeIntegration: true,
      contextIsolation: false
    },
    titleBarStyle: 'hidden',
    vibrancy: 'under-window',
    visualEffectState: 'active'
  })

  mainWindow.loadFile('index.html')
}

app.whenReady().then(createMainWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createMainWindow()
  }
})
