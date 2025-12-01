import { ref } from 'vue';
import { useProjectStore } from '@/stores/project';
import { useEditorStore } from '@/stores/editor';

export function useMenuActions() {
  const projectStore = useProjectStore();
  const editorStore = useEditorStore();

  const openFolder = async () => {
    try {
      const result = await window.electronAPI?.openFolderDialog();
      if (result && result.path) {
        const projectName = result.path.split(/[/\\]/).pop();
        const addResult = await window.electronAPI.addProject(projectName, result.path);
        if (addResult && addResult.success) {
          const project = {
            id: addResult.id,
            name: projectName,
            path: result.path,
          };
          projectStore.setCurrentProject(project);
        }
      }
    } catch (error) {
      console.error('Failed to open folder:', error);
    }
  };

  const openFile = async () => {
    try {
      const result = await window.electronAPI?.openFileDialog();
      if (result && result.path) {
        projectStore.setActiveFile(result.path);
      }
    } catch (error) {
      console.error('Failed to open file:', error);
    }
  };

  const createNewFile = async () => {
    try {
      if (!projectStore.currentProject) {
        alert('Please open a project first');
        return;
      }
      const fileName = prompt('Enter file name:', 'untitled.txt');
      if (!fileName || !fileName.trim()) return;
      
      // Use IPC to join paths properly (handles Windows/Unix differences)
      const filePath = await window.electronAPI.joinPath(projectStore.currentProject.path, fileName.trim());
      
      // Create empty file
      const result = await window.electronAPI.writeFile(filePath, '');
      if (result && result.success !== false) {
        projectStore.setActiveFile(filePath);
        // Refresh file tree
        window.dispatchEvent(new CustomEvent('refresh-file-tree'));
      } else {
        alert(`Failed to create file: ${result?.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to create file:', error);
      alert(`Failed to create file: ${error.message}`);
    }
  };

  const createNewFolder = async () => {
    try {
      if (!projectStore.currentProject) {
        alert('Please open a project first');
        return;
      }
      const folderName = prompt('Enter folder name:', 'New Folder');
      if (!folderName || !folderName.trim()) return;
      
      // Use IPC to join paths properly (handles Windows/Unix differences)
      const folderPath = await window.electronAPI.joinPath(projectStore.currentProject.path, folderName.trim());
      
      const result = await window.electronAPI.createDirectory(folderPath);
      if (result && result.success) {
        // Refresh file tree
        window.dispatchEvent(new CustomEvent('refresh-file-tree'));
      } else {
        alert(`Failed to create folder: ${result?.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to create folder:', error);
      alert(`Failed to create folder: ${error.message}`);
    }
  };

  const saveFile = async () => {
    if (!projectStore.activeFile || !editorStore.editorInstance) {
      return;
    }
    const content = editorStore.editorInstance.getValue();
    try {
      await window.electronAPI.writeFile(projectStore.activeFile, content);
      if (projectStore.currentProject) {
        await window.electronAPI.addRecentFile(
          projectStore.currentProject.id,
          projectStore.activeFile
        );
      }
    } catch (error) {
      console.error('Failed to save file:', error);
      alert(`Failed to save file: ${error.message}`);
    }
  };

  const saveFileAs = async () => {
    try {
      if (!projectStore.activeFile) {
        alert('No file to save');
        return;
      }
      const result = await window.electronAPI?.showSaveDialog({
        defaultPath: projectStore.activeFile,
        filters: [{ name: 'All Files', extensions: ['*'] }],
      });
      if (result && result.path) {
        const content = editorStore.editorInstance?.getValue() || '';
        await window.electronAPI.writeFile(result.path, content);
        projectStore.setActiveFile(result.path);
      }
    } catch (error) {
      console.error('Failed to save file:', error);
    }
  };

  const closeCurrentFile = () => {
    if (projectStore.activeFile) {
      projectStore.closeFile(projectStore.activeFile);
    }
  };

  const closeProject = () => {
    projectStore.setCurrentProject(null);
    projectStore.openFiles.value = [];
    projectStore.activeFile = null;
  };

  const findInEditor = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.getAction('actions.find').run();
    }
  };

  const replaceInEditor = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.getAction('editor.action.startFindReplaceAction').run();
    }
  };

  const showCommandPalette = () => {
    alert('Command Palette coming soon!');
  };

  const selectAll = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.getAction('editor.action.selectAll').run();
    }
  };

  const undo = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.trigger('editor', 'undo');
    }
  };

  const redo = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.trigger('editor', 'redo');
    }
  };

  const cut = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.trigger('editor', 'editor.action.clipboardCutAction');
    }
  };

  const copy = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.trigger('editor', 'editor.action.clipboardCopyAction');
    }
  };

  const paste = () => {
    if (editorStore.editorInstance) {
      editorStore.editorInstance.trigger('editor', 'editor.action.clipboardPasteAction');
    }
  };

  return {
    openFolder,
    openFile,
    createNewFile,
    createNewFolder,
    saveFile,
    saveFileAs,
    closeCurrentFile,
    closeProject,
    findInEditor,
    replaceInEditor,
    selectAll,
    undo,
    redo,
    cut,
    copy,
    paste,
  };
}

