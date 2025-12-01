/**
 * Utility functions for Electron API
 */

/**
 * Check if Electron API is available
 * @returns {boolean}
 */
export function isElectronAvailable() {
  return typeof window !== 'undefined' && window.electronAPI !== undefined;
}

/**
 * Get Electron API with error handling
 * @returns {object|null}
 */
export function getElectronAPI() {
  if (!isElectronAvailable()) {
    console.warn('Electron API is not available. Make sure you are running this app in Electron, not in a browser.');
    return null;
  }
  return window.electronAPI;
}

/**
 * Show error message if Electron is not available
 * @param {string} feature - Feature name for error message
 */
export function requireElectron(feature = 'This feature') {
  if (!isElectronAvailable()) {
    const message = `${feature} requires Electron. Please run the app using 'npm run dev' or start Electron manually.`;
    console.error(message);
    alert(message);
    return false;
  }
  return true;
}








































