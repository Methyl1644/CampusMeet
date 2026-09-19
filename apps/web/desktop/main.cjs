const path = require('node:path')
const { app, BrowserWindow, shell } = require('electron')
const { startDesktopServer } = require('./server.cjs')

let mainWindow
let desktopServer

async function createWindow() {
  const distDir = path.join(__dirname, 'dist')
  const local = await startDesktopServer(distDir)
  desktopServer = local.server

  mainWindow = new BrowserWindow({
    title: '梧桐遇 CampusMeet',
    width: 1440,
    height: 920,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: '#f7f8f9',
    autoHideMenuBar: true,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(local.url)) {
      event.preventDefault()
      shell.openExternal(url)
    }
  })

  await mainWindow.loadURL(local.url)
}

const hasLock = app.requestSingleInstanceLock()
if (!hasLock) {
  app.quit()
} else {
  app.setAppUserModelId('cn.campusmeet.desktop')
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })
  app.whenReady().then(createWindow)
}

app.on('window-all-closed', () => {
  if (desktopServer) desktopServer.close()
  if (process.platform !== 'darwin') app.quit()
})
