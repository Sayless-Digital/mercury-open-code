<template>
  <div class="terminal">
    <div class="terminal-header">
      <div class="header-left">
        <TerminalIcon class="terminal-icon" :size="14" />
        <span class="terminal-title">Terminal</span>
      </div>
      <button class="clear-btn" @click="clear" title="Clear">
        <Eraser :size="14" />
      </button>
    </div>
    <div 
      ref="terminalContainer" 
      class="terminal-container"
      @click="focusTerminal"
      draggable="false"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount, nextTick } from 'vue';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { CanvasAddon } from '@xterm/addon-canvas';
import { Terminal as TerminalIcon, Eraser } from 'lucide-vue-next';
import { useTheme } from '@/composables/useTheme';
import '@xterm/xterm/css/xterm.css';

const props = defineProps({
  cwd: {
    type: String,
    default: null,
  },
});

const terminalContainer = ref(null);
let terminal = null;
let fitAddon = null;
let ptyId = null;
let removeDataListener = null;
let removeExitListener = null;
let resizeObserver = null;
const { isDark: isDarkTheme } = useTheme();

const getTerminalTheme = () => {
  // Get colors from CSS variables directly
  const root = document.documentElement;
  const styles = getComputedStyle(root);
  
  // Check if we're in dark mode
  const isDark = root.classList.contains('dark');
  
  // Use design system colors for terminal text
  const foregroundColor = styles.getPropertyValue('--foreground').trim() || (isDark ? '#e0e0e0' : '#404040');
  const mutedColor = styles.getPropertyValue('--muted-foreground').trim() || (isDark ? '#b4b4b4' : '#646464');
  const bgColor = styles.getPropertyValue('--sidebar').trim() || (isDark ? '#191919' : '#fcfcfc');
  
  // Use theme-appropriate cursor colors that match the app's warm color scheme
  // Dark mode: warm cream/peach (#ffe0c2) - the primary color
  // Light mode: warm brown (#644a40) - the primary color
  const cursorColor = isDark ? '#ffe0c2' : '#644a40';
  
  return {
    background: bgColor,
    foreground: foregroundColor,
    cursor: cursorColor,
    cursorAccent: isDark ? '#191919' : '#ffffff', // Text under cursor should contrast
    selection: `rgba(${styles.getPropertyValue('--primary-rgb').trim() || (isDark ? '255, 224, 194' : '100, 74, 64')}, 0.2)`,
    black: foregroundColor,
    red: styles.getPropertyValue('--destructive').trim() || '#e54d2e',
    green: '#4caf50',
    yellow: '#ff9800',
    blue: mutedColor,
    magenta: '#9c27b0',
    cyan: mutedColor,
    white: bgColor,
    brightBlack: mutedColor,
    brightRed: '#ff6b6b',
    brightGreen: '#81c784',
    brightYellow: '#ffb74d',
    brightBlue: mutedColor,
    brightMagenta: '#ba68c8',
    brightCyan: mutedColor,
    brightWhite: foregroundColor,
  };
};

const initTerminal = () => {
  if (!terminalContainer.value) return;
  
  // Clean up any existing terminal first
  cleanupTerminal();
  
  const theme = getTerminalTheme();
  console.log('[Terminal] Theme cursor color:', theme.cursor);
  
  terminal = new XTerm({
    theme: theme,
    fontSize: 14,
    fontFamily: '"JetBrains Mono", "Fira Code", "Source Code Pro", "Courier New", monospace',
    cursorBlink: true,
    cursorStyle: 'bar', // Vertical bar cursor like modern code editors
    cursorWidth: 2, // Bar width
    cursorInactiveStyle: 'bar', // Show bar cursor even when not focused
    lineHeight: 1.2,
    letterSpacing: 0,
    convertEol: true,
    disableStdin: false,
    allowProposedApi: true,
    scrollback: 1000,
    allowTransparency: false,
    windowsMode: false,
  });

  fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.loadAddon(new WebLinksAddon());

  terminal.open(terminalContainer.value);
  
  // Load the Canvas addon AFTER opening - this forces 2D canvas rendering
  // which is more reliable than WebGL (avoids GPU driver issues)
  terminal.loadAddon(new CanvasAddon());
  console.log('[Terminal] Canvas addon loaded for 2D rendering');
  
  // After opening, ensure cursor is properly configured
  terminal.options.cursorBlink = true;
  terminal.options.cursorStyle = 'bar'; // Vertical bar cursor like modern code editors
  terminal.options.cursorWidth = 2;
  terminal.options.theme = theme;
  
  console.log('[Terminal] Terminal opened, cursor style:', terminal.options.cursorStyle);
  
  // Set up listeners FIRST, before creating PTY
  // This ensures we don't miss any data from the PTY
  if (window.electronAPI) {
    // Store cleanup functions so we can remove listeners later
    removeDataListener = window.electronAPI.onTerminalData((receivedPtyId, data) => {
      // Only process data for our PTY instance
      if (receivedPtyId === ptyId && terminal) {
        // Write data directly - xterm.js will process escape sequences correctly
        terminal.write(data);
      }
    });

    removeExitListener = window.electronAPI.onTerminalExit((receivedPtyId, code, signal) => {
      if (receivedPtyId === ptyId) {
        // PTY exited, can recreate if needed
        ptyId = null;
      }
    });
  }
  
  // Create PTY connection function
  const createPty = async () => {
    if (!window.electronAPI || !window.electronAPI.terminalCreate) {
      terminal.writeln('\x1b[31mError: Terminal API not available\x1b[0m');
      return;
    }

    const result = await window.electronAPI.terminalCreate(props.cwd);
    if (result.success) {
      ptyId = result.ptyId;
    } else {
      terminal.writeln(`\x1b[31mError creating terminal: ${result.error}\x1b[0m`);
    }
  };

  // Handle terminal input - send directly to PTY
  terminal.onData((data) => {
    if (ptyId && window.electronAPI && window.electronAPI.terminalWrite) {
      window.electronAPI.terminalWrite(ptyId, data);
    }
  });

  // Wait for terminal to be fully initialized before creating PTY
  // This ensures xterm.js is ready to process escape sequences correctly
  nextTick(async () => {
    if (!terminal) return;
    
    // Fit terminal to container
    if (fitAddon) {
      fitAddon.fit();
      console.log('[Terminal] Fitted to container');
    }
    
    // Small delay to ensure xterm.js is fully initialized
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Now create PTY connection
    await createPty();
    console.log('[Terminal] PTY created, ptyId:', ptyId);
    
    // After PTY is created, ensure cursor is visible
    if (terminal) {
      // Re-apply theme to ensure cursor color is set
      const theme = getTerminalTheme();
      terminal.options.theme = theme;
      terminal.options.cursorBlink = true;
      terminal.options.cursorStyle = 'bar';
      terminal.options.cursorWidth = 2;
      
      // Force refresh to redraw everything including cursor
      terminal.refresh(0, terminal.rows - 1);
      
      // Focus the terminal so cursor appears
      terminal.focus();
      console.log('[Terminal] Terminal focused');
      
      // Fit again after everything is ready
      if (fitAddon) {
        fitAddon.fit();
      }
    }
  });

  // Handle window resize
  resizeObserver = new ResizeObserver(() => {
    if (fitAddon) {
      fitAddon.fit();
    }
    handleResize();
  });
  resizeObserver.observe(terminalContainer.value);
  
  // Also handle terminal resize events
  terminal.onResize(() => {
    handleResize();
  });
};

// Cleanup function to properly dispose of terminal resources
const cleanupTerminal = () => {
  // Remove specific listeners (not all listeners)
  if (removeDataListener) {
    removeDataListener();
    removeDataListener = null;
  }
  if (removeExitListener) {
    removeExitListener();
    removeExitListener = null;
  }
  
  // Kill PTY
  if (ptyId && window.electronAPI && window.electronAPI.terminalKill) {
    window.electronAPI.terminalKill(ptyId);
    ptyId = null;
  }
  
  // Disconnect resize observer
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  
  // Dispose terminal
  if (terminal) {
    terminal.dispose();
    terminal = null;
  }
  
  fitAddon = null;
};

// Handle resize - update PTY size
const handleResize = () => {
  if (ptyId && terminal && fitAddon && window.electronAPI && window.electronAPI.terminalResize) {
    const dimensions = fitAddon.proposeDimensions();
    if (dimensions) {
      window.electronAPI.terminalResize(ptyId, dimensions.cols, dimensions.rows);
    }
  }
};

const clear = () => {
  if (terminal) {
    // Use xterm.js's built-in clear method which properly clears the buffer
    terminal.clear();
    
    // Also use ANSI escape sequences to ensure everything is cleared:
    // \x1b[2J - Clear entire screen (viewport)
    // \x1b[3J - Clear scrollback buffer
    // \x1b[H  - Move cursor to home position (top-left)
    terminal.write('\x1b[2J\x1b[3J\x1b[H');
    
    // Send Ctrl+L to the PTY to trigger shell's clear and get fresh prompt
    // This is more reliable than sending 'clear' command as it works in most shells
    if (ptyId && window.electronAPI && window.electronAPI.terminalWrite) {
      window.electronAPI.terminalWrite(ptyId, '\x0c'); // Ctrl+L
    }
    
    // Force a refresh to ensure the display is updated
    terminal.refresh(0, terminal.rows - 1);
    
    // Focus the terminal after clearing
    terminal.focus();
  }
};

const focusTerminal = () => {
  if (terminal) {
    terminal.focus();
  }
};

watch(() => props.cwd, async (newCwd, oldCwd) => {
  // Only recreate if there's a meaningful change and terminal exists
  if (!terminal || !newCwd || newCwd === oldCwd) return;
  
  // Kill the old PTY but keep the terminal display
  if (ptyId && window.electronAPI && window.electronAPI.terminalKill) {
    await window.electronAPI.terminalKill(ptyId);
    ptyId = null;
  }
  
  // Recreate PTY with new cwd
  if (window.electronAPI && window.electronAPI.terminalCreate) {
    const result = await window.electronAPI.terminalCreate(newCwd);
    if (result.success) {
      ptyId = result.ptyId;
    }
  }
});

// Watch for theme changes and update terminal theme
watch(isDarkTheme, () => {
  if (terminal) {
    const newTheme = getTerminalTheme();
    // Update theme
    terminal.options.theme = newTheme;
    // Force xterm to redraw with new theme
    terminal.refresh(0, terminal.rows - 1);
  }
}, { immediate: false });

onMounted(() => {
  initTerminal();
});

onBeforeUnmount(() => {
  // Use the centralized cleanup function
  cleanupTerminal();
});
</script>

<style scoped>
.terminal {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--sidebar);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--muted);
  font-size: 12px;
  color: var(--foreground);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  height: var(--header-md);
  min-height: var(--header-md);
  cursor: grab;
}

.terminal-header:active {
  cursor: grabbing;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.terminal-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ring);
  flex-shrink: 0;
}

.terminal-title {
  font-weight: 600;
  color: var(--foreground);
  font-size: 13px;
}

.clear-btn {
  background: var(--muted);
  border: none;
  color: var(--foreground);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
}

.clear-btn:hover {
  background: var(--accent);
  opacity: 0.9;
}

.clear-btn svg {
  flex-shrink: 0;
}

.terminal-container {
  flex: 1;
  padding: var(--space-6);
  overflow: hidden;
  background: var(--sidebar);
  -ms-overflow-style: none;
  scrollbar-width: none;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  position: relative;
}

.terminal-container::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

:deep(.xterm) {
  height: 100%;
  width: 100%;
  padding: 0 !important;
}

/* Dark mode: set background only on main container elements, NOT on cursor canvas */
.dark :deep(.xterm) {
  background: var(--sidebar) !important;
}

.dark :deep(.xterm-viewport),
.dark :deep(.xterm-screen) {
  background-color: var(--sidebar) !important;
}

/* Do NOT set background on canvas elements - this interferes with cursor rendering */
/* The background is handled by the xterm theme configuration */

:deep(.xterm-viewport) {
  border-radius: 0 0 12px 12px;
}

:deep(.xterm-viewport::-webkit-scrollbar) {
  display: none;
  width: 0;
  height: 0;
}

:deep(.xterm-viewport) {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

:deep(.xterm-screen) {
  border-radius: 0 0 12px 12px;
}

:deep(.xterm .xterm-selection div) {
  background: color-mix(in srgb, var(--primary) 20%, transparent) !important;
}

:deep(.xterm .xterm-helper-textarea) {
  pointer-events: auto !important;
  z-index: 11 !important;
}

/* Cursor layer visibility */
:deep(.xterm .xterm-cursor-layer) {
  opacity: 1 !important;
  z-index: 10 !important;
}

/* Base cursor styles */
:deep(.xterm .xterm-cursor) {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

/* Cursor blink animation */
:deep(.xterm .xterm-cursor.xterm-cursor-blink) {
  animation: xterm-cursor-blink 1s step-end infinite !important;
}

/* Cursor styles - using theme-appropriate colors */
/* Dark mode: warm cream/peach to match primary */
.dark :deep(.xterm .xterm-cursor),
.dark :deep(.xterm .xterm-cursor.xterm-cursor-block),
.dark :deep(.xterm .xterm-cursor.xterm-cursor-bar),
.dark :deep(.xterm .xterm-cursor.xterm-cursor-underline),
.dark :deep(.xterm .xterm-cursor.xterm-cursor-outline) {
  background-color: #ffe0c2 !important;
  border-color: #ffe0c2 !important;
}

/* Light mode: warm brown to match primary */
:not(.dark) :deep(.xterm .xterm-cursor),
:not(.dark) :deep(.xterm .xterm-cursor.xterm-cursor-block),
:not(.dark) :deep(.xterm .xterm-cursor.xterm-cursor-bar),
:not(.dark) :deep(.xterm .xterm-cursor.xterm-cursor-underline),
:not(.dark) :deep(.xterm .xterm-cursor.xterm-cursor-outline) {
  background-color: #644a40 !important;
  border-color: #644a40 !important;
}

@keyframes xterm-cursor-blink {
  0%, 49% { 
    opacity: 1; 
  }
  50%, 100% { 
    opacity: 0; 
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

:deep(.xterm .xterm-rows) {
  font-family: var(--font-mono);
}

:deep(.xterm .xterm-scroll-area) {
  /* Background set by theme-specific rules below */
}

/* Light mode: use sidebar background for terminal */
:not(.dark) .terminal {
  background: var(--sidebar);
}

:not(.dark) .terminal-container {
  background: var(--sidebar);
}

:not(.dark) :deep(.xterm-viewport) {
  background: var(--sidebar) !important;
}

:not(.dark) :deep(.xterm .xterm-scroll-area) {
  background: var(--sidebar) !important;
}

:not(.dark) :deep(.xterm-screen) {
  background: var(--sidebar) !important;
}

/* Dark mode: use sidebar background color - must come after to override light mode */
.dark .terminal {
  background: var(--sidebar) !important;
}

.dark .terminal-container {
  background: var(--sidebar) !important;
}

.dark :deep(.xterm-viewport) {
  background: var(--sidebar) !important;
}

.dark :deep(.xterm .xterm-scroll-area) {
  background: var(--sidebar) !important;
}

.dark :deep(.xterm-screen) {
  background: var(--sidebar) !important;
}
</style>


