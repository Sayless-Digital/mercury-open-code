const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs').promises;
const { spawn } = require('child_process');
const pty = require('node-pty');
const chokidar = require('chokidar');

const OPENCODE_URL = 'http://127.0.0.1:4096';
const WHISPER_URL = 'http://127.0.0.1:8001';
const chatStreams = new Map();

// Safe console wrapper to prevent EPIPE errors
const safeConsole = {
  log: (...args) => {
    try {
      console.log(...args);
    } catch (err) {
      // Silently ignore EPIPE errors
    }
  },
  error: (...args) => {
    try {
      console.error(...args);
    } catch (err) {
      // Silently ignore EPIPE errors
    }
  }
};

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  if (error.code === 'EPIPE' || error.errno === 'EPIPE') {
    // Ignore EPIPE errors (broken pipe)
    return;
  }
  safeConsole.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  safeConsole.error('Unhandled rejection at:', promise, 'reason:', reason);
});

const getFetchImpl = () => {
  if (typeof fetch === 'function') {
    return fetch;
  }
  return require('node-fetch');
};

async function backendRequest(endpoint, options = {}) {
  const fetchImpl = getFetchImpl();
  const requestOptions = {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  };

  if (options.body !== undefined) {
    requestOptions.body =
      typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
  }

  const response = await fetchImpl(`${OPENCODE_URL}${endpoint}`, requestOptions);
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail || data.error || 'Backend request failed');
    error.response = data;
    throw error;
  }
  return data;
}

function pushChatStreamChunk(streamId, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('chat-stream-chunk', streamId, payload);
  }
}

function stopChatStream(streamId) {
  const controller = chatStreams.get(streamId);
  if (controller) {
    controller.abort();
    chatStreams.delete(streamId);
  }
}

function startChatStream(streamId, payload) {
  const fetchImpl = getFetchImpl();
  const controller = new AbortController();
  chatStreams.set(streamId, controller);

  fetchImpl(`${OPENCODE_URL}/session/${payload.sessionId}/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(payload),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const segments = buffer.split('\n\n');
        buffer = segments.pop() || '';

        for (const segment of segments) {
          const dataLines = segment
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.replace(/^data:\s*/, ''));

          if (!dataLines.length) continue;

          const dataStr = dataLines.join('\n');
          if (!dataStr.trim()) continue;

          try {
            const payloadObj = JSON.parse(dataStr);
            pushChatStreamChunk(streamId, payloadObj);
          } catch (err) {
            console.error('Failed to parse SSE chunk', err);
          }
        }
      }
      pushChatStreamChunk(streamId, { type: 'done' });
    })
    .catch((error) => {
      if (controller.signal.aborted) {
        pushChatStreamChunk(streamId, { type: 'cancelled' });
      } else {
        pushChatStreamChunk(streamId, { type: 'error', message: error.message });
      }
    })
    .finally(() => {
      chatStreams.delete(streamId);
    });
}

let mainWindow;
let opencodeProcess = null;
let whisperProcess = null;
let db;
let fileWatcher = null;

// Try to load database module (may fail if native module isn't rebuilt)
let ProjectDatabase;
try {
  ProjectDatabase = require('./database');
} catch (error) {
  console.error('Warning: Could not load database module:', error.message);
  console.error('  Project management features will be disabled.');
  console.error('  Run: npx electron-rebuild -f -w better-sqlite3');
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#1e1e1e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: true, // Keep security enabled but allow localhost connections
      allowRunningInsecureContent: false, // Keep secure
      // Enable experimental features if needed for EventSource/SSE
      experimentalFeatures: false, // EventSource works without this
    },
    show: false, // Don't show until ready
    skipTaskbar: false, // Ensure window appears in taskbar
  });

  // Handle media access permissions
  mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowedPermissions = ['media', 'mediaKeySystem'];
    if (allowedPermissions.includes(permission)) {
      callback(true); // Grant permission
    } else {
      callback(false); // Deny permission
    }
  });

  // Handle permission check requests
  mainWindow.webContents.session.setPermissionCheckHandler((webContents, permission, requestingOrigin) => {
    const allowedPermissions = ['media', 'mediaKeySystem'];
    return allowedPermissions.includes(permission);
  });

  // Handle media access permissions
  mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowedPermissions = ['media', 'mediaKeySystem'];
    if (allowedPermissions.includes(permission)) {
      callback(true); // Grant permission
    } else {
      callback(false); // Deny permission
    }
  });

  // Handle permission check requests
  mainWindow.webContents.session.setPermissionCheckHandler((webContents, permission, requestingOrigin) => {
    const allowedPermissions = ['media', 'mediaKeySystem'];
    return allowedPermissions.includes(permission);
  });

  // Load the app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    // Uncomment to open DevTools in development
    // mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Also show window if it fails to load after a timeout
  const showTimeout = setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      console.log('Showing window after timeout...');
      mainWindow.show();
      mainWindow.focus();
    }
  }, 5000); // Show after 5 seconds even if page hasn't loaded

  mainWindow.once('did-finish-load', () => {
    clearTimeout(showTimeout);
  });

  // Handle page load errors
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load page:', errorCode, errorDescription);
    // Still show window even on error
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Window control IPC handlers
  ipcMain.handle('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.handle('window-maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
        return false;
      } else {
        mainWindow.maximize();
        return true;
      }
    }
    return false;
  });

  ipcMain.handle('window-close', () => {
    if (mainWindow) mainWindow.close();
  });

  ipcMain.handle('window-is-maximized', () => {
    return mainWindow ? mainWindow.isMaximized() : false;
  });


  // Database IPC handlers (with null checks)
  ipcMain.handle('db-get-projects', () => {
    return db ? db.getProjects() : [];
  });

  ipcMain.handle('db-get-project', (event, projectId) => {
    return db ? db.getProject(projectId) : null;
  });

  ipcMain.handle('db-add-project', (event, name, projectPath, description) => {
    if (!db) {
      return { success: false, error: 'Database not initialized' };
    }
    try {
      const result = db.addProject(name, projectPath, description);
      return { success: true, id: result.lastInsertRowid };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('db-open-project', (event, projectId) => {
    return db ? db.openProject(projectId) : null;
  });

  ipcMain.handle('db-delete-project', (event, projectId) => {
    if (!db) {
      return { success: false, error: 'Database not initialized' };
    }
    try {
      db.deleteProject(projectId);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('db-add-recent-file', (event, projectId, filePath) => {
    return db ? db.addRecentFile(projectId, filePath) : null;
  });

  // File system IPC handlers
  ipcMain.handle('fs-read-dir', async (event, dirPath) => {
    const fs = require('fs').promises;
    try {
      if (!dirPath) {
        console.error('fs-read-dir: No directory path provided');
        throw new Error('No directory path provided');
      }

      // Validate that the path exists and is a directory
      const stats = await fs.stat(dirPath).catch(() => null);
      if (!stats) {
        console.error(`fs-read-dir: Path does not exist: ${dirPath}`);
        throw new Error(`Directory does not exist: ${dirPath}`);
      }
      if (!stats.isDirectory()) {
        console.error(`fs-read-dir: Path is not a directory: ${dirPath}`);
        throw new Error(`Path is not a directory: ${dirPath}`);
      }

      console.log(`fs-read-dir: Reading directory: ${dirPath}`);
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      
      // Filter out hidden files/directories (starting with .) and common system dirs
      const filteredEntries = entries.filter(entry => {
        // Skip hidden files/directories
        if (entry.name.startsWith('.')) {
          return false;
        }
        return true;
      });
      
      const result = filteredEntries.map(entry => ({
        name: entry.name,
        path: path.join(dirPath, entry.name),
        isDirectory: entry.isDirectory(),
        isFile: entry.isFile(),
      }));
      
      safeConsole.log(`fs-read-dir: Returning ${result.length} entries from ${dirPath}`);
      return result;
    } catch (error) {
      safeConsole.error(`fs-read-dir: Error reading directory ${dirPath}:`, error);
      throw new Error(`Failed to read directory: ${error.message}`);
    }
  });

  ipcMain.handle('fs-read-file', async (event, filePath) => {
    const fs = require('fs').promises;
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      return content;
    } catch (error) {
      throw new Error(`Failed to read file: ${error.message}`);
    }
  });

  ipcMain.handle('fs-write-file', async (event, filePath, content) => {
    const fs = require('fs').promises;
    try {
      await fs.writeFile(filePath, content, 'utf-8');
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('fs-delete-file', async (event, filePath) => {
    const fs = require('fs').promises;
    const path = require('path');
    try {
      const stats = await fs.stat(filePath);
      if (stats.isDirectory()) {
        await fs.rmdir(filePath, { recursive: true });
      } else {
        await fs.unlink(filePath);
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('fs-rename-file', async (event, oldPath, newPath) => {
    const fs = require('fs').promises;
    try {
      await fs.rename(oldPath, newPath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('fs-copy-file', async (event, sourcePath, destPath) => {
    const fs = require('fs').promises;
    const path = require('path');
    
    async function copyRecursive(src, dest) {
      const stats = await fs.stat(src);
      
      if (stats.isDirectory()) {
        // Create destination directory
        await fs.mkdir(dest, { recursive: true });
        
        // Read all items in source directory
        const entries = await fs.readdir(src);
        
        // Copy each item recursively
        for (const entry of entries) {
          const srcPath = path.join(src, entry);
          const destPath = path.join(dest, entry);
          await copyRecursive(srcPath, destPath);
        }
      } else {
        // Copy file - ensure destination directory exists
        const destDir = path.dirname(dest);
        await fs.mkdir(destDir, { recursive: true });
        await fs.copyFile(src, dest);
      }
    }
    
    try {
      await copyRecursive(sourcePath, destPath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Dialog handlers
  ipcMain.handle('dialog-open-folder', async () => {
    if (mainWindow) {
      mainWindow.focus();
    }
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
      title: 'Select Project Folder',
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
      return { path: result.filePaths[0] };
    }
    return null;
  });

  ipcMain.handle('dialog-open-file', async () => {
    if (mainWindow) {
      mainWindow.focus();
    }
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      title: 'Open File',
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
      return { path: result.filePaths[0] };
    }
    return null;
  });

  ipcMain.handle('open-path-in-explorer', async (event, pathToOpen) => {
    try {
      const fs = require('fs');
      const path = require('path');
      
      // Verify the path exists
      if (!fs.existsSync(pathToOpen)) {
        return { success: false, error: 'Path does not exist' };
      }
      
      // Normalize the path
      const normalizedPath = path.resolve(pathToOpen);
      
      // Use openExternal with file:// URL for better cross-platform support
      // On Windows, this ensures the explorer opens in the foreground
      const fileUrl = process.platform === 'win32' 
        ? `file:///${normalizedPath.replace(/\\/g, '/')}`
        : `file://${normalizedPath}`;
      
      await shell.openExternal(fileUrl);
      return { success: true };
    } catch (error) {
      console.error('Error opening path in explorer:', error);
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('dialog-save-file', async (event, options = {}) => {
    if (mainWindow) {
      mainWindow.focus();
    }
    const result = await dialog.showSaveDialog(mainWindow, {
      title: options.title || 'Save File',
      defaultPath: options.defaultPath,
      filters: options.filters || [{ name: 'All Files', extensions: ['*'] }],
    });
    
    if (!result.canceled && result.filePath) {
      return { path: result.filePath };
    }
    return null;
  });

  ipcMain.handle('dialog-input', async (event, options = {}) => {
    // Simple input dialog using prompt (we can enhance this later with a custom dialog)
    // For now, return a basic implementation
    return { value: null }; // Placeholder - would need custom dialog implementation
  });

  ipcMain.handle('fs-create-directory', async (event, dirPath) => {
    const fs = require('fs').promises;
    try {
      await fs.mkdir(dirPath, { recursive: true });
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // File system watcher handlers
  function startWatchingProject(projectPath) {
    // Stop existing watcher if any
    if (fileWatcher) {
      console.log('[FileWatcher] Stopping existing watcher');
      fileWatcher.close();
      fileWatcher = null;
    }

    if (!projectPath) {
      console.warn('[FileWatcher] No project path provided, cannot start watcher');
      return;
    }

    console.log(`[FileWatcher] Starting file watcher for: ${projectPath}`);
    
    // Watch the project directory (ignore node_modules, .git, etc.)
    fileWatcher = chokidar.watch(projectPath, {
      ignored: [
        /node_modules/,
        /\.git/,
        /\.vscode/,
        /dist/,
        /build/,
        /__pycache__/,
        /\.pyc$/,
        /\.DS_Store$/,
      ],
      ignoreInitial: true, // Don't fire events for existing files
      persistent: true,
      depth: 99, // Watch all subdirectories
      awaitWriteFinish: {
        stabilityThreshold: 100, // Wait 100ms after file stops changing
        pollInterval: 50,
      },
      usePolling: false, // Use native file system events (faster, but may not work on all systems)
      ignorePermissionErrors: true, // Don't crash on permission errors
    });

    // Send events to renderer when files change
    fileWatcher
      .on('add', (filePath) => {
        console.log(`[FileWatcher] File added: ${filePath}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('file-system-change', {
            type: 'add',
            path: filePath,
          });
        } else {
          console.warn('[FileWatcher] Main window not available, cannot send event');
        }
      })
      .on('change', (filePath) => {
        console.log(`[FileWatcher] File changed: ${filePath}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('file-system-change', {
            type: 'change',
            path: filePath,
          });
        } else {
          console.warn('[FileWatcher] Main window not available, cannot send event');
        }
      })
      .on('unlink', (filePath) => {
        console.log(`[FileWatcher] File deleted: ${filePath}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('file-system-change', {
            type: 'unlink',
            path: filePath,
          });
        } else {
          console.warn('[FileWatcher] Main window not available, cannot send unlink event');
        }
      })
      .on('addDir', (dirPath) => {
        console.log(`Directory added: ${dirPath}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('file-system-change', {
            type: 'addDir',
            path: dirPath,
          });
        }
      })
      .on('unlinkDir', (dirPath) => {
        console.log(`[FileWatcher] Directory deleted: ${dirPath}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('file-system-change', {
            type: 'unlinkDir',
            path: dirPath,
          });
        } else {
          console.warn('[FileWatcher] Main window not available, cannot send unlinkDir event');
        }
      })
      .on('error', (error) => {
        console.error('File watcher error:', error);
      })
      .on('ready', () => {
        console.log(`[FileWatcher] Ready and watching: ${projectPath}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('file-system-change', {
            type: 'ready',
            path: projectPath,
          });
        }
      });
  }

  function stopWatchingProject() {
    if (fileWatcher) {
      console.log('Stopping file watcher');
      fileWatcher.close();
      fileWatcher = null;
    }
  }

  ipcMain.handle('fs-watch-project', (event, projectPath) => {
    console.log(`[IPC] fs-watch-project called with path: ${projectPath}`);
    startWatchingProject(projectPath);
    return { success: true };
  });

  ipcMain.handle('fs-unwatch-project', () => {
    stopWatchingProject();
    return { success: true };
  });

  ipcMain.handle('fs-join-path', async (event, ...pathSegments) => {
    return path.join(...pathSegments);
  });

  // Mercury Coder global config operations
  ipcMain.handle('get-mercury-config-dir', async () => {
    const configDir = path.join(os.homedir(), '.config', 'mercury-coder');
    // Ensure directory exists
    await fs.mkdir(configDir, { recursive: true });
    return configDir;
  });

  ipcMain.handle('write-mercury-config', async (event, configData) => {
    try {
      const configDir = path.join(os.homedir(), '.config', 'mercury-coder');
      await fs.mkdir(configDir, { recursive: true });
      const configPath = path.join(configDir, 'opencode.json');
      await fs.writeFile(configPath, JSON.stringify(configData, null, 2));
      return { success: true, path: configPath };
    } catch (error) {
      safeConsole.error('[Electron] Error writing Mercury config:', error);
      return { success: false, error: error.message };
    }
  });

  // Python backend communication
  ipcMain.handle('backend-send-message', async (event, message, context) => {
    try {
      return await backendRequest('/api/chat', {
        method: 'POST',
        body: { message, context },
      });
    } catch (error) {
      return {
        response: `Error connecting to backend: ${error.message}. Make sure the Python backend is running on port 8000.`,
        success: false,
        error: error.message,
      };
    }
  });

  ipcMain.handle('chat-stream-start', async (event, payload) => {
    try {
      const streamId = Date.now().toString();
      startChatStream(streamId, payload);
      return { streamId, success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('chat-stream-stop', async (event, streamId) => {
    stopChatStream(streamId);
    return { success: true };
  });


  // Terminal PTY management
  let terminalPty = null;
  let terminalPtyId = null;

  // Create a new PTY terminal
  ipcMain.handle('terminal-create', async (event, cwd) => {
    try {
      // Kill existing PTY if any
      if (terminalPty) {
        terminalPty.kill();
      }

      const shell = process.platform === 'win32' ? 'cmd.exe' : process.env.SHELL || '/bin/bash';
      const cwdPath = cwd || process.cwd();
      
      // Set up environment with color support
      const env = { ...process.env };
      env.FORCE_COLOR = '1';
      env.CLI_COLORS = '1';
      env.TERM = 'xterm-256color';
      env.COLORTERM = 'truecolor';
      // Prevent shell from outputting cursor control sequences as text
      env.DEBIAN_FRONTEND = 'noninteractive';
      // Disable any shell integration that might output escape sequences
      env.BASH_SILENCE_DEPRECATION_WARNING = '1';

      // Get initial terminal size from main window if available
      let cols = 80;
      let rows = 24;
      if (mainWindow && !mainWindow.isDestroyed()) {
        const size = mainWindow.getContentSize();
        // Estimate cols/rows based on window size (rough estimate)
        cols = Math.max(80, Math.floor(size[0] / 8));
        rows = Math.max(24, Math.floor(size[1] / 16));
      }

      terminalPty = pty.spawn(shell, [], {
        name: 'xterm-256color',
        cols: cols,
        rows: rows,
        cwd: cwdPath,
        env: env,
        encoding: 'utf8',
      });

      terminalPtyId = Date.now().toString();

      // Handle PTY output
      // Note: xterm.js handles ANSI escape sequences natively, so we don't filter them
      // If escape sequences appear as text, it means xterm.js isn't ready to process them
      terminalPty.onData((data) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          // Send data directly to xterm.js - it will handle escape sequences properly
          mainWindow.webContents.send('terminal-data', terminalPtyId, data);
        }
      });

      // Handle PTY exit
      terminalPty.onExit((code, signal) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('terminal-exit', terminalPtyId, code, signal);
        }
        terminalPty = null;
        terminalPtyId = null;
      });

      return { success: true, ptyId: terminalPtyId };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Write data to PTY
  ipcMain.handle('terminal-write', async (event, ptyId, data) => {
    if (terminalPty && terminalPtyId === ptyId) {
      terminalPty.write(data);
      return { success: true };
    }
    return { success: false, error: 'PTY not found' };
  });

  // Resize PTY
  ipcMain.handle('terminal-resize', async (event, ptyId, cols, rows) => {
    if (terminalPty && terminalPtyId === ptyId) {
      terminalPty.resize(cols, rows);
      return { success: true };
    }
    return { success: false, error: 'PTY not found' };
  });

  // Kill PTY
  ipcMain.handle('terminal-kill', async (event, ptyId) => {
    if (terminalPty && terminalPtyId === ptyId) {
      terminalPty.kill();
      terminalPty = null;
      terminalPtyId = null;
      return { success: true };
    }
    return { success: false, error: 'PTY not found' };
  });

  // Execute command synchronously and return result
  ipcMain.handle('execute-command', async (event, options) => {
    const { command, args = [], cwd } = options;
    
    if (!command) {
      return { success: false, error: 'Command is required' };
    }

    const workingDir = cwd || process.cwd();
    const envVars = { ...process.env };

    return new Promise((resolve) => {
      const childProcess = spawn(command, args, {
        cwd: workingDir,
        shell: false,
        env: envVars
      });

      let stdout = '';
      let stderr = '';

      childProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      childProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      childProcess.on('close', (code) => {
        resolve({
          success: code === 0,
          stdout: stdout.trim(),
          stderr: stderr.trim(),
          returnCode: code
        });
      });

      childProcess.on('error', (error) => {
        resolve({
          success: false,
          error: error.message,
          stdout: stdout.trim(),
          stderr: stderr.trim()
        });
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (!childProcess.killed) {
          childProcess.kill();
          resolve({
            success: false,
            error: 'Command timed out',
            stdout: stdout.trim(),
            stderr: stderr.trim()
          });
        }
      }, 30000);
    });
  });
}

// Check if OpenCode server is running
async function isOpencodeRunning() {
  try {
    const fetchImpl = getFetchImpl();
    const response = await fetchImpl('http://127.0.0.1:4096/config', { 
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return response.ok;
  } catch {
    return false;
  }
}

// Check if Whisper service is running
async function isWhisperRunning() {
  try {
    const fetchImpl = getFetchImpl();
    const response = await fetchImpl('http://127.0.0.1:8001/health', { 
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return response.ok;
  } catch {
    return false;
  }
}

// Start OpenCode server
async function startOpencodeServer() {
  if (opencodeProcess) {
    safeConsole.log('[OpenCode] Process already exists');
    return;
  }

  // Check if already running
  if (await isOpencodeRunning()) {
    safeConsole.log('[OpenCode] Server already running on port 4096');
    return;
  }

  safeConsole.log('[OpenCode] Starting local backend server on port 4096...');
  
  try {
    // Use local opencode-backend instead of global installation
    const opencodeBackendPath = path.join(__dirname, '..', '..', 'opencode-backend');
    const bunPath = process.env.BUN_PATH || 'bun';
    
    // Set Mercury Coder global config path
    const mercuryConfigDir = path.join(os.homedir(), '.config', 'mercury-coder');
    await fs.mkdir(mercuryConfigDir, { recursive: true });
    const mercuryConfigPath = path.join(mercuryConfigDir, 'opencode.json');
    
    safeConsole.log('[OpenCode] Backend path:', opencodeBackendPath);
    safeConsole.log('[OpenCode] Mercury config path:', mercuryConfigPath);
    
    opencodeProcess = spawn(bunPath, [
      'run',
      '--cwd', path.join(opencodeBackendPath, 'packages/opencode'),
      '--conditions=browser',
      'src/index.ts',
      'serve',
      '--port', '4096',
      '--hostname', '127.0.0.1',
      '--print-logs',
      '--log-level', 'DEBUG'
    ], {
      stdio: 'ignore', // Changed from 'inherit' to prevent EPIPE
      env: { 
        ...process.env,
        NODE_ENV: 'development',
        OPENCODE_CONFIG: mercuryConfigPath
      },
      cwd: opencodeBackendPath
    });

    opencodeProcess.on('error', (error) => {
      safeConsole.error('[OpenCode] Failed to start:', error);
      dialog.showErrorBox(
        'OpenCode Server Error',
        `Failed to start local OpenCode backend: ${error.message}\n\nPlease ensure bun is installed and opencode-backend exists.`
      );
      opencodeProcess = null;
    });

    opencodeProcess.on('exit', (code) => {
      safeConsole.log(`[OpenCode] Server exited with code ${code}`);
      opencodeProcess = null;
    });

    // Wait for server to be ready
    let retries = 0;
    const maxRetries = 30; // 30 seconds max wait
    while (retries < maxRetries) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      if (await isOpencodeRunning()) {
        safeConsole.log('[OpenCode] Local backend server ready!');
        return;
      }
      retries++;
    }

    if (retries >= maxRetries) {
      safeConsole.error('[OpenCode] Server did not start in time');
      dialog.showErrorBox(
        'OpenCode Server Timeout',
        'OpenCode server did not start within 30 seconds. Please check the console for errors.'
      );
    }
  } catch (error) {
    safeConsole.error('[OpenCode] Startup error:', error);
  }
}

// Start Whisper service
async function startWhisperService() {
  if (whisperProcess) {
    safeConsole.log('[Whisper] Process already exists');
    return;
  }

  // Check if already running
  if (await isWhisperRunning()) {
    safeConsole.log('[Whisper] Service already running on port 8001');
    return;
  }

  safeConsole.log('[Whisper] Starting service on port 8001...');

  const whisperPath = path.join(__dirname, '../backend-whisper');
  const isDev = process.env.NODE_ENV === 'development';

  try {
    whisperProcess = spawn('python3', [
      '-m', 'uvicorn',
      'main:app',
      '--host', '127.0.0.1',
      '--port', '8001',
      ...(isDev ? ['--reload'] : [])
    ], {
      cwd: whisperPath,
      stdio: 'ignore', // Changed from 'inherit' to prevent EPIPE
      env: { ...process.env }
    });

    whisperProcess.on('error', (error) => {
      safeConsole.error('[Whisper] Failed to start:', error);
      dialog.showMessageBox({
        type: 'warning',
        title: 'Whisper Service Warning',
        message: 'Failed to start Whisper transcription service. Voice recording will not work.',
        detail: `Error: ${error.message}\n\nPlease ensure Python dependencies are installed:\ncd backend-whisper && pip install -r requirements.txt`
      });
      whisperProcess = null;
    });

    whisperProcess.on('exit', (code) => {
      safeConsole.log(`[Whisper] Service exited with code ${code}`);
      whisperProcess = null;
    });

    // Wait for service to be ready
    let retries = 0;
    while (retries < 10) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      if (await isWhisperRunning()) {
        safeConsole.log('[Whisper] Service ready!');
        return;
      }
      retries++;
    }

    if (retries >= 10) {
      safeConsole.error('[Whisper] Service did not start in time (voice recording may not work)');
    }
  } catch (error) {
    safeConsole.error('[Whisper] Startup error:', error);
  }
}

// Initialize all backend services
async function initializeServices() {
  safeConsole.log('[Services] Initializing backend services...');
  
  // Start OpenCode server (critical)
  await startOpencodeServer();
  
  // Start Whisper service (optional, non-blocking)
  startWhisperService().catch(err => {
    safeConsole.error('[Whisper] Service startup failed (non-critical):', err);
  });
  
  safeConsole.log('[Services] Backend services initialized');
}

app.whenReady().then(async () => {
  // Initialize database (with error handling)
  if (ProjectDatabase) {
    try {
      db = new ProjectDatabase();
      console.log('✓ Database initialized');
    } catch (error) {
      console.error('✗ Failed to initialize database:', error.message);
      console.error('  App will continue but project management features may not work');
      // Continue anyway - database is optional for basic functionality
    }
  } else {
    console.log('⚠ Database module not available - project management disabled');
  }
  
  // Initialize backend services (OpenCode + Whisper)
  await initializeServices();
  
  // Create window after services are ready
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // Cleanup services
  if (opencodeProcess) {
    console.log('[OpenCode] Terminating server...');
    opencodeProcess.kill();
  }
  if (whisperProcess) {
    console.log('[Whisper] Terminating service...');
    whisperProcess.kill();
  }
  if (db) {
    db.close();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  // Cleanup services
  if (opencodeProcess) {
    console.log('[OpenCode] Terminating server...');
    opencodeProcess.kill();
  }
  if (whisperProcess) {
    console.log('[Whisper] Terminating service...');
    whisperProcess.kill();
  }
  if (db) {
    db.close();
  }
});

