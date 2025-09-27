import { app, BrowserWindow, ipcMain, screen } from 'electron'
import { join } from 'path'

let mainWindow: any = null
let backendProcess: any = null
let hideTimeout: NodeJS.Timeout | null = null
let showTimeout: NodeJS.Timeout | null = null
let isAutoHideEnabled = true
let hoverZoneHeight = 10
const hoverCooldown = 500
const hideCooldown = 1000
let lastHoverState = false
const animationDuration = 300
const animationSteps = 20


function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay()
  const { width: screenWidth } = primaryDisplay.bounds
  
  mainWindow = new BrowserWindow({
    width: screenWidth,
    height: 60,
    minHeight: 60,
    maxHeight: 60,
    x: 0,
    y: 0,
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: false,
    movable: true,
    show: false,
    focusable: false,
    icon: join(__dirname, '../src/assets/images/Ctrl-arm-02.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hidden',
    backgroundColor: '#cccccc'
  })

  mainWindow.loadURL('http://localhost:5174')

  mainWindow.setIgnoreMouseEvents(false)

  if (isAutoHideEnabled) {
    mainWindow.setPosition(0, 0)
    mainWindow.show()
    
    setTimeout(() => {
      if (mainWindow && isAutoHideEnabled) {
        animateWindowToPosition(0, -60)
      }
    }, 10000)
  } else {
    mainWindow.setPosition(0, 0)
    mainWindow.show()
  }
  
  startAutoHideTimer()

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('resize', () => {
    if (mainWindow) {
      const [width, height] = mainWindow.getSize()
      if (height !== 60) {
        mainWindow.setSize(width, 60)
      }
    }
  })

  mainWindow.on('focus', () => {
    if (mainWindow) {
      mainWindow.setSkipTaskbar(false)
    }
  })

  mainWindow.on('blur', () => {
    if (mainWindow) {
      mainWindow.setSkipTaskbar(false)
    }
  })
}

function startBackend() {
}

function animateWindowToPosition(targetX: number, targetY: number) {
  if (!mainWindow) return
  
  const startPos = mainWindow.getPosition()
  const startY = startPos[1]
  const deltaY = targetY - startY
  
  if (Math.abs(deltaY) < 5) {
    mainWindow.setPosition(targetX, targetY)
    return
  }
  
  const steps = 10
  const stepSize = deltaY / steps
  let currentStep = 0
  
  const animate = () => {
    if (currentStep >= steps || !mainWindow) return
    
    currentStep++
    const newY = Math.round(startY + (stepSize * currentStep))
    
    try {
      mainWindow.setPosition(targetX, newY)
    } catch (error) {
      return
    }
    
    if (currentStep < steps) {
      setTimeout(() => animate(), 20)
    }
  }
  
  animate()
}

function startAutoHideTimer() {
  setInterval(() => {
    if (!mainWindow || !isAutoHideEnabled) return
    
    const { screen } = require('electron')
    const cursor = screen.getCursorScreenPoint()
    const primaryDisplay = screen.getPrimaryDisplay()
    const { width: screenWidth } = primaryDisplay.bounds
    const currentPos = mainWindow.getPosition()
    const isWindowVisible = currentPos[1] >= 0
    
    const isInHoverZone = cursor.y <= hoverZoneHeight
    const isOverTaskbar = isWindowVisible && cursor.y <= 60 && cursor.x >= 0 && cursor.x <= screenWidth
    
    if (isInHoverZone || isOverTaskbar) {
      if (!lastHoverState) {
        lastHoverState = true
        if (hideTimeout) {
          clearTimeout(hideTimeout)
          hideTimeout = null
        }
        
        if (!isWindowVisible && !showTimeout) {
          showTimeout = setTimeout(() => {
            if (mainWindow && isAutoHideEnabled) {
              animateWindowToPosition(0, 0)
              mainWindow.show()
              mainWindow.setSkipTaskbar(false)
              mainWindow.blur()
            }
            showTimeout = null
          }, hoverCooldown)
        }
      } else if (isOverTaskbar && hideTimeout) {
        clearTimeout(hideTimeout)
        hideTimeout = null
      }
    } else {
      if (lastHoverState) {
        lastHoverState = false
        if (showTimeout) {
          clearTimeout(showTimeout)
          showTimeout = null
        }
        
        if (isWindowVisible && !hideTimeout) {
          hideTimeout = setTimeout(() => {
            if (mainWindow && isAutoHideEnabled) {
              animateWindowToPosition(0, -60)
            }
            hideTimeout = null
          }, hideCooldown)
        }
      }
    }
  }, 100)
}

app.disableHardwareAcceleration()

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

ipcMain.handle('send-command', async (_, command: string) => {
  return { 
    success: true, 
    command, 
    result: `Command '${command}' executed successfully (simulated)`,
    timestamp: Date.now()
  }
})

ipcMain.handle('toggle-auto-hide', () => {
  isAutoHideEnabled = !isAutoHideEnabled
  if (!isAutoHideEnabled && mainWindow) {
    animateWindowToPosition(0, 0)
    if (hideTimeout) {
      clearTimeout(hideTimeout)
      hideTimeout = null
    }
    if (showTimeout) {
      clearTimeout(showTimeout)
      showTimeout = null
    }
  } else if (isAutoHideEnabled && mainWindow) {
    animateWindowToPosition(0, -60)
  }
  return isAutoHideEnabled
})

ipcMain.handle('get-auto-hide-status', () => {
  return isAutoHideEnabled
})
