import { app, BrowserWindow, ipcMain, screen } from 'electron'
import { join } from 'path'
import * as fs from 'fs'
import * as yaml from 'js-yaml'
import * as express from 'express'
import * as cors from 'cors'

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

let sidebarHoverZoneWidth = 20
let sidebarHoverCooldown = 300
let sidebarHideCooldown = 800
let lastSidebarHoverState = false
let sidebarHideTimeout: NodeJS.Timeout | null = null
let sidebarShowTimeout: NodeJS.Timeout | null = null

// Express server for voice data
let voiceServer: any = null

function setupVoiceServer() {
  const app = express()
  
  app.use(cors())
  app.use(express.json())
  
  // Voice data endpoint
  app.post('/api/voice-data', (req, res) => {
    console.log('Voice data received via HTTP:', req.body)
    
    // Send to visualizer window if it exists
    if (visualizerWindow && !visualizerWindow.isDestroyed()) {
      visualizerWindow.webContents.send('voice-data', req.body)
    }
    
    // Also send to main window for potential logging
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('voice-data', req.body)
    }
    
    res.json({ success: true })
  })
  
  // Voice status endpoint
  app.post('/api/voice-status', (req, res) => {
    console.log('Voice status received via HTTP:', req.body)
    
    // Send to visualizer window if it exists
    if (visualizerWindow && !visualizerWindow.isDestroyed()) {
      visualizerWindow.webContents.send('voice-status', req.body)
    }
    
    // Also send to main window for potential logging
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('voice-status', req.body)
    }
    
    res.json({ success: true })
  })
  
  voiceServer = app.listen(3000, () => {
    console.log('Voice server listening on port 3000')
  })
}

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
    if (hideTimeout) {
      clearTimeout(hideTimeout)
      hideTimeout = null
    }
    if (showTimeout) {
      clearTimeout(showTimeout)
      showTimeout = null
    }
    
    if (visualizerWindow) {
      visualizerWindow.destroy()
      visualizerWindow = null
    }
    
    if (configWindow) {
      configWindow.destroy()
      configWindow = null
    }
    
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

function animateSidebarToPosition(window: any, targetX: number, targetY: number) {
  if (!window) return
  
  const wasMovable = window.isMovable()
  if (!wasMovable) {
    window.setMovable(true)
  }
  
  const startPos = window.getPosition()
  const startX = startPos[0]
  const startY = startPos[1]
  const deltaX = targetX - startX
  const deltaY = targetY - startY
  
  if (Math.abs(deltaX) < 5 && Math.abs(deltaY) < 5) {
    window.setPosition(targetX, targetY)
    if (!wasMovable) {
      window.setMovable(false)
    }
    return
  }
  
  const steps = 15
  const stepSizeX = deltaX / steps
  const stepSizeY = deltaY / steps
  let currentStep = 0
  
  const animate = () => {
    if (currentStep >= steps || !window) return
    
    currentStep++
    const newX = Math.round(startX + (stepSizeX * currentStep))
    const newY = Math.round(startY + (stepSizeY * currentStep))
    
    try {
      window.setPosition(newX, newY)
    } catch (error) {
      if (!wasMovable) {
        window.setMovable(false)
      }
      return
    }
    
    if (currentStep < steps) {
      setTimeout(() => animate(), 20)
    } else {
      if (!wasMovable) {
        window.setMovable(false)
      }
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

function startSidebarHoverTimer() {
  setInterval(() => {
    const { screen } = require('electron')
    const cursor = screen.getCursorScreenPoint()
    const primaryDisplay = screen.getPrimaryDisplay()
    const { width: screenWidth, height: screenHeight } = primaryDisplay.bounds
    
    const isInLeftHoverZone = cursor.x <= sidebarHoverZoneWidth
    
    const isInRightHoverZone = cursor.x >= screenWidth - sidebarHoverZoneWidth
    
    const isOverVisualizer = visualizerWindow && visualizerWindow.isVisible() && 
      cursor.x >= 0 && cursor.x <= 400 && 
      cursor.y >= Math.floor((screenHeight - 600) / 2) && 
      cursor.y <= Math.floor((screenHeight - 600) / 2) + 600
    
    const isOverConfig = configWindow && configWindow.isVisible() && 
      cursor.x >= screenWidth - 250 && cursor.x <= screenWidth && 
      cursor.y >= Math.floor((screenHeight - 750) / 2) && 
      cursor.y <= Math.floor((screenHeight - 750) / 2) + 750
    
    const isOverAnySidebar = isOverVisualizer || isOverConfig
    
    if (isInLeftHoverZone || isOverVisualizer) {
      if (!lastSidebarHoverState) {
        lastSidebarHoverState = true
        if (sidebarHideTimeout) {
          clearTimeout(sidebarHideTimeout)
          sidebarHideTimeout = null
        }
        
        if (configWindow && configWindow.isVisible()) {
          const primaryDisplay = screen.getPrimaryDisplay()
          const { width: screenWidth, height: screenHeight } = primaryDisplay.bounds
          animateSidebarToPosition(configWindow, screenWidth, Math.floor((screenHeight - 750) / 2))
          setTimeout(() => {
            if (configWindow) configWindow.hide()
          }, 300) // Wait for animation to complete
        }
        
        if (!visualizerWindow || !visualizerWindow.isVisible()) {
          if (!sidebarShowTimeout) {
            sidebarShowTimeout = setTimeout(() => {
              if (visualizerWindow) {
                const primaryDisplay = screen.getPrimaryDisplay()
                const { height: screenHeight } = primaryDisplay.bounds
                visualizerWindow.setPosition(-400, Math.floor((screenHeight - 600) / 2))
                visualizerWindow.show()
                animateSidebarToPosition(visualizerWindow, 0, Math.floor((screenHeight - 600) / 2))
                return
              }
              
              const primaryDisplay = screen.getPrimaryDisplay()
              const { height: screenHeight } = primaryDisplay.bounds
              
              visualizerWindow = new BrowserWindow({
                width: 400,
                height: 600,
                x: -400,
                y: Math.floor((screenHeight - 600) / 2),
                frame: false,
                transparent: true,
                alwaysOnTop: true,
                skipTaskbar: true,
                resizable: false,
                movable: false,
                show: false,
                focusable: false,
                webPreferences: {
                  nodeIntegration: false,
                  contextIsolation: true,
                  preload: join(__dirname, 'preload.js')
                },
                backgroundColor: 'rgba(0,0,0,0)'
              })
              
              visualizerWindow.show()
              
              animateSidebarToPosition(visualizerWindow, 0, Math.floor((screenHeight - 600) / 2))
              
              const htmlPath = join(process.cwd(), 'src/renderer/visualizer.html')
              visualizerWindow.loadFile(htmlPath).then(() => {
                visualizerWindow.reload()
              }).catch((error: any) => {
                console.error('Error loading visualizer HTML:', error)
              })
              
              sidebarShowTimeout = null
            }, sidebarHoverCooldown)
          }
        }
      } else if (isOverVisualizer && sidebarHideTimeout) {
        clearTimeout(sidebarHideTimeout)
        sidebarHideTimeout = null
      }
    }
    
    if (isInRightHoverZone || isOverConfig) {
      if (!lastSidebarHoverState) {
        lastSidebarHoverState = true
        if (sidebarHideTimeout) {
          clearTimeout(sidebarHideTimeout)
          sidebarHideTimeout = null
        }
        
        if (visualizerWindow && visualizerWindow.isVisible()) {
          const primaryDisplay = screen.getPrimaryDisplay()
          const { height: screenHeight } = primaryDisplay.bounds
          animateSidebarToPosition(visualizerWindow, -400, Math.floor((screenHeight - 600) / 2))
          setTimeout(() => {
            if (visualizerWindow) visualizerWindow.hide()
          }, 300) // Wait for animation to complete
        }
        
        if (!configWindow || !configWindow.isVisible()) {
          if (!sidebarShowTimeout) {
            sidebarShowTimeout = setTimeout(() => {
              if (configWindow) {
                const primaryDisplay = screen.getPrimaryDisplay()
                const { width: screenWidth, height: screenHeight } = primaryDisplay.bounds
                configWindow.setPosition(screenWidth, Math.floor((screenHeight - 750) / 2))
                configWindow.show()
                animateSidebarToPosition(configWindow, screenWidth - 250, Math.floor((screenHeight - 750) / 2))
                return
              }
              
              const primaryDisplay = screen.getPrimaryDisplay()
              const { width: screenWidth, height: screenHeight } = primaryDisplay.bounds
              
              configWindow = new BrowserWindow({
                width: 250,
                height: 750,
                x: screenWidth,
                y: Math.floor((screenHeight - 750) / 2),
                frame: false,
                transparent: true,
                alwaysOnTop: true,
                skipTaskbar: true,
                resizable: false,
                movable: false,
                show: false,
                focusable: false,
                webPreferences: {
                  nodeIntegration: false,
                  contextIsolation: true,
                  preload: join(__dirname, 'preload.js')
                },
                backgroundColor: 'rgba(0,0,0,0)'
              })
              
              configWindow.show()
              
              setTimeout(() => {
                animateSidebarToPosition(configWindow, screenWidth - 250, Math.floor((screenHeight - 750) / 2))
              }, 50)
              
              const htmlPath = join(process.cwd(), 'src/renderer/config-popup.html')
              configWindow.loadFile(htmlPath).then(() => {
                configWindow.reload()
              }).catch((error: any) => {
                console.error('Error loading config HTML:', error)
              })
              
              sidebarShowTimeout = null
            }, sidebarHoverCooldown)
          }
        }
      } else if (isOverConfig && sidebarHideTimeout) {
        clearTimeout(sidebarHideTimeout)
        sidebarHideTimeout = null
      }
    }
    
    if (!isInLeftHoverZone && !isInRightHoverZone && !isOverAnySidebar) {
      if (lastSidebarHoverState) {
        lastSidebarHoverState = false
        if (sidebarShowTimeout) {
          clearTimeout(sidebarShowTimeout)
          sidebarShowTimeout = null
        }
        
        if ((visualizerWindow && visualizerWindow.isVisible()) || 
            (configWindow && configWindow.isVisible())) {
                if (!sidebarHideTimeout) {
                  sidebarHideTimeout = setTimeout(() => {
                    if (visualizerWindow && visualizerWindow.isVisible()) {
                      const primaryDisplay = screen.getPrimaryDisplay()
                      const { height: screenHeight } = primaryDisplay.bounds
                      animateSidebarToPosition(visualizerWindow, -400, Math.floor((screenHeight - 600) / 2))
                      setTimeout(() => {
                        if (visualizerWindow) visualizerWindow.hide()
                      }, 300)
                    }
                    if (configWindow && configWindow.isVisible()) {
                      const primaryDisplay = screen.getPrimaryDisplay()
                      const { width: screenWidth, height: screenHeight } = primaryDisplay.bounds
                      animateSidebarToPosition(configWindow, screenWidth, Math.floor((screenHeight - 750) / 2))
                      setTimeout(() => {
                        if (configWindow) configWindow.hide()
                      }, 300)
                    }
                    sidebarHideTimeout = null
                  }, sidebarHideCooldown)
                }
        }
      }
    }
  }, 100)
}

app.disableHardwareAcceleration()

app.whenReady().then(() => {
  createWindow()
  startBackend()
  startSidebarHoverTimer()
  setupVoiceServer()

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
  if (visualizerWindow) {
    visualizerWindow.destroy()
    visualizerWindow = null
  }
  
  if (configWindow) {
    configWindow.destroy()
    configWindow = null
  }
  
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
    width: 400,
    height: 600,
    x: -400,
    y: Math.floor((screenHeight - 600) / 2),
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    movable: false,
    show: false,
    focusable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    backgroundColor: 'rgba(0,0,0,0)'
  })
  
  visualizerWindow.show()
  console.log('Visualizer window shown immediately')
  
  animateSidebarToPosition(visualizerWindow, 0, Math.floor((screenHeight - 600) / 2))
  
  const htmlPath = join(process.cwd(), 'src/renderer/visualizer.html')
  console.log('Loading HTML from:', htmlPath)
  
  visualizerWindow.loadFile(htmlPath).then(() => {
    console.log('HTML loaded successfully')
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
    if (mainWindow) {
      mainWindow.webContents.send('visualizer-closed')
    }
  }
})

ipcMain.handle('show-config', () => {
  console.log('show-config IPC handler called')
  if (configWindow) {
    console.log('Config window already exists, showing it')
    configWindow.show()
    return
  }
  
  console.log('Creating new config window')
  const primaryDisplay = screen.getPrimaryDisplay()
  const { width: screenWidth, height: screenHeight } = primaryDisplay.bounds
  
  configWindow = new BrowserWindow({
    width: 500,
    height: 800,
    x: screenWidth,
    y: Math.floor((screenHeight - 600) / 2),
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    movable: false,
    show: false,
    focusable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    backgroundColor: 'rgba(0,0,0,0)'
  })
  
  configWindow.show()
  console.log('Config window shown immediately')
  
  animateSidebarToPosition(configWindow, screenWidth - 250, Math.floor((screenHeight - 600) / 2))
  
  const htmlPath = join(process.cwd(), 'src/renderer/config-popup.html')
  console.log('Loading config HTML from:', htmlPath)
  
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
    if (mainWindow) {
      mainWindow.webContents.send('config-closed')
    }
  }
})

ipcMain.handle('get-config', async () => {
  console.log('get-config IPC handler called')
  try {
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

// Voice data IPC handlers
ipcMain.handle('send-voice-data', async (_, voiceData: any) => {
  console.log('Voice data received:', voiceData)
  
  // Send voice data to the visualizer window if it exists
  if (visualizerWindow && !visualizerWindow.isDestroyed()) {
    visualizerWindow.webContents.send('voice-data', voiceData)
  }
  
  // Also send to main window for potential logging
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('voice-data', voiceData)
  }
  
  return { success: true }
})

ipcMain.handle('send-voice-status', async (_, status: any) => {
  console.log('Voice status received:', status)
  
  // Send voice status to the visualizer window if it exists
  if (visualizerWindow && !visualizerWindow.isDestroyed()) {
    visualizerWindow.webContents.send('voice-status', status)
  }
  
  // Also send to main window for potential logging
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('voice-status', status)
  }
  
  return { success: true }
})
