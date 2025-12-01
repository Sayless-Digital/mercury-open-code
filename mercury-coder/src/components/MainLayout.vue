<template>
  <div class="app-container" :class="{ resizing: isResizing }" :data-resize-type="resizeType === 'vertical' ? 'vertical' : 'horizontal'">
    <TitleBar />
    <div class="main-content">
      <!-- Left Column (swappable with any panel) -->
      <div 
        class="left-column" 
        :style="{ width: leftColumnWidth + 'px' }"
        :class="{ 'dragging': isDragging === layoutOrder.left, 'drag-over': dragOver === layoutOrder.left }"
        @mousedown="handleMouseDown"
        @dragstart="(e) => handleDragStart(e, layoutOrder.left)"
        @dragend="handleDragEnd"
        @dragover.prevent="(e) => handleDragOver(e, layoutOrder.left)"
        @dragleave="handleDragLeave"
        @drop="(e) => handleDrop(e, layoutOrder.left)"
        draggable="true"
      >
        <FileManager 
          v-if="layoutOrder.left === 'file-manager'"
          class="file-manager" 
          :project-path="projectStore.currentProject?.path"
          :active-file-path="projectStore.activeFile"
          @file-selected="handleFileSelected"
        />
        <ChatPanel v-else-if="layoutOrder.left === 'agent'" />
        <div v-else-if="layoutOrder.left === 'editor'" class="editor-wrapper-in-column">
          <div class="editor-header" v-if="projectStore.openFiles.length > 0">
            <div 
              v-for="file in projectStore.openFiles" 
              :key="file"
              class="tab"
              :class="{ active: file === projectStore.activeFile }"
              @click="projectStore.setActiveFile(file)"
            >
              <component :is="getFileIcon(file)" class="tab-icon" :size="12" />
              <span class="tab-label">{{ getFileName(file) }}</span>
              <button 
                class="tab-close"
                @click.stop="projectStore.closeFile(file)"
              >
                <X :size="12" />
              </button>
            </div>
          </div>
          <div class="editor-header" v-else>
            <div class="empty-header-placeholder"></div>
          </div>
          <CodeEditor 
            class="code-editor" 
            :file-path="projectStore.activeFile"
            v-if="projectStore.activeFile"
          />
          <div v-else class="empty-editor">
            <div class="empty-editor-content">
              <div class="app-logo">
                <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                  <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="6"/>
                  <circle cx="40" cy="40" r="14" stroke="currentColor" stroke-width="6"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="layoutOrder.left === 'terminal'" class="terminal-wrapper-in-column" :style="{ height: '100%' }">
          <Terminal 
            class="terminal" 
            :cwd="projectStore.currentProject?.path"
          />
        </div>
      </div>
      
      <!-- Resize handle between left and center -->
      <div 
        class="resize-handle resize-handle-left"
        @mousedown="(e) => startResize('left', e)"
        @dblclick="resetLeftColumn"
      ></div>
      
      <!-- Center Column (swappable with any panel) -->
      <div 
        class="assistant-column"
        :class="{ 'dragging': isDragging === layoutOrder.center, 'drag-over': dragOver === layoutOrder.center }"
        @mousedown="handleMouseDown"
        @dragstart="(e) => handleDragStart(e, layoutOrder.center)"
        @dragend="handleDragEnd"
        @dragover.prevent="(e) => handleDragOver(e, layoutOrder.center)"
        @dragleave="handleDragLeave"
        @drop="(e) => handleDrop(e, layoutOrder.center)"
        draggable="true"
      >
        <FileManager 
          v-if="layoutOrder.center === 'file-manager'"
          class="file-manager" 
          :project-path="projectStore.currentProject?.path"
          :active-file-path="projectStore.activeFile"
          @file-selected="handleFileSelected"
        />
        <ChatPanel v-else-if="layoutOrder.center === 'agent'" />
        <div v-else-if="layoutOrder.center === 'editor'" class="editor-wrapper-in-column">
          <div class="editor-header" v-if="projectStore.openFiles.length > 0">
            <div 
              v-for="file in projectStore.openFiles" 
              :key="file"
              class="tab"
              :class="{ active: file === projectStore.activeFile }"
              @click="projectStore.setActiveFile(file)"
            >
              <component :is="getFileIcon(file)" class="tab-icon" :size="12" />
              <span class="tab-label">{{ getFileName(file) }}</span>
              <button 
                class="tab-close"
                @click.stop="projectStore.closeFile(file)"
              >
                <X :size="12" />
              </button>
            </div>
          </div>
          <div class="editor-header" v-else>
            <div class="empty-header-placeholder"></div>
          </div>
          <CodeEditor 
            class="code-editor" 
            :file-path="projectStore.activeFile"
            v-if="projectStore.activeFile"
          />
          <div v-else class="empty-editor">
            <div class="empty-editor-content">
              <div class="app-logo">
                <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                  <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="6"/>
                  <circle cx="40" cy="40" r="14" stroke="currentColor" stroke-width="6"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="layoutOrder.center === 'terminal'" class="terminal-wrapper-in-column" :style="{ height: '100%' }">
          <Terminal 
            class="terminal" 
            :cwd="projectStore.currentProject?.path"
          />
        </div>
      </div>
      
      <!-- Resize handle between center and right -->
      <div 
        class="resize-handle resize-handle-right"
        @mousedown="(e) => startResize('right', e)"
        @dblclick="resetRightColumn"
      ></div>
      
      <!-- Right: Editor + Terminal (stacked) -->
      <div class="editor-terminal-container" :style="{ width: rightColumnWidth + 'px' }">
        <!-- Editor/Terminal/FileManager/Agent (swappable) -->
        <div 
          v-if="layoutOrder.editor === 'editor'"
          class="editor-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.editor, 'drag-over': dragOver === layoutOrder.editor }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.editor)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.editor)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.editor)"
          draggable="true"
        >
          <div class="editor-header" v-if="projectStore.openFiles.length > 0">
            <div 
              v-for="file in projectStore.openFiles" 
              :key="file"
              class="tab"
              :class="{ active: file === projectStore.activeFile }"
              @click="projectStore.setActiveFile(file)"
            >
              <component :is="getFileIcon(file)" class="tab-icon" :size="12" />
              <span class="tab-label">{{ getFileName(file) }}</span>
              <button 
                class="tab-close"
                @click.stop="projectStore.closeFile(file)"
              >
                <X :size="12" />
              </button>
            </div>
          </div>
          <div class="editor-header" v-else>
            <div class="empty-header-placeholder"></div>
          </div>
          <CodeEditor 
            class="code-editor" 
            :file-path="projectStore.activeFile"
            v-if="projectStore.activeFile"
          />
          <div v-else class="empty-editor">
            <div class="empty-editor-content">
              <div class="app-logo">
                <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                  <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="6"/>
                  <circle cx="40" cy="40" r="14" stroke="currentColor" stroke-width="6"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
        
        <div 
          v-else-if="layoutOrder.editor === 'terminal'"
          class="editor-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.editor, 'drag-over': dragOver === layoutOrder.editor }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.editor)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.editor)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.editor)"
          draggable="true"
        >
          <Terminal 
            class="terminal" 
            :cwd="projectStore.currentProject?.path"
          />
        </div>
        <div 
          v-else-if="layoutOrder.editor === 'file-manager'"
          class="editor-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.editor, 'drag-over': dragOver === layoutOrder.editor }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.editor)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.editor)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.editor)"
          draggable="true"
        >
          <FileManager 
            class="file-manager" 
            :project-path="projectStore.currentProject?.path"
            :active-file-path="projectStore.activeFile"
            @file-selected="handleFileSelected"
          />
        </div>
        <div 
          v-else-if="layoutOrder.editor === 'agent'"
          class="editor-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.editor, 'drag-over': dragOver === layoutOrder.editor }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.editor)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.editor)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.editor)"
          draggable="true"
        >
          <ChatPanel />
        </div>
        
        <!-- Resize handle between editor and terminal -->
        <div 
          class="resize-handle-vertical"
          @mousedown="(e) => startResize('vertical', e)"
          @dblclick="resetTerminalHeight"
        ></div>
        
        <div 
          v-if="layoutOrder.terminal === 'editor'"
          class="terminal-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.terminal, 'drag-over': dragOver === layoutOrder.terminal }"
          :style="{ height: terminalHeight + 'px', flexShrink: 0 }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.terminal)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.terminal)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.terminal)"
          draggable="true"
        >
        <div class="editor-header" v-if="projectStore.openFiles.length > 0">
          <div 
            v-for="file in projectStore.openFiles" 
            :key="file"
            class="tab"
            :class="{ active: file === projectStore.activeFile }"
            @click="projectStore.setActiveFile(file)"
          >
            <span>{{ getFileName(file) }}</span>
            <button 
              class="tab-close"
              @click.stop="projectStore.closeFile(file)"
            >
              <X :size="14" />
            </button>
          </div>
        </div>
        <div class="editor-header" v-else>
          <div class="empty-header-placeholder"></div>
        </div>
        <CodeEditor 
          class="code-editor" 
          :file-path="projectStore.activeFile"
          v-if="projectStore.activeFile"
        />
        <div v-else class="empty-editor">
          <div class="empty-editor-content">
            <div class="app-logo">
              <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="6"/>
                <circle cx="40" cy="40" r="14" stroke="currentColor" stroke-width="6"/>
              </svg>
            </div>
          </div>
        </div>
        </div>
        
        <div 
          v-else-if="layoutOrder.terminal === 'terminal'"
          class="terminal-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.terminal, 'drag-over': dragOver === layoutOrder.terminal }"
          :style="{ height: terminalHeight + 'px', flexShrink: 0 }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.terminal)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.terminal)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.terminal)"
          draggable="true"
        >
        <Terminal 
          class="terminal" 
          :cwd="projectStore.currentProject?.path"
        />
        </div>
        <div 
          v-else-if="layoutOrder.terminal === 'file-manager'"
          class="file-manager-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.terminal, 'drag-over': dragOver === layoutOrder.terminal }"
          :style="{ height: terminalHeight + 'px', flexShrink: 0 }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.terminal)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.terminal)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.terminal)"
          draggable="true"
        >
          <FileManager 
            class="file-manager" 
            :project-path="projectStore.currentProject?.path"
            :active-file-path="projectStore.activeFile"
            @file-selected="handleFileSelected"
          />
        </div>
        <div 
          v-else-if="layoutOrder.terminal === 'agent'"
          class="agent-wrapper"
          :class="{ 'dragging': isDragging === layoutOrder.terminal, 'drag-over': dragOver === layoutOrder.terminal }"
          :style="{ height: terminalHeight + 'px', flexShrink: 0 }"
          @mousedown="handleMouseDown"
          @dragstart="(e) => handleDragStart(e, layoutOrder.terminal)"
          @dragend="handleDragEnd"
          @dragover.prevent="(e) => handleDragOver(e, layoutOrder.terminal)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, layoutOrder.terminal)"
          draggable="true"
        >
          <ChatPanel />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, ref, onMounted, onUnmounted, provide } from 'vue';
import { 
  X, File, FileText, FileCode, FileJson, FileCode2, 
  Code, Image as ImageIcon 
} from 'lucide-vue-next';
import TitleBar from './TitleBar.vue';
import FileManager from './FileManager.vue';
import CodeEditor from './CodeEditor.vue';
import Terminal from './Terminal.vue';
import ChatPanel from './ChatPanel.vue';
import { useProjectStore } from '@/stores/project';
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts';

const projectStore = useProjectStore();

// Resize functionality
const DEFAULT_LEFT_WIDTH = 360;
const DEFAULT_RIGHT_WIDTH = 360;
const DEFAULT_TERMINAL_HEIGHT = 300;

const leftColumnWidth = ref(DEFAULT_LEFT_WIDTH);
const rightColumnWidth = ref(DEFAULT_RIGHT_WIDTH);
const terminalHeight = ref(DEFAULT_TERMINAL_HEIGHT);
const isResizing = ref(false);
const resizeType = ref(null);
const startX = ref(0);
const startY = ref(0);
const startLeftWidth = ref(0);
const startRightWidth = ref(0);
const startTerminalHeight = ref(0);

// Drag and drop functionality
const isDragging = ref(null);
const dragOver = ref(null);
const lastMouseDownTarget = ref(null);
const layoutOrder = ref({
  left: 'file-manager',
  center: 'agent',
  editor: 'editor',
  terminal: 'terminal'
});

// Track mousedown to know what element was actually clicked
function handleMouseDown(e) {
  lastMouseDownTarget.value = e.target;
}

function handleDragStart(e, panelType) {
  // Only allow dragging from header areas
  const headerSelectors = '.chat-header, .editor-header, .terminal-header, .file-manager-toolbar';
  const clickedHeader = lastMouseDownTarget.value?.closest(headerSelectors);
  
  if (!clickedHeader) {
    // Not clicking on a header - cancel the drag
    e.preventDefault();
    return;
  }
  
  isDragging.value = panelType;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', panelType);
  
  // Use a transparent 1x1 pixel image to hide the default drag preview
  const img = new Image();
  img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
  e.dataTransfer.setDragImage(img, 0, 0);
}

function handleDragOver(e, panelType) {
  if (isDragging.value && isDragging.value !== panelType) {
    dragOver.value = panelType;
  }
}

function handleDragLeave() {
  dragOver.value = null;
}

function handleDragEnd() {
  isDragging.value = null;
  dragOver.value = null;
}

function handleDrop(e, targetType) {
  e.preventDefault();
  const sourceType = isDragging.value;
  
  if (!sourceType || sourceType === targetType) {
    dragOver.value = null;
    return;
  }
  
  // Find where source and target currently are
  let sourcePosition = null;
  let targetPosition = null;
  
  if (layoutOrder.value.left === sourceType) sourcePosition = 'left';
  else if (layoutOrder.value.center === sourceType) sourcePosition = 'center';
  else if (layoutOrder.value.editor === sourceType) sourcePosition = 'editor';
  else if (layoutOrder.value.terminal === sourceType) sourcePosition = 'terminal';
  
  if (layoutOrder.value.left === targetType) targetPosition = 'left';
  else if (layoutOrder.value.center === targetType) targetPosition = 'center';
  else if (layoutOrder.value.editor === targetType) targetPosition = 'editor';
  else if (layoutOrder.value.terminal === targetType) targetPosition = 'terminal';
  
  // Swap the panels
  if (sourcePosition && targetPosition) {
    // Get what's currently in the target position
    const targetContent = layoutOrder.value[targetPosition];
    
    // Move source to target position
    layoutOrder.value[targetPosition] = sourceType;
    
    // Move target to source position
    layoutOrder.value[sourcePosition] = targetContent;
  }
  
  dragOver.value = null;
  isDragging.value = null;
  
  // Save layout order to localStorage
  localStorage.setItem('mercury-layout-order', JSON.stringify(layoutOrder.value));
}

function resetLeftColumn() {
  leftColumnWidth.value = DEFAULT_LEFT_WIDTH;
}

function resetRightColumn() {
  rightColumnWidth.value = DEFAULT_RIGHT_WIDTH;
}

function resetTerminalHeight() {
  terminalHeight.value = DEFAULT_TERMINAL_HEIGHT;
}

function resetLayoutArrangement() {
  layoutOrder.value = {
    left: 'file-manager',
    center: 'agent',
    editor: 'editor',
    terminal: 'terminal'
  };
  localStorage.setItem('mercury-layout-order', JSON.stringify(layoutOrder.value));
}

// Provide reset function for TitleBar to use
provide('resetLayoutArrangement', resetLayoutArrangement);

function startResize(type, e) {
  e.preventDefault();
  e.stopPropagation();
  isResizing.value = true;
  resizeType.value = type;
  startX.value = e.clientX;
  startY.value = e.clientY;
  startLeftWidth.value = leftColumnWidth.value;
  startRightWidth.value = rightColumnWidth.value;
  startTerminalHeight.value = terminalHeight.value;
}

function handleMouseMove(e) {
  if (!isResizing.value) return;
  
  e.preventDefault();
  const deltaX = e.clientX - startX.value;
  const deltaY = e.clientY - startY.value;
  
  if (resizeType.value === 'left') {
    // Resize file manager column (left column)
    const newWidth = startLeftWidth.value + deltaX;
    if (newWidth >= 320 && newWidth <= 600) {
      leftColumnWidth.value = newWidth;
    }
  } else if (resizeType.value === 'right') {
    // Resize editor/terminal column (right column)
    const newWidth = startRightWidth.value - deltaX;
    if (newWidth >= 320 && newWidth <= 600) {
      rightColumnWidth.value = newWidth;
    }
  } else if (resizeType.value === 'vertical') {
    // Resize terminal height (vertical)
    const newHeight = startTerminalHeight.value - deltaY;
    if (newHeight >= 200 && newHeight <= 800) {
      terminalHeight.value = newHeight;
    }
  }
}

function handleMouseUp() {
  if (isResizing.value) {
    isResizing.value = false;
    resizeType.value = null;
  }
}

onMounted(() => {
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
  
  // Load saved widths and heights from localStorage
  const savedLeftWidth = localStorage.getItem('mercury-left-column-width');
  const savedRightWidth = localStorage.getItem('mercury-right-column-width');
  const savedTerminalHeight = localStorage.getItem('mercury-terminal-height');
  if (savedLeftWidth) leftColumnWidth.value = parseInt(savedLeftWidth);
  if (savedRightWidth) rightColumnWidth.value = parseInt(savedRightWidth);
  if (savedTerminalHeight) terminalHeight.value = parseInt(savedTerminalHeight);
  
  // Load saved layout order
  const savedLayoutOrder = localStorage.getItem('mercury-layout-order');
  if (savedLayoutOrder) {
    try {
      layoutOrder.value = JSON.parse(savedLayoutOrder);
    } catch (e) {
      console.error('Failed to parse layout order:', e);
    }
  }
});

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
});

// Save widths and height to localStorage when they change
watch([leftColumnWidth, rightColumnWidth, terminalHeight], ([left, right, height]) => {
  localStorage.setItem('mercury-left-column-width', left.toString());
  localStorage.setItem('mercury-right-column-width', right.toString());
  localStorage.setItem('mercury-terminal-height', height.toString());
});

// Initialize keyboard shortcuts
useKeyboardShortcuts();

// Debug: Log project changes
watch(() => projectStore.currentProject, (project) => {
  console.log('MainLayout: Project changed:', project);
  console.log('MainLayout: Project path:', project?.path);
  console.log('MainLayout: Full project object:', JSON.stringify(project, null, 2));
}, { immediate: true });

// Debug: Log project path prop changes
watch(() => projectStore.currentProject?.path, (path) => {
  console.log('MainLayout: Project path changed to:', path);
}, { immediate: true });

const handleFileSelected = (filePath) => {
  projectStore.setActiveFile(filePath);
};

const getFileName = (filePath) => {
  return filePath.split(/[/\\]/).pop();
};

const getFileIcon = (filePath) => {
  const fileName = getFileName(filePath);
  const lastDot = fileName.lastIndexOf('.');
  if (lastDot === -1 || lastDot === fileName.length - 1) {
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
};
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  background: var(--background);
  padding: var(--space-4);
  gap: 0;
}

.left-column {
  min-width: 320px;
  max-width: 600px;
  display: flex;
  flex-direction: column;
  margin: 0;
  overflow: hidden;
  flex-shrink: 0;
}

.file-manager {
  flex: 1;
  min-height: 0;
  background: var(--sidebar);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Light mode: slightly grey background for sidebar */
:not(.dark) .file-manager {
  background: var(--sidebar);
}

/* Dark mode: use original sidebar color */
.dark .file-manager {
  background: var(--sidebar);
}

.editor-terminal-container {
  min-width: 320px;
  max-width: 600px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin: 0;
  flex-shrink: 0;
}

.editor-header {
  display: flex;
  align-items: center;
  background: var(--muted);
  overflow-x: auto;
  overflow-y: hidden;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  height: 28px;
  min-height: 28px;
  margin: 0;
  gap: var(--space-2);
}

.tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) 2px var(--space-1) 5px;
  background: transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  border-radius: var(--radius-sm);
  height: 20px;
  color: var(--muted-foreground);
  font-size: 13px;
}

.tab-icon {
  flex-shrink: 0;
  color: var(--muted-foreground);
  opacity: 0.7;
  transition: all 0.2s;
}

.tab.active .tab-icon {
  color: var(--primary);
  opacity: 1;
}

.tab-label {
  font-size: 13px;
  line-height: 1;
}

.tab:hover {
  background: color-mix(in srgb, var(--muted) 50%, transparent 50%);
  color: var(--foreground);
}

.tab:hover .tab-icon {
  opacity: 0.9;
  color: var(--foreground);
}

.tab.active {
  background: var(--card);
  color: var(--foreground);
  font-weight: 500;
}

.tab-close {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-1);
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs);
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.tab:hover .tab-close {
  opacity: 1;
}

.tab-close:hover {
  background: var(--accent);
  color: var(--foreground);
}

.editor-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.editor-wrapper-in-column {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.terminal-wrapper-in-column {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-manager-wrapper {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.agent-wrapper {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.code-editor {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  margin: 0;
}

/* Light mode: slightly grey background for editor */
:not(.dark) .code-editor {
  background: var(--card);
}

/* Dark mode: use original card color */
.dark .code-editor {
  background: var(--card);
}

.empty-editor {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  margin: 0;
  background: var(--card);
  display: flex;
  flex-direction: column;
}

/* Light mode: slightly grey background for empty editor */
:not(.dark) .empty-editor {
  background: var(--card);
}

/* Dark mode: use original card color */
.dark .empty-editor {
  background: var(--card);
}

.empty-editor-content {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted-foreground);
}

.app-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.3;
}

.empty-header-placeholder {
  width: 100%;
  height: 100%;
}

.terminal-wrapper {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.terminal {
  width: 100%;
  height: 100%;
  resize: none;
  overflow: hidden;
  margin: 0;
  flex: 1;
  min-height: 0;
}

/* Light mode: slightly grey background for terminal */
:not(.dark) .terminal {
  background: var(--card);
}

/* Dark mode: use original card color */
.dark .terminal {
  background: var(--card);
}

.assistant-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  margin: 0;
  min-height: 0;
}

.resize-handle {
  width: 4px;
  background: transparent;
  cursor: col-resize;
  flex-shrink: 0;
  position: relative;
  transition: background-color 0.2s;
  z-index: 10;
  border-radius: var(--radius-full);
  margin: 0 var(--space-1);
}

.resize-handle:hover {
  background: var(--primary);
  opacity: 0.5;
  border-radius: var(--radius-full);
}

.resize-handle::before {
  content: '';
  position: absolute;
  left: -4px;
  right: -4px;
  top: 0;
  bottom: 0;
  cursor: col-resize;
}

.app-container.resizing {
  user-select: none;
}

.app-container.resizing[data-resize-type="horizontal"] {
  cursor: col-resize;
}

.app-container.resizing[data-resize-type="horizontal"] * {
  cursor: col-resize !important;
}

.app-container.resizing[data-resize-type="vertical"] {
  cursor: row-resize;
}

.app-container.resizing[data-resize-type="vertical"] * {
  cursor: row-resize !important;
}

.resize-handle-vertical {
  height: 4px;
  background: transparent;
  cursor: row-resize;
  flex-shrink: 0;
  position: relative;
  transition: background-color 0.2s;
  z-index: 10;
  border-radius: var(--radius-full);
  margin: var(--space-1) 0;
}

.resize-handle-vertical:hover {
  background: var(--primary);
  opacity: 0.5;
  border-radius: var(--radius-full);
}

.resize-handle-vertical::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -4px;
  bottom: -4px;
  cursor: row-resize;
}

.dragging {
  opacity: 0.5;
  cursor: grabbing !important;
}

.drag-over {
  border: 2px solid var(--primary) !important;
  background: color-mix(in srgb, var(--primary) 10%, transparent);
  border-radius: var(--radius-xl);
  box-sizing: border-box;
}

/* During active dragging, disable interactions on content */
.dragging *,
.dragging.terminal-wrapper .terminal,
.dragging.editor-wrapper .code-editor,
.dragging.editor-wrapper .empty-editor {
  pointer-events: none;
  user-select: none;
}

/* Drag handle cursor for headers only */
.editor-header {
  cursor: grab;
}

.editor-header:active {
  cursor: grabbing;
}

</style>


