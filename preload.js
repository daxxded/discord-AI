// file: preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('hyperplexity', {
  readConfig: () => ipcRenderer.invoke('read-config'),
  performAction: (action) => ipcRenderer.invoke('perform-action', action)
});
