import { app, BrowserWindow, ipcMain, screen } from 'electron'
import { join } from 'path'
import * as fs from 'fs'
import * as yaml from 'js-yaml'

let mainWindow: any = null
let visualizerWindow: any = null
let configWindow: any = null
let backendProcess: any = null
let hideTimeout: NodeJS.Timeout | null = null
let showTimeout: NodeJS.Timeout | null = null
let isAutoHideEnabled = true
let hoverZoneHeight = 10
const hoverCooldown = 500
const hideCooldown = 1000
let lastHoverState = false


function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay()
  const { width: screenWidth } = primaryDisplay.bounds
  
  mainWindow = new BrowserWindow({
    width: screenWidth,
    height: screen.getPrimaryDisplay().bounds.height,
    minHeight: 60,
    maxHeight: screen.getPrimaryDisplay().bounds.height,
    x: 0,
    y: 0,
    frame: false,
    transparent: true,
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
    backgroundColor: 'rgba(0,0,0,0)'
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

  mainWindow.on('close', () => {
    // Clear any pending timers
    if (hideTimeout) {
      clearTimeout(hideTimeout)
      hideTimeout = null
    }
    if (showTimeout) {
      clearTimeout(showTimeout)
      showTimeout = null
    }
    // Force immediate cleanup
    mainWindow.destroy()
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
    mainWindow.destroy()
    mainWindow = null
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

ipcMain.handle('show-visualizer', () => {
  console.log('show-visualizer IPC handler called')
  if (visualizerWindow) {
    console.log('Visualizer window already exists, showing it')
    visualizerWindow.show()
    return
  }
  
  console.log('Creating new visualizer window')
  const primaryDisplay = screen.getPrimaryDisplay()
  const { height: screenHeight } = primaryDisplay.bounds
  
  console.log('Screen height:', screenHeight)
  console.log('Window position: x=50, y=', Math.floor((screenHeight - 600) / 2))
  
  visualizerWindow = new BrowserWindow({
    width: 420, // Wider to accommodate arrow tab
    height: 600,
    x: 50, // Position so arrow tab is visible at x: 0
    y: Math.floor((screenHeight - 600) / 2), // Vertically centered
    frame: false, // No frame for clean look
    transparent: true, // Transparent for glassmorphism effect
    alwaysOnTop: true,
    skipTaskbar: true, // Don't show in taskbar
    resizable: false, // Fixed size
    movable: false, // Fixed position
    show: false,
    focusable: false, // Don't steal focus
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    backgroundColor: 'rgba(0,0,0,0)' // Transparent background
  })
  
  // Show window immediately without loading HTML first
  visualizerWindow.show()
  console.log('Visualizer window shown immediately')
  
  // Load HTML file properly with cache busting
  const htmlPath = join(__dirname, '../src/renderer/visualizer.html')
  console.log('Loading HTML from:', htmlPath)
  
  visualizerWindow.loadFile(htmlPath).then(() => {
    console.log('HTML loaded successfully')
    // Force reload to get latest changes
    visualizerWindow.reload()
  }).catch((error: any) => {
    console.error('Error loading HTML:', error)
  })
  
  visualizerWindow.on('ready-to-show', () => {
    console.log('Visualizer window ready to show')
  })
  
  visualizerWindow.on('show', () => {
    console.log('Visualizer window show event')
  })
  
  visualizerWindow.on('error', (error: any) => {
    console.error('Visualizer window error:', error)
  })
})

ipcMain.handle('hide-visualizer', () => {
  if (visualizerWindow) {
    visualizerWindow.hide()
    visualizerWindow.destroy()
    visualizerWindow = null
    // Notify the main window that the visualizer was closed
    if (mainWindow) {
      mainWindow.webContents.send('visualizer-closed')
    }
  }
})

// Config popup handlers
ipcMain.handle('show-config', () => {
  console.log('show-config IPC handler called')
  if (configWindow) {
    console.log('Config window already exists, showing it')
    configWindow.show()
    return
  }
  
  console.log('Creating new config window')
  const primaryDisplay = screen.getPrimaryDisplay()
  const { height: screenHeight } = primaryDisplay.bounds
  
  configWindow = new BrowserWindow({
    width: 520, // Wider to accommodate arrow tab
    height: 700,
    x: 50, // Position so arrow tab is visible at x: 0
    y: Math.floor((screenHeight - 700) / 2), // Vertically centered
    frame: false, // No frame for clean look
    transparent: true, // Transparent for glassmorphism effect
    alwaysOnTop: true,
    skipTaskbar: true, // Don't show in taskbar
    resizable: false, // Fixed size
    movable: false, // Fixed position
    show: false,
    focusable: false, // Don't steal focus
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    backgroundColor: 'rgba(0,0,0,0)' // Transparent background
  })
  
  // Show window immediately
  configWindow.show()
  console.log('Config window shown immediately')
  
  // Load HTML file
  const htmlPath = join(__dirname, '../src/renderer/config-popup.html')
  console.log('Loading config HTML from:', htmlPath)
  
  // Check if file exists
  if (!fs.existsSync(htmlPath)) {
    console.error('Config HTML file not found at:', htmlPath)
    return
  }
  
  configWindow.loadFile(htmlPath).then(() => {
    console.log('Config HTML loaded successfully')
    configWindow.reload()
  }).catch((error: any) => {
    console.error('Error loading config HTML:', error)
  })
  
  configWindow.on('ready-to-show', () => {
    console.log('Config window ready to show')
  })
  
  configWindow.on('show', () => {
    console.log('Config window show event')
  })
  
  configWindow.on('closed', () => {
    console.log('Config window closed')
    configWindow = null
  })
})

ipcMain.handle('hide-config', () => {
  console.log('hide-config IPC handler called')
  if (configWindow) {
    console.log('Hiding config window')
    configWindow.hide()
    configWindow.destroy()
    configWindow = null
    // Notify the main window that the config was closed
    if (mainWindow) {
      mainWindow.webContents.send('config-closed')
    }
  }
})

ipcMain.handle('get-config', async () => {
  console.log('get-config IPC handler called')
  try {
    // Try multiple possible paths for the config file
    const possiblePaths = [
      join(__dirname, '../../hardware/config.yaml'),
      join(process.cwd(), 'hardware/config.yaml'),
      join(__dirname, '../../../hardware/config.yaml')
    ]
    
    let configPath: string | null = null
    for (const path of possiblePaths) {
      if (fs.existsSync(path)) {
        configPath = path
        break
      }
    }
    
    if (!configPath) {
      console.error('Config file not found in any of the expected locations:', possiblePaths)
      return null
    }
    
    console.log('Reading config from:', configPath)
    
    const configFile = fs.readFileSync(configPath, 'utf8')
    const config = yaml.load(configFile)
    
    console.log('Config loaded successfully:', config)
    return config
  } catch (error) {
    console.error('Error reading config file:', error)
    return null
  }
})
