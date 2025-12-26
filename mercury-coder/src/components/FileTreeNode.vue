<template>
  <div class="file-tree-node">
    <div 
      class="node-item"
      :class="{ 
        'is-directory': file.isDirectory, 
        'is-file': file.isFile,
        'is-expanded': file.isDirectory && expanded,
        'is-active': isActive,
        'is-selected': isSelected
      }"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      @click="handleClick"
      @contextmenu.prevent="handleContextMenu"
    >
      <!-- Dropdown arrow for directories -->
      <ChevronRight 
        v-if="file.isDirectory" 
        class="chevron-icon"
        :class="{ 'expanded': expanded }"
        :size="14"
      />
      <span v-else class="chevron-spacer"></span>
      
      <component :is="getIcon" class="node-icon" :size="16" />
      <span 
        ref="renameInputRef"
        class="node-name"
        :class="{ 'is-editing': isRenaming }"
        :contenteditable="isRenaming"
        @blur="confirmRename"
        @keydown.enter.prevent="confirmRename"
        @keydown.escape="cancelRename"
        v-text="file.name"
      ></span>
    </div>
    
    <!-- Context Menu -->
    <div 
      v-if="contextMenuVisible"
      class="context-menu"
      :style="{ top: contextMenuY + 'px', left: contextMenuX + 'px' }"
      @click.stop
    >
      <button class="context-menu-item" @click="handleCopy">
        <Copy :size="14" />
        <span>Copy</span>
      </button>
      <button 
        class="context-menu-item" 
        @click="handlePaste"
        :disabled="!hasCopiedFile"
      >
        <Clipboard :size="14" />
        <span>Paste</span>
      </button>
      <div class="context-menu-divider"></div>
      <button 
        v-if="file.isDirectory"
        class="context-menu-item" 
        @click="handleOpenInExplorer"
      >
        <ExternalLink :size="14" />
        <span>Open in Explorer</span>
      </button>
      <div v-if="file.isDirectory" class="context-menu-divider"></div>
      <button class="context-menu-item" @click="handleMove">
        <FolderOpen :size="14" />
        <span>Move</span>
      </button>
      <button class="context-menu-item" @click="startRename">
        <Pencil :size="14" />
        <span>Rename</span>
      </button>
      <button class="context-menu-item context-menu-item-danger" @click="handleDelete">
        <Trash2 :size="14" />
        <span>Delete</span>
      </button>
    </div>
    
    <!-- Move Dialog -->
    <div v-if="showMoveDialog" class="move-dialog-overlay" @click="cancelMove">
      <div class="move-dialog" @click.stop>
        <div class="move-dialog-header">
          <h3>Move {{ file.isDirectory ? 'Folder' : 'File' }}</h3>
          <button @click="cancelMove" class="close-btn">
            <X :size="16" />
          </button>
        </div>
        <div class="move-dialog-body">
          <p class="move-source">Moving: <strong>{{ file.name }}</strong></p>
          <p class="move-label">Select destination folder:</p>
          <div class="move-tree-container">
            <MoveDestinationTree
              :project-path="projectPath"
              :current-path="file.path"
              :selected-path="moveTargetPath"
              @path-selected="(path) => { console.log('[FileTreeNode] Path selected:', path); moveTargetPath = path; }"
            />
          </div>
        </div>
        <div class="move-dialog-actions">
          <button @click="cancelMove" class="dialog-btn cancel-dialog-btn">Cancel</button>
          <button @click="confirmMove" class="dialog-btn confirm-dialog-btn" :disabled="!canMove">Move</button>
        </div>
      </div>
    </div>
    
    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog" class="delete-dialog-overlay" @click="cancelDelete">
      <div class="delete-dialog" @click.stop>
        <div class="delete-dialog-header">
          <AlertTriangle :size="20" class="delete-dialog-icon" />
          <h3>Delete {{ file.isDirectory ? 'Folder' : 'File' }}?</h3>
        </div>
        <div class="delete-dialog-body">
          <p>Are you sure you want to delete <strong>{{ file.name }}</strong>?</p>
          <p class="delete-warning">This action cannot be undone.</p>
        </div>
        <div class="delete-dialog-actions">
          <button class="delete-dialog-btn cancel-btn" @click="cancelDelete">
            Cancel
          </button>
          <button class="delete-dialog-btn confirm-btn" @click="confirmDelete">
            Delete
          </button>
        </div>
      </div>
    </div>
    
    <div v-if="file.isDirectory && expanded" class="node-children">
      <!-- Create input appears at the top of selected directory -->
      <div 
        v-if="showCreateInput" 
        class="inline-create-item" 
        :style="{ paddingLeft: `${(depth + 1) * 16 + 8}px` }"
      >
        <FilePlus v-if="creatingItemType === 'file'" :size="14" class="create-icon" />
        <FolderPlus v-else :size="14" class="create-icon" />
        <input
          ref="createInputRef"
          v-model="localCreateItemName"
          type="text"
          class="inline-create-input"
          :placeholder="creatingItemType === 'file' ? 'File name (e.g., example.txt)' : 'Folder name'"
          @keydown.enter.prevent="$emit('confirm-create')"
          @keydown.escape="$emit('cancel-create')"
          @blur="$emit('create-input-blur')"
        />
      </div>
      
      <FileTreeNode
        v-for="child in children"
        :key="child.path"
        :file="child"
        :depth="depth + 1"
        :active-file-path="activeFilePath"
        :selected-path="selectedPath"
        :creating-item="creatingItem"
        :creating-item-type="creatingItemType"
        :create-item-name="createItemName"
        :create-in-path="createInPath"
        :copied-file-path="copiedFilePath"
        :has-copied-file="hasCopiedFile"
        :project-path="projectPath"
        @file-selected="$emit('file-selected', $event)"
        @item-selected="(path, isDirectory) => emit('item-selected', path, isDirectory)"
        @confirm-create="$emit('confirm-create')"
        @cancel-create="$emit('cancel-create')"
        @create-input-blur="$emit('create-input-blur')"
        @update:createItemName="$emit('update:createItemName', $event)"
        @copy-file="(path, isDirectory) => emit('copy-file', path, isDirectory)"
        @paste-file="(path) => emit('paste-file', path)"
        @move-file="(sourcePath, targetDirectory) => emit('move-file', sourcePath, targetDirectory)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { 
  Folder, FolderOpen, File, FileText, FileCode, FileJson, 
  FileImage, FileType, Code, FileCode2, Image as ImageIcon,
  ChevronRight, Pencil, Trash2, FilePlus, FolderPlus, AlertTriangle, Copy, Clipboard, X, ExternalLink
} from 'lucide-vue-next';
import MoveDestinationTree from './MoveDestinationTree.vue';

const props = defineProps({
  file: {
    type: Object,
    required: true,
  },
  depth: {
    type: Number,
    default: 0,
  },
  activeFilePath: {
    type: String,
    default: null,
  },
  selectedPath: {
    type: String,
    default: null,
  },
  creatingItem: {
    type: Boolean,
    default: false,
  },
  creatingItemType: {
    type: String,
    default: 'file',
  },
  createItemName: {
    type: String,
    default: '',
  },
  createInPath: {
    type: String,
    default: null,
  },
  copiedFilePath: {
    type: String,
    default: null,
  },
  hasCopiedFile: {
    type: Boolean,
    default: false,
  },
  projectPath: {
    type: String,
    default: null,
  },
});

const emit = defineEmits(['file-selected', 'item-selected', 'confirm-create', 'cancel-create', 'create-input-blur', 'update:createItemName', 'copy-file', 'paste-file', 'move-file']);

// Initialize expanded state and children
// If children are preloaded, start expanded
const expanded = ref(props.file.children ? props.file.children.length > 0 : false);
const children = ref(props.file.children || []);
const loading = ref(false);

// Context menu state
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);

// Rename state
const isRenaming = ref(false);
const renameValue = ref('');
const renameInputRef = ref(null);
const originalFilePath = ref(null);

// Delete dialog state
const showDeleteDialog = ref(false);

// Move dialog state
const showMoveDialog = ref(false);
const moveTargetPath = ref(null);


// Check if this file/folder is the active one
const isActive = computed(() => {
  return props.activeFilePath && props.file.path === props.activeFilePath;
});

// Check if this file/folder is selected
const isSelected = computed(() => {
  return props.selectedPath && props.file.path === props.selectedPath;
});

// Check if we should show the create input in this directory
// Only show in subdirectories (depth > 0), root level is handled in FileManager
const showCreateInput = computed(() => {
  return props.creatingItem && 
         props.file.isDirectory && 
         props.createInPath === props.file.path &&
         props.depth > 0; // Don't show at root level
});

const createInputRef = ref(null);
const localCreateItemName = ref('');

// Sync local value with prop
watch(() => props.createItemName, (newVal) => {
  localCreateItemName.value = newVal;
}, { immediate: true });

// Emit updates
watch(localCreateItemName, (newVal) => {
  emit('update:createItemName', newVal);
});

// Focus create input when it appears
watch(showCreateInput, async (show) => {
  if (show) {
    await nextTick();
    if (createInputRef.value) {
      createInputRef.value.focus();
      createInputRef.value.select();
    }
  }
});

// Auto-expand folder if it contains the active file
const autoExpandForActiveFile = async () => {
  if (props.file.isDirectory && props.activeFilePath) {
    // Normalize paths for comparison
    const dirPath = props.file.path.replace(/\\/g, '/');
    const activePath = props.activeFilePath.replace(/\\/g, '/');
    
    // Check if the active file is inside this directory
    if (activePath.startsWith(dirPath + '/')) {
      if (!expanded.value) {
        expanded.value = true;
        if (children.value.length === 0) {
          await loadChildren();
        }
        // After loading, recursively expand children if needed
        if (children.value.length > 0) {
          // This will be handled by child components through the watch
        }
      }
    }
  }
};

const getIcon = computed(() => {
  if (props.file.isDirectory) {
    return expanded.value ? FolderOpen : Folder;
  }
  // Get file extension
  const fileName = props.file.name || '';
  const lastDot = fileName.lastIndexOf('.');
  if (lastDot === -1 || lastDot === fileName.length - 1) {
    // No extension or ends with dot - use default File icon
    return File;
  }
  const ext = fileName.substring(lastDot + 1).toLowerCase();
  const iconMap = {
    js: Code,
    ts: FileCode,
    jsx: FileCode2,
    tsx: FileCode2,
    py: FileCode,
    java: FileCode,
    cpp: FileCode,
    c: FileCode,
    html: FileCode,
    css: FileCode,
    scss: FileCode,
    sass: FileCode,
    json: FileJson,
    xml: FileText,
    yaml: FileText,
    yml: FileText,
    md: FileText,
    txt: FileText,
    vue: FileCode,
    png: ImageIcon,
    jpg: ImageIcon,
    jpeg: ImageIcon,
    gif: ImageIcon,
    svg: ImageIcon,
  };
  return iconMap[ext] || File;
});

const handleClick = async (event) => {
  // Don't handle clicks when renaming
  if (isRenaming.value) {
    return;
  }
  
  event.stopPropagation();
  
  // Emit selection event (pass path and isDirectory as separate parameters)
  emit('item-selected', props.file.path, props.file.isDirectory);
  
  if (props.file.isDirectory) {
    expanded.value = !expanded.value;
    if (expanded.value && children.value.length === 0) {
      await loadChildren();
    }
  } else {
    // It's a file, open it
    emit('file-selected', props.file.path);
  }
};

const loadChildren = async (force = false) => {
  // If children are already loaded and not forcing, don't reload
  if (!force && children.value.length > 0 && props.file.children) {
    return;
  }
  
  loading.value = true;
  try {
    const entries = await window.electronAPI.readDirectory(props.file.path);
    children.value = entries.sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.name.localeCompare(b.name);
    });
    // After loading children, check if we need to auto-expand for active file
    if (props.activeFilePath) {
      await autoExpandForActiveFile();
    }
  } catch (error) {
    console.error('Failed to load children:', error);
  } finally {
    loading.value = false;
  }
};

// Listen for file system changes and refresh if this directory is affected
const handleFileSystemChange = (data) => {
  if (!props.file.isDirectory || !expanded.value) {
    return;
  }
  
  const changePath = data.path?.replace(/\\/g, '/') || '';
  const dirPath = props.file.path.replace(/\\/g, '/');
  
  // Check if the change is a direct child of this directory
  // (i.e., the file/directory is immediately inside this directory, not in a subdirectory)
  if (changePath.startsWith(dirPath + '/')) {
    const relativePath = changePath.substring(dirPath.length + 1);
    const isDirectChild = !relativePath.includes('/');
    
    if (isDirectChild) {
      console.log(`FileTreeNode: Refreshing ${dirPath} due to ${data.type} at ${changePath}`);
      // Force reload children with a small delay to ensure file system has settled
      setTimeout(() => {
        loadChildren(true);
      }, 50);
    }
  }
};

// Set up file system change listener
let fileSystemChangeCleanup = null;

// Watch for active file changes and auto-expand
watch(() => props.activeFilePath, async () => {
  await autoExpandForActiveFile();
}, { immediate: true });

const handleContextMenu = (event) => {
  event.preventDefault();
  event.stopPropagation();
  contextMenuX.value = event.clientX;
  contextMenuY.value = event.clientY;
  contextMenuVisible.value = true;
  
  // Close context menu when clicking outside
  const closeMenu = (e) => {
    if (!e.target.closest('.context-menu') && !e.target.closest('.node-item')) {
      contextMenuVisible.value = false;
      document.removeEventListener('click', closeMenu);
    }
  };
  setTimeout(() => {
    document.addEventListener('click', closeMenu);
  }, 0);
};

const startRename = () => {
  contextMenuVisible.value = false;
  isRenaming.value = true;
  renameValue.value = props.file.name;
  originalFilePath.value = props.file.path; // Store the original path to avoid stale references
  nextTick(() => {
    if (renameInputRef.value) {
      renameInputRef.value.focus();
      // Select all text for easy renaming
      const range = document.createRange();
      range.selectNodeContents(renameInputRef.value);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  });
};

const confirmRename = async (event) => {
  if (!renameInputRef.value || !originalFilePath.value) {
    cancelRename();
    return;
  }
  
  const newName = renameInputRef.value.textContent?.trim() || '';
  
  if (!newName || newName === props.file.name) {
    cancelRename();
    return;
  }
  
  // Use the stored original path to avoid stale references
  const filePath = originalFilePath.value;
  
  // Construct new path by replacing the filename
  // Handle both forward and backward slashes for cross-platform compatibility
  const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
  const dir = lastSlash >= 0 ? filePath.substring(0, lastSlash + 1) : '';
  const newPath = dir + newName;
  
  if (!window.electronAPI?.renameFile) {
    alert('Rename functionality is not available');
    cancelRename();
    return;
  }
  
  try {
    const result = await window.electronAPI.renameFile(filePath, newPath);
    if (result.success) {
      isRenaming.value = false;
      originalFilePath.value = null;
      // The file system watcher should detect the change and refresh
    } else {
      alert(`Failed to rename: ${result.error}`);
      cancelRename();
    }
  } catch (error) {
    alert(`Failed to rename: ${error.message}`);
    cancelRename();
  }
};

const cancelRename = () => {
  isRenaming.value = false;
  originalFilePath.value = null;
  if (renameInputRef.value) {
    renameInputRef.value.textContent = props.file.name;
  }
  renameValue.value = '';
};

const handleDelete = () => {
  contextMenuVisible.value = false;
  showDeleteDialog.value = true;
};

const cancelDelete = () => {
  showDeleteDialog.value = false;
};

const confirmDelete = async () => {
  showDeleteDialog.value = false;
  
  if (!window.electronAPI?.deleteFile) {
    alert('Delete functionality is not available');
    return;
  }
  
  try {
    const result = await window.electronAPI.deleteFile(props.file.path);
    if (!result.success) {
      alert(`Failed to delete: ${result.error}`);
    }
    // The file system watcher should detect the change and refresh
  } catch (error) {
    alert(`Failed to delete: ${error.message}`);
  }
};

const handleCopy = () => {
  contextMenuVisible.value = false;
  emit('copy-file', props.file.path, props.file.isDirectory);
};

const handlePaste = () => {
  contextMenuVisible.value = false;
  // If it's a directory, paste into it
  // If it's a file, paste into its parent directory
  if (props.file.isDirectory) {
    emit('paste-file', props.file.path);
  } else {
    // Get parent directory of the file
    const lastSlash = Math.max(props.file.path.lastIndexOf('/'), props.file.path.lastIndexOf('\\'));
    if (lastSlash >= 0) {
      const parentDirectory = props.file.path.substring(0, lastSlash);
      emit('paste-file', parentDirectory);
    } else {
      // File is at root level (no directory separator found)
      // Emit null and FileManager will use projectPath
      emit('paste-file', null);
    }
  }
};

const canMove = computed(() => {
  if (!moveTargetPath.value) {
    return props.projectPath && props.file.path !== props.projectPath;
  }
  // Can't move to itself or into itself
  if (moveTargetPath.value === props.file.path) {
    return false;
  }
  // Can't move a directory into itself or its children
  if (props.file.isDirectory) {
    const normalizedSourcePath = props.file.path.replace(/\\/g, '/');
    const normalizedTargetPath = moveTargetPath.value.replace(/\\/g, '/');
    if (normalizedTargetPath.startsWith(normalizedSourcePath + '/')) {
      return false;
    }
  }
  return true;
});

const handleOpenInExplorer = async () => {
  contextMenuVisible.value = false;
  if (props.file.isDirectory && window.electronAPI?.openPathInExplorer) {
    try {
      const result = await window.electronAPI.openPathInExplorer(props.file.path);
      if (!result || !result.success) {
        console.error('Failed to open directory in explorer:', result?.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Failed to open directory in explorer:', error);
    }
  }
};

const handleMove = () => {
  contextMenuVisible.value = false;
  showMoveDialog.value = true;
  // Initialize with parent directory or project root
  const lastSlash = Math.max(props.file.path.lastIndexOf('/'), props.file.path.lastIndexOf('\\'));
  if (lastSlash >= 0) {
    moveTargetPath.value = props.file.path.substring(0, lastSlash);
  } else {
    moveTargetPath.value = props.projectPath || null;
  }
  console.log('[FileTreeNode] Move dialog opened, initial target:', moveTargetPath.value);
};

const confirmMove = () => {
  if (!canMove.value) {
    return;
  }
  const targetDirectory = moveTargetPath.value || props.projectPath;
  if (targetDirectory) {
    emit('move-file', props.file.path, targetDirectory);
  }
  showMoveDialog.value = false;
  moveTargetPath.value = null;
};

const cancelMove = () => {
  showMoveDialog.value = false;
  moveTargetPath.value = null;
};

onMounted(async () => {
  if (props.activeFilePath && props.file.isDirectory) {
    await autoExpandForActiveFile();
  }
  
  // Listen for file system changes if this is a directory
  if (props.file.isDirectory && window.electronAPI?.onFileSystemChange) {
    fileSystemChangeCleanup = window.electronAPI.onFileSystemChange(handleFileSystemChange);
  }
});

onUnmounted(() => {
  if (fileSystemChangeCleanup) {
    fileSystemChangeCleanup();
    fileSystemChangeCleanup = null;
  }
});
</script>

<style scoped>
.file-tree-node {
  user-select: none;
}

.node-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  font-size: 13px;
  color: var(--foreground);
  transition: background-color 0.15s;
  border-radius: var(--radius-sm);
  user-select: none;
  -webkit-user-select: none;
}

.node-item:has(.node-name.is-editing) {
  user-select: auto;
  -webkit-user-select: auto;
}

.node-item:hover {
  background: var(--accent);
}


.node-item:active {
  cursor: grabbing;
}

.node-item.is-directory {
  font-weight: 500;
}

.node-item.is-active {
  background: var(--accent);
  color: var(--foreground);
  font-weight: 500;
}

.node-item.is-selected {
  background: rgba(var(--primary-rgb, 59, 130, 246), 0.1);
  border-left: 2px solid var(--primary);
}

.node-item.is-expanded {
  /* Additional styles for expanded folders if needed */
}

.chevron-icon {
  flex-shrink: 0;
  width: var(--icon-sm);
  height: var(--icon-sm);
  color: var(--muted-foreground);
  transition: transform 0.2s ease;
  margin-right: var(--space-1);
}

.chevron-icon.expanded {
  transform: rotate(90deg);
}

.chevron-spacer {
  width: var(--icon-md);
  flex-shrink: 0;
}

.node-icon {
  flex-shrink: 0;
  width: var(--icon-md);
  height: var(--icon-md);
  color: var(--muted-foreground);
}

.node-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  outline: none;
  min-width: 0;
}

.node-name.is-editing {
  background: var(--card);
  border: 1px solid var(--primary);
  border-radius: 4px;
  padding: 2px 4px;
  margin: -2px -4px;
  outline: none;
  cursor: text;
  user-select: text;
  -webkit-user-select: text;
  overflow: visible;
  white-space: nowrap;
  text-overflow: clip;
}

.node-children {
  margin-left: 0;
}


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

.context-menu-item-danger {
  color: var(--destructive);
}

.context-menu-item-danger:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.context-menu-item svg {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
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
  border-radius: var(--radius-sm);
  color: var(--foreground);
  outline: none;
  font-family: inherit;
}

.inline-create-input:focus {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 20%, transparent);
}

/* Delete Confirmation Dialog */
.delete-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.delete-dialog {
  background: var(--card);
  border-radius: var(--radius-lg);
  max-width: 420px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  animation: slideUp 0.3s ease;
  overflow: hidden;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.delete-dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.delete-dialog-icon {
  color: var(--destructive);
  flex-shrink: 0;
}

.delete-dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--foreground);
}

.delete-dialog-body {
  padding: 20px 24px;
}

.delete-dialog-body p {
  margin: 0;
  color: var(--foreground);
  line-height: 1.6;
  font-size: 14px;
}

.delete-dialog-body p:not(:last-child) {
  margin-bottom: 8px;
}

.delete-dialog-body strong {
  font-weight: 600;
  color: var(--foreground);
}

.delete-warning {
  color: var(--muted-foreground);
  font-size: 13px;
}

/* Move Dialog Styles */
.move-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20000;
  animation: fadeIn 0.2s ease;
}

.move-dialog {
  background: var(--card);
  border-radius: var(--radius-lg);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  animation: slideUp 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.move-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.move-dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--foreground);
}

.close-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-1);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--accent);
  color: var(--foreground);
}

.move-dialog-body {
  padding: 20px 24px;
  flex: 1;
  overflow-y: auto;
}

.move-source {
  margin: 0 0 12px 0;
  color: var(--foreground);
  font-size: 14px;
}

.move-source strong {
  font-weight: 600;
  color: var(--primary);
}

.move-label {
  margin: 16px 0 8px 0;
  color: var(--muted-foreground);
  font-size: 13px;
}

.move-tree-container {
  margin-top: var(--space-3);
}

.move-dialog-actions {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  justify-content: flex-end;
  background: var(--muted);
}

.dialog-btn {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  font-family: inherit;
}

.dialog-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cancel-dialog-btn {
  background: var(--background);
  color: var(--foreground);
}

.cancel-dialog-btn:hover:not(:disabled) {
  background: var(--accent);
}

.confirm-dialog-btn {
  background: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}

.confirm-dialog-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.delete-dialog-actions {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  justify-content: flex-end;
  background: var(--muted);
}

.delete-dialog-btn {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  font-family: inherit;
  min-width: 80px;
}

.delete-dialog-btn.cancel-btn {
  background: var(--background);
  color: var(--foreground);
}

.delete-dialog-btn.cancel-btn:hover {
  background: var(--accent);
}

.delete-dialog-btn.confirm-btn {
  background: var(--destructive);
  color: var(--destructive-foreground);
  border-color: var(--destructive);
}

.delete-dialog-btn.confirm-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}
</style>


