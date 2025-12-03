const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  windowMinimize: () => ipcRenderer.invoke('window-minimize'),
  windowMaximize: () => ipcRenderer.invoke('window-maximize'),
  windowClose: () => ipcRenderer.invoke('window-close'),
  windowIsMaximized: () => ipcRenderer.invoke('window-is-maximized'),

  // Database operations
  getProjects: () => ipcRenderer.invoke('db-get-projects'),
  getProject: (id) => ipcRenderer.invoke('db-get-project', id),
  addProject: (name, path, description) => 
    ipcRenderer.invoke('db-add-project', name, path, description),
  openProject: (id) => ipcRenderer.invoke('db-open-project', id),
  deleteProject: (id) => ipcRenderer.invoke('db-delete-project', id),
  addRecentFile: (projectId, filePath) => 
    ipcRenderer.invoke('db-add-recent-file', projectId, filePath),

  // File system operations
  readDirectory: (dirPath) => ipcRenderer.invoke('fs-read-dir', dirPath),
  readFile: (filePath) => ipcRenderer.invoke('fs-read-file', filePath),
  writeFile: (filePath, content) => 
    ipcRenderer.invoke('fs-write-file', filePath, content),
  deleteFile: (filePath) => ipcRenderer.invoke('fs-delete-file', filePath),
  renameFile: (oldPath, newPath) => ipcRenderer.invoke('fs-rename-file', oldPath, newPath),
  copyFile: (sourcePath, destPath) => ipcRenderer.invoke('fs-copy-file', sourcePath, destPath),

  // Backend communication
  sendMessage: (message, context) => 
    ipcRenderer.invoke('backend-send-message', message, context),
  chatStreamStart: (payload) => ipcRenderer.invoke('chat-stream-start', payload),
  chatStreamStop: (streamId) => ipcRenderer.invoke('chat-stream-stop', streamId),
  onChatStreamChunk: (callback) => {
    const handler = (event, streamId, data) => callback(streamId, data);
    ipcRenderer.on('chat-stream-chunk', handler);
    return () => ipcRenderer.removeListener('chat-stream-chunk', handler);
  },
  removeChatStreamListeners: () => {
    ipcRenderer.removeAllListeners('chat-stream-chunk');
  },

  // Dialog operations
  openFolderDialog: () => ipcRenderer.invoke('dialog-open-folder'),
  openFileDialog: () => ipcRenderer.invoke('dialog-open-file'),
  showSaveDialog: (options) => ipcRenderer.invoke('dialog-save-file', options),
  showInputDialog: (options) => ipcRenderer.invoke('dialog-input', options),
  createDirectory: (dirPath) => ipcRenderer.invoke('fs-create-directory', dirPath),
  joinPath: (...paths) => ipcRenderer.invoke('fs-join-path', ...paths),

  // Terminal operations (PTY-based)
  terminalCreate: (cwd) => ipcRenderer.invoke('terminal-create', cwd),
  terminalWrite: (ptyId, data) => ipcRenderer.invoke('terminal-write', ptyId, data),
  terminalResize: (ptyId, cols, rows) => ipcRenderer.invoke('terminal-resize', ptyId, cols, rows),
  terminalKill: (ptyId) => ipcRenderer.invoke('terminal-kill', ptyId),
  
  // Legacy terminal-exec (for backwards compatibility)
  terminalExec: (command, cwd) => ipcRenderer.invoke('terminal-exec', command, cwd),
  
  // Listen for terminal data - returns cleanup function to remove specific listener
  onTerminalData: (callback) => {
    const handler = (event, ptyId, data) => callback(ptyId, data);
    ipcRenderer.on('terminal-data', handler);
    // Return cleanup function to remove this specific listener
    return () => ipcRenderer.removeListener('terminal-data', handler);
  },
  onTerminalExit: (callback) => {
    const handler = (event, ptyId, code, signal) => callback(ptyId, code, signal);
    ipcRenderer.on('terminal-exit', handler);
    // Return cleanup function to remove this specific listener
    return () => ipcRenderer.removeListener('terminal-exit', handler);
  },
  removeTerminalListeners: () => {
    ipcRenderer.removeAllListeners('terminal-data');
    ipcRenderer.removeAllListeners('terminal-exit');
  },

  // File system watcher
  watchProject: (projectPath) => ipcRenderer.invoke('fs-watch-project', projectPath),
  unwatchProject: () => ipcRenderer.invoke('fs-unwatch-project'),
  onFileSystemChange: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('file-system-change', handler);
    return () => ipcRenderer.removeListener('file-system-change', handler);
  },

  // Mercury Coder global config operations
  getMercuryConfigDir: () => ipcRenderer.invoke('get-mercury-config-dir'),
  writeMercuryConfig: (configData) => ipcRenderer.invoke('write-mercury-config', configData),
  
  // Execute command synchronously
  executeCommand: (options) => ipcRenderer.invoke('execute-command', options),
});

