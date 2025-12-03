<template>
  <div class="file-tree-node">
    <div 
      class="node-item"
      :class="{ 
        'is-directory': file.isDirectory, 
        'is-file': file.isFile,
        'is-expanded': file.isDirectory && expanded,
        'is-active': isActive
      }"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      @click="handleClick"
      @contextmenu.prevent="handleContextMenu"
    >
      <!-- Inline rename input -->
      <div v-if="isRenaming" class="rename-input-wrapper">
        <input
          ref="renameInputRef"
          v-model="renameValue"
          type="text"
          class="rename-input"
          @keydown.enter.prevent="confirmRename"
          @keydown.escape="cancelRename"
          @blur="cancelRename"
        />
      </div>
      <template v-else>
        <!-- Dropdown arrow for directories -->
        <ChevronRight 
          v-if="file.isDirectory" 
          class="chevron-icon"
          :class="{ 'expanded': expanded }"
          :size="14"
        />
        <span v-else class="chevron-spacer"></span>
        
        <component :is="getIcon" class="node-icon" :size="16" />
        <span class="node-name">{{ file.name }}</span>
      </template>
    </div>
    
    <!-- Context Menu -->
    <div 
      v-if="contextMenuVisible"
      class="context-menu"
      :style="{ top: contextMenuY + 'px', left: contextMenuX + 'px' }"
      @click.stop
    >
      <button class="context-menu-item" @click="startRename">
        <Pencil :size="14" />
        <span>Rename</span>
      </button>
      <button class="context-menu-item context-menu-item-danger" @click="handleDelete">
        <Trash2 :size="14" />
        <span>Delete</span>
      </button>
    </div>
    
    <div v-if="file.isDirectory && expanded" class="node-children">
      <FileTreeNode
        v-for="child in children"
        :key="child.path"
        :file="child"
        :depth="depth + 1"
        :active-file-path="activeFilePath"
        @file-selected="$emit('file-selected', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { 
  Folder, FolderOpen, File, FileText, FileCode, FileJson, 
  FileImage, FileType, Code, FileCode2, Image as ImageIcon,
  ChevronRight, Pencil, Trash2
} from 'lucide-vue-next';

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
});

const emit = defineEmits(['file-selected']);

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

// Check if this file/folder is the active one
const isActive = computed(() => {
  return props.activeFilePath && props.file.path === props.activeFilePath;
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
  event.stopPropagation();
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
  nextTick(() => {
    if (renameInputRef.value) {
      renameInputRef.value.focus();
      // Select filename without extension for easier renaming
      const lastDot = renameValue.value.lastIndexOf('.');
      if (lastDot > 0) {
        renameInputRef.value.setSelectionRange(0, lastDot);
      } else {
        renameInputRef.value.select();
      }
    }
  });
};

const confirmRename = async () => {
  if (!renameValue.value.trim() || renameValue.value === props.file.name) {
    cancelRename();
    return;
  }
  
  // Construct new path by replacing the filename
  // Handle both forward and backward slashes for cross-platform compatibility
  const filePath = props.file.path;
  const isWindows = filePath.includes('\\');
  const separator = isWindows ? '\\' : '/';
  const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
  const dir = lastSlash >= 0 ? filePath.substring(0, lastSlash + 1) : '';
  const newPath = dir + renameValue.value.trim();
  
  if (!window.electronAPI?.renameFile) {
    alert('Rename functionality is not available');
    cancelRename();
    return;
  }
  
  try {
    const result = await window.electronAPI.renameFile(props.file.path, newPath);
    if (result.success) {
      isRenaming.value = false;
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
  renameValue.value = '';
};

const handleDelete = async () => {
  contextMenuVisible.value = false;
  
  const itemType = props.file.isDirectory ? 'folder' : 'file';
  const confirmed = confirm(`Are you sure you want to delete this ${itemType}?\n\n${props.file.name}\n\nThis action cannot be undone.`);
  
  if (!confirmed) {
    return;
  }
  
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

.node-item:hover {
  background: var(--accent);
}

.node-item.is-file {
  cursor: pointer;
}

.node-item.is-directory {
  font-weight: 500;
}

.node-item.is-active {
  background: var(--accent);
  color: var(--foreground);
  font-weight: 500;
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
}

.node-children {
  margin-left: 0;
}

.rename-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
}

.rename-input {
  flex: 1;
  padding: 2px 4px;
  border: 1px solid var(--primary);
  border-radius: 4px;
  background: var(--card);
  color: var(--foreground);
  font-size: 13px;
  font-family: inherit;
  outline: none;
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

.context-menu-item:hover {
  background: var(--accent);
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
</style>


