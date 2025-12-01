import { onMounted, onUnmounted } from 'vue';
import { useMenuActions } from './useMenuActions';

export function useKeyboardShortcuts() {
  const menuActions = useMenuActions();

  const handleKeyDown = (event) => {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const ctrlOrCmd = isMac ? event.metaKey : event.ctrlKey;

    // File operations
    if (ctrlOrCmd && event.key === 'n' && !event.shiftKey) {
      event.preventDefault();
      menuActions.createNewFile();
    } else if (ctrlOrCmd && event.key === 'o') {
      event.preventDefault();
      menuActions.openFile();
    } else if (ctrlOrCmd && event.key === 's') {
      if (event.shiftKey) {
        event.preventDefault();
        menuActions.saveFileAs();
      } else {
        event.preventDefault();
        menuActions.saveFile();
      }
    } else if (ctrlOrCmd && event.key === 'w') {
      event.preventDefault();
      menuActions.closeCurrentFile();
    } else if (ctrlOrCmd && event.key === 'q') {
      event.preventDefault();
      // Exit handled by window controls
    }

    // Edit operations
    if (ctrlOrCmd && event.key === 'z' && !event.shiftKey) {
      // Undo - Monaco handles this, but we can trigger it
      if (!event.target.closest('.monaco-editor')) {
        menuActions.undo();
      }
    } else if ((ctrlOrCmd && event.key === 'y') || (ctrlOrCmd && event.shiftKey && event.key === 'z')) {
      // Redo
      if (!event.target.closest('.monaco-editor')) {
        event.preventDefault();
        menuActions.redo();
      }
    } else if (ctrlOrCmd && event.key === 'x') {
      // Cut - Monaco handles this
      if (!event.target.closest('.monaco-editor')) {
        menuActions.cut();
      }
    } else if (ctrlOrCmd && event.key === 'c') {
      // Copy - Monaco handles this
      if (!event.target.closest('.monaco-editor')) {
        menuActions.copy();
      }
    } else if (ctrlOrCmd && event.key === 'v') {
      // Paste - Monaco handles this
      if (!event.target.closest('.monaco-editor')) {
        menuActions.paste();
      }
    } else if (ctrlOrCmd && event.key === 'f') {
      if (!event.target.closest('.monaco-editor')) {
        event.preventDefault();
        menuActions.findInEditor();
      }
    } else if (ctrlOrCmd && event.key === 'h') {
      if (!event.target.closest('.monaco-editor')) {
        event.preventDefault();
        menuActions.replaceInEditor();
      }
    } else if (ctrlOrCmd && event.key === 'a') {
      if (!event.target.closest('.monaco-editor')) {
        event.preventDefault();
        menuActions.selectAll();
      }
    }

    // View operations
    if (ctrlOrCmd && event.shiftKey && event.key === 'P') {
      event.preventDefault();
      alert('Command Palette coming soon!');
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown);
  });
}








































