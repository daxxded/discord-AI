// file: main.js
const { app, BrowserWindow, ipcMain, screen, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const CONFIG_PATH = path.join(__dirname, 'config.json');

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  const windowWidth = 600;
  const windowHeight = 120;

  const x = Math.round((screenWidth - windowWidth) / 2);
  const y = Math.round(screenHeight - windowHeight - 20);

  const win = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x,
    y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('read-config', async () => {
  const raw = fs.readFileSync(CONFIG_PATH, 'utf-8');
  return JSON.parse(raw);
});

ipcMain.handle('perform-action', async (event, action) => {
  if (!action || !action.type) {
    return { ok: false, error: 'Missing action type.' };
  }

  if (action.type === 'open_url') {
    if (action.arguments?.url) {
      await shell.openExternal(action.arguments.url);
      return { ok: true };
    }
    return { ok: false, error: 'Missing url.' };
  }

  if (action.type === 'open_folder') {
    const targetPath = action.arguments?.path;
    if (!targetPath) {
      return { ok: false, error: 'Missing path.' };
    }

    if (process.platform === 'win32') {
      exec(`explorer "${targetPath}"`);
      return { ok: true };
    }

    if (process.platform === 'darwin') {
      exec(`open "${targetPath}"`);
      return { ok: true };
    }

    exec(`xdg-open "${targetPath}"`);
    return { ok: true };
  }

  return { ok: false, error: 'Unknown action type.' };
});
