<template>
  <div class="move-destination-tree">
    <!-- Breadcrumb navigation -->
    <div class="breadcrumb" v-if="currentDirectory !== projectPath">
      <button class="breadcrumb-btn" @click="navigateToParent">
        <ChevronLeft :size="14" />
        <span>Back</span>
      </button>
      <div class="breadcrumb-path">{{ getRelativePath(currentDirectory) }}</div>
    </div>
    
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="tree-list">
      <!-- Subdirectories (click to navigate into) -->
      <div 
        v-for="dir in subdirectories" 
        :key="dir.path" 
        class="tree-item tree-item-navigable"
        @click="navigateToDirectory(dir.path)"
      >
        <FolderOpen :size="16" />
        <span>{{ dir.name }}</span>
        <ChevronRight :size="14" class="navigate-icon" />
      </div>
      
      <!-- Files (for reference, not selectable) -->
      <div 
        v-for="file in files" 
        :key="file.path" 
        class="tree-item tree-item-file"
      >
        <File :size="16" />
        <span>{{ file.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { FolderOpen, File, ChevronLeft, ChevronRight } from 'lucide-vue-next';

const props = defineProps({
  projectPath: {
    type: String,
    required: true,
  },
  currentPath: {
    type: String,
    required: true,
  },
  selectedPath: {
    type: String,
    default: null,
  },
});

const emit = defineEmits(['path-selected']);

const loading = ref(true);
const currentDirectory = ref(props.projectPath);
const subdirectories = ref([]);
const files = ref([]);

const getProjectName = () => {
  if (!props.projectPath) return 'Project Root';
  const lastSlash = Math.max(props.projectPath.lastIndexOf('/'), props.projectPath.lastIndexOf('\\'));
  return lastSlash >= 0 ? props.projectPath.substring(lastSlash + 1) : props.projectPath;
};

const getDirectoryName = (path) => {
  const lastSlash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
  return lastSlash >= 0 ? path.substring(lastSlash + 1) : path;
};

const getRelativePath = (path) => {
  if (path === props.projectPath) return getProjectName();
  const relative = path.replace(props.projectPath, '').replace(/^[\/\\]/, '');
  return relative || getProjectName();
};

const selectPath = (path) => {
  if (!path) {
    return;
  }
  
  // Don't allow selecting the current path
  if (path === props.currentPath) {
    return;
  }
  
  // Don't allow selecting a directory that contains the current path (for folders)
  const normalizedCurrent = props.currentPath.replace(/\\/g, '/');
  const normalizedSelected = path.replace(/\\/g, '/');
  if (normalizedSelected.startsWith(normalizedCurrent + '/')) {
    return;
  }
  
  emit('path-selected', path);
};

const navigateToDirectory = (path) => {
  currentDirectory.value = path;
  // Automatically select this directory when navigating into it
  selectPath(path);
  loadDirectory(path);
};

const navigateToParent = () => {
  const lastSlash = Math.max(currentDirectory.value.lastIndexOf('/'), currentDirectory.value.lastIndexOf('\\'));
  let parentPath;
  if (lastSlash >= 0) {
    parentPath = currentDirectory.value.substring(0, lastSlash);
    // Don't go above project root
    if (parentPath.length < props.projectPath.length) {
      parentPath = props.projectPath;
    }
  } else {
    parentPath = props.projectPath;
  }
  
  currentDirectory.value = parentPath;
  // Automatically select the parent directory when navigating back
  selectPath(parentPath);
  loadDirectory(parentPath);
};

const loadDirectory = async (dirPath) => {
  if (!dirPath || !window.electronAPI?.readDirectory) {
    loading.value = false;
    return;
  }
  
  loading.value = true;
  
  try {
    const entries = await window.electronAPI.readDirectory(dirPath);
    const dirs = [];
    const fileList = [];
    
    for (const entry of entries) {
      // Don't include the current path or its children
      if (entry.path === props.currentPath) {
        continue;
      }
      
      const normalizedCurrent = props.currentPath.replace(/\\/g, '/');
      const normalizedEntry = entry.path.replace(/\\/g, '/');
      if (normalizedEntry.startsWith(normalizedCurrent + '/')) {
        continue;
      }
      
      if (entry.isDirectory) {
        dirs.push({
          path: entry.path,
          name: entry.name,
        });
      } else {
        fileList.push({
          path: entry.path,
          name: entry.name,
        });
      }
    }
    
    subdirectories.value = dirs.sort((a, b) => a.name.localeCompare(b.name));
    files.value = fileList.sort((a, b) => a.name.localeCompare(b.name));
  } catch (error) {
    console.error('Error loading directory:', error);
    subdirectories.value = [];
    files.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  // Automatically select the project root when first loading
  selectPath(currentDirectory.value);
  loadDirectory(currentDirectory.value);
});

// Watch for projectPath changes
watch(() => props.projectPath, (newPath) => {
  if (newPath) {
    currentDirectory.value = newPath;
    loadDirectory(newPath);
  }
});
</script>

<style scoped>
.move-destination-tree {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--background);
  display: flex;
  flex-direction: column;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border);
  background: var(--muted);
  flex-shrink: 0;
}

.breadcrumb-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--background);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
  color: var(--foreground);
  transition: all 0.15s;
}

.breadcrumb-btn:hover {
  background: var(--accent);
}

.breadcrumb-path {
  flex: 1;
  font-size: 12px;
  color: var(--muted-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading {
  padding: var(--space-4);
  text-align: center;
  color: var(--muted-foreground);
  font-size: 13px;
}

.tree-list {
  padding: var(--space-2);
  flex: 1;
  overflow-y: auto;
}

.tree-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  transition: background 0.15s, color 0.15s;
  font-size: 13px;
  color: var(--foreground);
  user-select: none;
  -webkit-user-select: none;
}

.tree-item-selectable {
  cursor: pointer;
}

.tree-item-selectable:hover:not(.is-selected) {
  background: var(--accent);
}

.tree-item-selectable.is-selected {
  background: var(--primary) !important;
  color: var(--primary-foreground) !important;
}

.tree-item-navigable {
  cursor: pointer;
}

.tree-item-navigable:hover {
  background: var(--accent);
}

.tree-item-file {
  opacity: 0.6;
  cursor: default;
}

.navigate-icon {
  margin-left: auto;
  color: var(--muted-foreground);
}

.tree-item-navigable:hover .navigate-icon {
  color: var(--foreground);
}

.tree-item svg:first-child {
  flex-shrink: 0;
  color: var(--muted-foreground);
  transition: color 0.15s;
}

.tree-item-navigable:hover svg:first-child {
  color: var(--foreground);
}
</style>

