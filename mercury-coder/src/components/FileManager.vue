<template>
  <div class="file-manager">
    <!-- Inline toolbar -->
    <div class="file-manager-toolbar" v-if="projectPath">
      <button class="toolbar-btn" @click="loadDirectory" :disabled="loading" title="Refresh">
        <RefreshCw :size="14" :class="{ spinning: loading }" />
      </button>
      <button class="toolbar-btn" @click.stop="startCreatingItem('file')" :disabled="loading || creatingItem" title="New File">
        <FilePlus :size="14" />
      </button>
      <button class="toolbar-btn" @click.stop="startCreatingItem('folder')" :disabled="loading || creatingItem" title="New Folder">
        <FolderPlus :size="14" />
      </button>
    </div>
    
    <!-- File tree with root folder -->
    <div 
      class="file-tree" 
      v-if="projectPath && rootFolder" 
      draggable="false" 
      @click.self="handleTreeClick"
      @contextmenu.prevent="handleTreeContextMenu"
    >
      <!-- Create input at root level if creating in project root -->
      <div 
        v-if="creatingItem && createInPath === projectPath" 
        class="inline-create-item" 
        :style="{ paddingLeft: '8px' }"
      >
        <FilePlus v-if="creatingItemType === 'file'" :size="14" class="create-icon" />
        <FolderPlus v-else :size="14" class="create-icon" />
        <input
          ref="createInputRef"
          v-model="createItemName"
          type="text"
          class="inline-create-input"
          :placeholder="creatingItemType === 'file' ? 'File name (e.g., example.txt)' : 'Folder name'"
          @keydown.enter.prevent="confirmCreate"
          @keydown.escape="cancelCreate"
          @blur="handleInputBlur"
        />
      </div>
      
      <FileTreeNode
        :file="rootFolder"
        :depth="0"
        :active-file-path="activeFilePath"
        :selected-path="selectedPath"
        :creating-item="creatingItem"
        :creating-item-type="creatingItemType"
        :create-item-name="createItemName"
        :create-in-path="createInPath"
        :copied-file-path="copiedFilePath"
        :has-copied-file="!!copiedFilePath"
        :project-path="projectPath"
        @file-selected="handleFileSelect"
        @item-selected="handleItemSelected"
        @confirm-create="confirmCreate"
        @cancel-create="cancelCreate"
        @create-input-blur="handleInputBlur"
        @update:createItemName="(val) => { createItemName = val }"
        @copy-file="handleCopyFile"
        @paste-file="handlePasteFile"
        @move-file="handleMoveFile"
      />
      
      <!-- Context menu for empty space (root level) -->
      <div 
        v-if="treeContextMenuVisible"
        class="context-menu"
        :style="{ top: treeContextMenuY + 'px', left: treeContextMenuX + 'px' }"
        @click.stop
      >
        <button 
          class="context-menu-item" 
          @click="handleTreePaste"
          :disabled="!copiedFilePath"
        >
          <Clipboard :size="14" />
          <span>Paste</span>
        </button>
        <div class="context-menu-divider"></div>
        <button class="context-menu-item" @click="handleTreeNewFile">
          <FilePlus :size="14" />
          <span>New File</span>
        </button>
        <button class="context-menu-item" @click="handleTreeNewFolder">
          <FolderPlus :size="14" />
          <span>New Folder</span>
        </button>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <p v-if="!projectPath" class="empty-state-hint">
        Open a project from the welcome screen to view files
      </p>
      <p v-else-if="loading" class="loading-hint">Loading...</p>
      <p v-else>No files found</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { RefreshCw, FilePlus, FolderPlus, Clipboard } from 'lucide-vue-next';
import FileTreeNode from './FileTreeNode.vue';

const props = defineProps({
  projectPath: {
    type: String,
    default: null,
  },
  activeFilePath: {
    type: String,
    default: null,
  },
});

const emit = defineEmits(['file-selected']);

const files = ref([]);
const loading = ref(false);
const rootFolder = ref(null);
const creatingItem = ref(false);
const creatingItemType = ref('file'); // 'file' or 'folder'
const createItemName = ref('');
const createInputRef = ref(null);
const selectedPath = ref(null); // Currently selected file/folder path
const selectedIsDirectory = ref(false); // Whether the selected item is a directory
const createInPath = ref(null); // Path where new item should be created
const copiedFilePath = ref(null); // Path of file/folder that was copied
const copiedFileIsDirectory = ref(false); // Whether the copied item is a directory
const treeContextMenuVisible = ref(false); // Context menu for empty space
const treeContextMenuX = ref(0);
const treeContextMenuY = ref(0);

const getProjectName = () => {
  if (!props.projectPath) return 'No Project';
  return props.projectPath.split(/[/\\]/).pop();
};

const loadDirectory = async () => {
  console.log('FileManager: loadDirectory called, projectPath:', props.projectPath);
  
  if (!props.projectPath) {
    console.warn('FileManager: No project path provided - setting empty files');
    files.value = [];
    rootFolder.value = null;
    return;
  }
  
  if (!window.electronAPI) {
    console.error('FileManager: Electron API is not available');
    files.value = [];
    rootFolder.value = null;
    return;
  }
  
  console.log('FileManager: Loading directory:', props.projectPath);
  loading.value = true;
  try {
    console.log('FileManager: Calling readDirectory with path:', props.projectPath);
    const entries = await window.electronAPI.readDirectory(props.projectPath);
    console.log('FileManager: readDirectory returned:', entries);
    console.log('FileManager: Loaded', entries?.length || 0, 'entries');
    
    if (!entries) {
      console.warn('FileManager: readDirectory returned null/undefined');
      files.value = [];
      rootFolder.value = null;
      return;
    }
    
    if (entries.length === 0) {
      console.warn('FileManager: Directory is empty');
      files.value = [];
      // Create root folder even if empty
      rootFolder.value = {
        name: getProjectName(),
        path: props.projectPath,
        isDirectory: true,
        isFile: false,
        children: []
      };
      return;
    }
    
    console.log('FileManager: Processing entries:', entries);
    const sortedEntries = entries.sort((a, b) => {
      // Directories first, then files
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.name.localeCompare(b.name);
    });
    files.value = sortedEntries;
    
    // Create root folder object
    rootFolder.value = {
      name: getProjectName(),
      path: props.projectPath,
      isDirectory: true,
      isFile: false,
      children: sortedEntries
    };
    
    console.log('FileManager: Files array set, length:', files.value.length);
    console.log('FileManager: Root folder created:', rootFolder.value);
  } catch (error) {
    console.error('FileManager: Failed to load directory:', error);
    console.error('FileManager: Error details:', {
      message: error.message,
      stack: error.stack,
      path: props.projectPath
    });
    files.value = [];
    rootFolder.value = null;
    // Show error message to user
    alert(`Failed to load directory: ${error.message || error}`);
  } finally {
    loading.value = false;
    console.log('FileManager: loadDirectory completed, files.value.length:', files.value.length);
  }
};

const handleFileSelect = (filePath) => {
  // When a file is selected, also update createInPath to its parent directory
  const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
  if (lastSlash >= 0) {
    createInPath.value = filePath.substring(0, lastSlash) || props.projectPath;
  } else {
    createInPath.value = props.projectPath;
  }
  selectedPath.value = filePath;
  selectedIsDirectory.value = false; // Files are not directories
  emit('file-selected', filePath);
};

const handleItemSelected = (filePath, isDirectory) => {
  // If clicking the same item, keep it selected
  if (selectedPath.value === filePath) {
    return;
  }
  
  selectedPath.value = filePath;
  selectedIsDirectory.value = isDirectory;
  // If it's a directory, set it as the create target
  if (isDirectory) {
    createInPath.value = filePath;
  } else {
    // If it's a file, use its parent directory
    // Extract directory from path (handle both / and \)
    const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
    createInPath.value = lastSlash >= 0 ? filePath.substring(0, lastSlash) : props.projectPath;
  }
};

const handleTreeClick = (event) => {
  // If clicking on the tree container itself (not on a node), deselect
  if (event.target === event.currentTarget || event.target.closest('.file-tree') === event.currentTarget) {
    selectedPath.value = null;
    createInPath.value = props.projectPath;
    treeContextMenuVisible.value = false;
    
    // Cancel creation if clicking outside the input
    if (creatingItem.value && !event.target.closest('.inline-create-item')) {
      cancelCreate();
    }
  }
};

const handleTreeContextMenu = (event) => {
  // Only show context menu if clicking on empty space (not on a file/folder)
  if (event.target === event.currentTarget || event.target.closest('.file-tree') === event.currentTarget) {
    event.preventDefault();
    treeContextMenuX.value = event.clientX;
    treeContextMenuY.value = event.clientY;
    treeContextMenuVisible.value = true;
    selectedPath.value = null;
    createInPath.value = props.projectPath;
    
    // Close context menu when clicking outside
    const closeMenu = (e) => {
      if (!e.target.closest('.context-menu') && !e.target.closest('.file-tree')) {
        treeContextMenuVisible.value = false;
        document.removeEventListener('click', closeMenu);
      }
    };
    setTimeout(() => {
      document.addEventListener('click', closeMenu);
    }, 0);
  }
};

const handleTreePaste = () => {
  treeContextMenuVisible.value = false;
  if (copiedFilePath.value && props.projectPath) {
    handlePasteFile(props.projectPath);
  }
};

const handleTreeNewFile = () => {
  treeContextMenuVisible.value = false;
  startCreatingItem('file');
};

const handleTreeNewFolder = () => {
  treeContextMenuVisible.value = false;
  startCreatingItem('folder');
};

const handleCopyFile = (filePath, isDirectory) => {
  copiedFilePath.value = filePath;
  copiedFileIsDirectory.value = isDirectory;
};

// Helper function to check if a file or directory exists
const pathExists = async (filePath) => {
  try {
    // Try to read as directory first (works for both files and dirs)
    await window.electronAPI.readDirectory(filePath);
    return true;
  } catch {
    try {
      // Try to read as file
      await window.electronAPI.readFile(filePath);
      return true;
    } catch {
      // Doesn't exist
      return false;
    }
  }
};

const handlePasteFile = async (targetDirectory) => {
  if (!copiedFilePath.value) {
    return;
  }
  
  // If targetDirectory is null or empty, use project root
  const pasteDirectory = targetDirectory || props.projectPath;
  if (!pasteDirectory) {
    return;
  }
  
  if (!window.electronAPI?.copyFile) {
    alert('Copy functionality is not available');
    return;
  }
  
  try {
    // Extract filename from copied path
    const lastSlash = Math.max(copiedFilePath.value.lastIndexOf('/'), copiedFilePath.value.lastIndexOf('\\'));
    const fileName = lastSlash >= 0 ? copiedFilePath.value.substring(lastSlash + 1) : copiedFilePath.value;
    
    // Check if pasting in the same directory as source
    const sourceDir = lastSlash >= 0 ? copiedFilePath.value.substring(0, lastSlash) : '';
    const isSameDirectory = sourceDir === pasteDirectory;
    
    // Generate unique filename
    const generateUniqueName = async (baseName, directory, isDir) => {
      let finalName = baseName;
      let counter = 0;
      
      // Split filename and extension (only for files)
      let nameWithoutExt = baseName;
      let extension = '';
      if (!isDir) {
        const lastDot = baseName.lastIndexOf('.');
        const hasExtension = lastDot > 0 && lastDot < baseName.length - 1;
        if (hasExtension) {
          nameWithoutExt = baseName.substring(0, lastDot);
          extension = baseName.substring(lastDot);
        }
      }
      
      // Check if we need to add " copy" suffix
      let needsCopySuffix = isSameDirectory;
      
      // Check if file/directory exists
      let testPath = await window.electronAPI.joinPath(directory, finalName);
      const exists = await pathExists(testPath);
      if (exists) {
        needsCopySuffix = true;
      }
      
      if (needsCopySuffix) {
        // Try " copy", " copy 2", " copy 3", etc.
        while (true) {
          if (counter === 0) {
            finalName = isDir ? `${baseName} copy` : `${nameWithoutExt} copy${extension}`;
          } else {
            finalName = isDir ? `${baseName} copy ${counter}` : `${nameWithoutExt} copy ${counter}${extension}`;
          }
          
          testPath = await window.electronAPI.joinPath(directory, finalName);
          const pathExistsResult = await pathExists(testPath);
          if (!pathExistsResult) {
            // Path doesn't exist, we can use this name
            break;
          }
          counter++;
        }
      }
      
      return finalName;
    };
    
    const uniqueFileName = await generateUniqueName(fileName, pasteDirectory, copiedFileIsDirectory.value);
    const destPath = await window.electronAPI.joinPath(pasteDirectory, uniqueFileName);
    
    // Copy the file/directory
    const result = await window.electronAPI.copyFile(copiedFilePath.value, destPath);
    
    if (result.success) {
      // Refresh file tree
      await loadDirectory();
    } else {
      alert(`Failed to paste: ${result.error}`);
    }
  } catch (error) {
    alert(`Failed to paste: ${error.message}`);
  }
};

const handleMoveFile = async (sourcePath, targetDirectory) => {
  console.log('[FileManager] handleMoveFile called:', { sourcePath, targetDirectory });
  
  if (!sourcePath || !targetDirectory) {
    console.log('[FileManager] Missing source or target');
    return;
  }
  
  if (!window.electronAPI?.renameFile) {
    alert('Move functionality is not available');
    return;
  }
  
  try {
    // Extract filename from source path
    const lastSlash = Math.max(sourcePath.lastIndexOf('/'), sourcePath.lastIndexOf('\\'));
    const fileName = lastSlash >= 0 ? sourcePath.substring(lastSlash + 1) : sourcePath;
    
    console.log('[FileManager] Moving file:', fileName, 'to:', targetDirectory);
    
    // Construct destination path
    const destPath = await window.electronAPI.joinPath(targetDirectory, fileName);
    
    console.log('[FileManager] Destination path:', destPath);
    
    // Check if destination already exists
    const exists = await pathExists(destPath);
    if (exists) {
      alert(`A file or folder with the name "${fileName}" already exists in the destination.`);
      return;
    }
    
    // Move the file/directory using rename (which also works for moving across directories)
    const result = await window.electronAPI.renameFile(sourcePath, destPath);
    
    console.log('[FileManager] Rename result:', result);
    
    if (result.success) {
      // Refresh file tree
      await loadDirectory();
    } else {
      alert(`Failed to move: ${result.error}`);
    }
  } catch (error) {
    console.error('Failed to move file:', error);
    alert(`Failed to move: ${error.message}`);
  }
};

const startCreatingItem = async (type) => {
  if (!props.projectPath) {
    return;
  }
  
  creatingItemType.value = type;
  createItemName.value = type === 'file' ? 'untitled.txt' : 'New Folder';
  creatingItem.value = true;
  
  // Determine where to create the new item
  if (selectedPath.value && createInPath.value) {
    // Use the createInPath that was set when the item was selected
    // This is already the correct directory (parent if file, self if directory)
  } else if (selectedPath.value) {
    // Fallback: if selectedPath exists but createInPath doesn't, determine it
    if (selectedIsDirectory.value) {
      createInPath.value = selectedPath.value;
    } else {
      // It's a file, get its parent directory
      const lastSlash = Math.max(selectedPath.value.lastIndexOf('/'), selectedPath.value.lastIndexOf('\\'));
      createInPath.value = lastSlash >= 0 ? selectedPath.value.substring(0, lastSlash) : props.projectPath;
    }
  } else {
    // No selection, create at project root
    createInPath.value = props.projectPath;
  }
  
  // Focus the input after it's rendered
  await nextTick();
  if (createInputRef.value) {
    createInputRef.value.focus();
    createInputRef.value.select();
  }
};

const confirmCreate = async () => {
  const name = createItemName.value.trim();
  if (!name) {
    cancelCreate();
    return;
  }
  
  creatingItem.value = false; // Hide input immediately
  
  if (creatingItemType.value === 'file') {
    await createNewFile(name);
  } else {
    await createNewFolder(name);
  }
  
  createItemName.value = '';
  creatingItemType.value = 'file';
};

const cancelCreate = () => {
  creatingItem.value = false;
  createItemName.value = '';
  creatingItemType.value = 'file';
  createInPath.value = null;
};

const handleInputBlur = (event) => {
  // Small delay to allow click events on confirm button to fire
  setTimeout(() => {
    // Cancel if still creating and the focus didn't move to another input in the same create item
    if (creatingItem.value) {
      const activeElement = document.activeElement;
      // Only cancel if focus didn't move to another element in the same create item
      if (!activeElement || !activeElement.closest('.inline-create-item')) {
        cancelCreate();
      }
    }
  }, 150);
};

const createNewFile = async (fileName) => {
  if (!fileName || !fileName.trim()) {
    return;
  }
  
  const targetPath = createInPath.value || props.projectPath;
  if (!targetPath) {
    return;
  }
  
  try {
    if (!window.electronAPI) {
      alert('Electron API is not available');
      return;
    }
    
    // Use IPC to join paths properly (handles Windows/Unix differences)
    const filePath = await window.electronAPI.joinPath(targetPath, fileName.trim());
    
    // Create empty file
    const result = await window.electronAPI.writeFile(filePath, '');
    if (result && result.success !== false) {
      // Refresh file tree and open the new file
      await loadDirectory();
      emit('file-selected', filePath);
    } else {
      alert(`Failed to create file: ${result?.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Failed to create file:', error);
    alert(`Failed to create file: ${error.message}`);
  }
};

const createNewFolder = async (folderName) => {
  if (!folderName || !folderName.trim()) {
    return;
  }
  
  const targetPath = createInPath.value || props.projectPath;
  if (!targetPath) {
    return;
  }
  
  try {
    if (!window.electronAPI) {
      alert('Electron API is not available');
      return;
    }
    
    // Use IPC to join paths properly (handles Windows/Unix differences)
    const folderPath = await window.electronAPI.joinPath(targetPath, folderName.trim());
    
    const result = await window.electronAPI.createDirectory(folderPath);
    if (result && result.success) {
      // Refresh file tree
      await loadDirectory();
    } else {
      alert(`Failed to create folder: ${result?.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Failed to create folder:', error);
    alert(`Failed to create folder: ${error.message}`);
  }
};

watch(() => props.projectPath, async (newPath, oldPath) => {
  console.log('FileManager: projectPath prop changed:', { oldPath, newPath });
  
  // Stop watching old project
  if (oldPath && window.electronAPI?.unwatchProject) {
    window.electronAPI.unwatchProject();
    if (fileWatcherCleanup) {
      fileWatcherCleanup();
      fileWatcherCleanup = null;
    }
  }
  
  // Load new directory
  await loadDirectory();
  
  // Start watching new project
  if (newPath && window.electronAPI?.watchProject) {
    console.log('FileManager: Starting file watcher for:', newPath);
    window.electronAPI.watchProject(newPath);
    
    // Listen for file system change events
    if (window.electronAPI.onFileSystemChange) {
      // Clean up old listener if exists
      if (fileWatcherCleanup) {
        fileWatcherCleanup();
      }
      fileWatcherCleanup = window.electronAPI.onFileSystemChange((data) => {
        console.log('FileManager: File system change detected:', data);
        // For deletions, refresh immediately (no debounce needed)
        // For other changes, use small debounce
        const isDeletion = data.type === 'unlink' || data.type === 'unlinkDir';
        const debounceTime = isDeletion ? 50 : 100;
        
        clearTimeout(window._fileRefreshTimeout);
        window._fileRefreshTimeout = setTimeout(() => {
          console.log('FileManager: Refreshing due to file system change:', data.type, data.path);
          loadDirectory();
        }, debounceTime);
      });
    }
  }
}, { immediate: true });

// File system watcher
let fileWatcherCleanup = null;

const handleDocumentClick = (event) => {
  // Cancel creation if clicking outside the file tree or the create input
  if (creatingItem.value) {
    if (!event.target.closest('.file-tree') && !event.target.closest('.inline-create-item')) {
      cancelCreate();
    }
  }
};

// Listen for refresh events
onMounted(() => {
  console.log('FileManager: Mounted with projectPath:', props.projectPath);
  if (props.projectPath) {
    loadDirectory();
    // Start watching for file system changes
    if (window.electronAPI?.watchProject) {
      console.log('FileManager: Starting file watcher on mount for:', props.projectPath);
      window.electronAPI.watchProject(props.projectPath);
      
      // Listen for file system change events
      if (window.electronAPI.onFileSystemChange) {
        fileWatcherCleanup = window.electronAPI.onFileSystemChange((data) => {
          console.log('FileManager: File system change detected:', data);
          // Immediate refresh for file changes (reduced debounce for real-time feel)
          clearTimeout(window._fileRefreshTimeout);
          window._fileRefreshTimeout = setTimeout(() => {
            console.log('FileManager: Refreshing due to file system change:', data.type, data.path);
            loadDirectory();
          }, 100); // Reduced from 300ms to 100ms for faster updates
        });
      }
    } else {
      console.warn('FileManager: watchProject API not available');
    }
  } else {
    console.warn('FileManager: No projectPath on mount');
  }
  
  window.addEventListener('refresh-file-tree', loadDirectory);
  document.addEventListener('click', handleDocumentClick);
});

onUnmounted(() => {
  window.removeEventListener('refresh-file-tree', loadDirectory);
  document.removeEventListener('click', handleDocumentClick);
  
  // Stop file watcher
  if (fileWatcherCleanup) {
    fileWatcherCleanup();
    fileWatcherCleanup = null;
  }
  
  if (window.electronAPI?.unwatchProject) {
    window.electronAPI.unwatchProject();
  }
  
  if (window._fileRefreshTimeout) {
    clearTimeout(window._fileRefreshTimeout);
  }
});
</script>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--sidebar);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.file-manager-toolbar {
  display: flex;
  align-items: center;
  padding: var(--space-4);
  background: var(--muted);
  gap: var(--space-2);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  height: var(--header-md);
  min-height: var(--header-md);
  cursor: grab;
}

.file-manager-toolbar:active {
  cursor: grabbing;
}

.toolbar-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--accent);
  color: var(--foreground);
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toolbar-btn .spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.file-tree {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2) 0;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--muted-foreground) 10%, transparent) transparent;
}

.file-tree::-webkit-scrollbar {
  width: var(--space-3);
}

.file-tree::-webkit-scrollbar-track {
  background: transparent;
}

.file-tree::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--muted-foreground) 10%, transparent);
  border-radius: var(--radius-xs);
}

.file-tree::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--muted-foreground) 15%, transparent);
}

.dark .file-tree {
  scrollbar-color: color-mix(in srgb, var(--muted-foreground) 10%, transparent) transparent;
}

.dark .file-tree::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--muted-foreground) 10%, transparent);
}

.dark .file-tree::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--muted-foreground) 15%, transparent);
}

.inline-create-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  margin-bottom: var(--space-1);
}

.create-icon {
  flex-shrink: 0;
  width: var(--icon-sm);
  height: var(--icon-sm);
  color: var(--muted-foreground);
}

.inline-create-input {
  flex: 1;
  padding: var(--space-1) var(--space-3);
  font-size: 13px;
  background: var(--input);
  border: none;
  border-radius: var(--radius-xs);
  color: var(--foreground);
  outline: none;
  font-family: inherit;
}

.inline-create-input:focus {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 20%, transparent);
}

.empty-state {
  padding: var(--space-10);
  text-align: center;
  color: var(--muted-foreground);
  font-size: 13px;
}

.empty-state-hint {
  font-size: 12px;
  margin-top: 8px;
  opacity: 0.8;
}

.loading-hint {
  font-size: 12px;
  margin-top: 8px;
  opacity: 0.8;
  font-style: italic;
}

/* Context Menu for Empty Space */
.context-menu {
  position: fixed;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10000;
  min-width: 150px;
  padding: 4px;
  display: flex;
  flex-direction: column;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--foreground);
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  text-align: left;
  transition: background 0.15s;
}

.context-menu-item:hover:not(:disabled) {
  background: var(--accent);
}

.context-menu-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.context-menu-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.context-menu-item svg {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}
</style>


