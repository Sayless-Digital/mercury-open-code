<template>
  <div class="file-manager">
    <!-- Inline toolbar -->
    <div class="file-manager-toolbar" v-if="projectPath">
      <button class="toolbar-btn" @click="loadDirectory" :disabled="loading" title="Refresh">
        <RefreshCw :size="14" :class="{ spinning: loading }" />
      </button>
      <button class="toolbar-btn" @click="startCreatingItem('file')" :disabled="loading || creatingItem" title="New File">
        <FilePlus :size="14" />
      </button>
      <button class="toolbar-btn" @click="startCreatingItem('folder')" :disabled="loading || creatingItem" title="New Folder">
        <FolderPlus :size="14" />
      </button>
    </div>
    
    <!-- File tree with root folder -->
    <div class="file-tree" v-if="projectPath && rootFolder" draggable="false">
      <!-- Inline input for new file/folder at the top -->
      <div v-if="creatingItem" class="inline-create-item" :style="{ paddingLeft: '8px' }">
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
        @file-selected="handleFileSelect"
      />
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
import { RefreshCw, FilePlus, FolderPlus } from 'lucide-vue-next';
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
  emit('file-selected', filePath);
};

const startCreatingItem = async (type) => {
  if (!props.projectPath) {
    return;
  }
  
  creatingItemType.value = type;
  createItemName.value = type === 'file' ? 'untitled.txt' : 'New Folder';
  creatingItem.value = true;
  
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
};

const handleInputBlur = () => {
  // Small delay to allow click events on confirm button to fire
  setTimeout(() => {
    if (creatingItem.value && !createItemName.value.trim()) {
      cancelCreate();
    }
  }, 200);
};

const createNewFile = async (fileName) => {
  if (!props.projectPath || !fileName || !fileName.trim()) {
    return;
  }
  
  try {
    if (!window.electronAPI) {
      alert('Electron API is not available');
      return;
    }
    
    // Use IPC to join paths properly (handles Windows/Unix differences)
    const filePath = await window.electronAPI.joinPath(props.projectPath, fileName.trim());
    
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
  if (!props.projectPath || !folderName || !folderName.trim()) {
    return;
  }
  
  try {
    if (!window.electronAPI) {
      alert('Electron API is not available');
      return;
    }
    
    // Use IPC to join paths properly (handles Windows/Unix differences)
    const folderPath = await window.electronAPI.joinPath(props.projectPath, folderName.trim());
    
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
});

onUnmounted(() => {
  window.removeEventListener('refresh-file-tree', loadDirectory);
  
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
</style>


