// 렌더러에 안전한 IPC 만 노출
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('kiyu', {
  listDrives: () => ipcRenderer.invoke('list-drives'),
  chooseFile: () => ipcRenderer.invoke('choose-file'),
  downloadLatest: () => ipcRenderer.invoke('download-latest'),
  flash: (image, drive, verify) => ipcRenderer.invoke('flash', image, drive, verify),
  onDlProgress: (cb) => ipcRenderer.on('dl-progress', (_e, frac, text) => cb(frac, text)),
  onFlashProgress: (cb) => ipcRenderer.on('flash-progress', (_e, phase, value) => cb(phase, value)),
  onFlashStatus: (cb) => ipcRenderer.on('flash-status', (_e, text) => cb(text)),
});
