<template>
  <div class="title-bar" :class="{ 'maximized': isMaximized }">
    <div class="title-bar-left">
      <div class="app-icon" @click="goToWelcome" title="Back to Welcome">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="7.5" stroke="currentColor" stroke-width="2.5"/>
          <circle cx="10" cy="10" r="3.5" stroke="currentColor" stroke-width="2.5"/>
        </svg>
      </div>
      <MenuBar :menus="menus" @menu-click="handleMenuClick" />
      <div class="title-bar-spacer"></div>
    </div>
    <div class="title-bar-right">
      <button class="title-bar-btn theme-toggle-btn" @click="toggleTheme" :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'">
        <Sun v-if="isDark" :size="14" />
        <Moon v-else :size="14" />
      </button>
      <button class="title-bar-btn" @click="minimize" title="Minimize">
        <Minus :size="14" />
      </button>
      <button class="title-bar-btn" @click="toggleMaximize" :title="isMaximized ? 'Restore' : 'Maximize'">
        <Maximize2 v-if="!isMaximized" :size="14" />
        <Minimize2 v-else :size="14" />
      </button>
      <button class="title-bar-btn close-btn" @click="close" title="Close">
        <X :size="14" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue';
import { 
  Minus, Maximize2, Minimize2, X, 
  FilePlus, FolderPlus, File, FolderOpen, Save, Settings, 
  XCircle, FolderX, Power,
  Undo2, Redo2, Scissors, Copy, Clipboard, Search, Replace, MousePointerClick,
  Command, FolderTree, Terminal, MessageSquare,
  Play, Bug, ListTodo,
  Home, BookOpen, Info,
  FileText, Edit, Eye, PlayCircle, HelpCircle,
  Sun, Moon, Brain, RotateCcw
} from 'lucide-vue-next';
import { useWindowControls } from '@/composables/useWindowControls';
import { useProjectStore } from '@/stores/project';
import { useMenuActions } from '@/composables/useMenuActions';
import { useTheme } from '@/composables/useTheme';
import MenuBar from './MenuBar.vue';

const { minimize, toggleMaximize, close, isMaximized } = useWindowControls();
const projectStore = useProjectStore();
const menuActions = useMenuActions();
const { isDark, toggleTheme } = useTheme();

const goToWelcome = () => {
  projectStore.setCurrentProject(null);
  projectStore.activeFile = null;
  projectStore.openFiles = [];
  projectStore.showSettings = false;
};

const openSettings = () => {
  projectStore.showSettings = true;
};

const openMemoryBrowser = () => {
  projectStore.showMemoryBrowser = true;
};

// Try to inject reset layout function (may not be available if not in MainLayout)
const resetLayoutArrangement = inject('resetLayoutArrangement', null);

const menus = computed(() => [
  {
    label: 'File',
    icon: FileText,
    items: [
      { label: 'New File', icon: FilePlus, shortcut: 'Ctrl+N', action: menuActions.createNewFile },
      { label: 'New Folder', icon: FolderPlus, action: menuActions.createNewFolder },
      { separator: true },
      { label: 'Open File...', icon: File, shortcut: 'Ctrl+O', action: menuActions.openFile },
      { label: 'Open Folder...', icon: FolderOpen, shortcut: 'Ctrl+K Ctrl+O', action: menuActions.openFolder },
      { separator: true },
      { label: 'Save', icon: Save, shortcut: 'Ctrl+S', action: menuActions.saveFile },
      { label: 'Save As...', icon: Save, shortcut: 'Ctrl+Shift+S', action: menuActions.saveFileAs },
      { separator: true },
      { 
        label: 'Preferences', 
        icon: Settings,
        submenu: [
          { label: 'Settings...', icon: Settings, shortcut: 'Ctrl+,', action: openSettings },
          { label: 'Manage Memory...', icon: Brain, action: openMemoryBrowser },
        ]
      },
      { separator: true },
      { label: 'Close Editor', icon: XCircle, shortcut: 'Ctrl+W', action: menuActions.closeCurrentFile },
      { label: 'Close Folder', icon: FolderX, action: menuActions.closeProject },
      { separator: true },
      { label: 'Exit', icon: Power, shortcut: 'Ctrl+Q', action: close },
    ]
  },
  {
    label: 'Edit',
    icon: Edit,
    items: [
      { label: 'Undo', icon: Undo2, shortcut: 'Ctrl+Z', action: menuActions.undo },
      { label: 'Redo', icon: Redo2, shortcut: 'Ctrl+Y', action: menuActions.redo },
      { separator: true },
      { label: 'Cut', icon: Scissors, shortcut: 'Ctrl+X', action: menuActions.cut },
      { label: 'Copy', icon: Copy, shortcut: 'Ctrl+C', action: menuActions.copy },
      { label: 'Paste', icon: Clipboard, shortcut: 'Ctrl+V', action: menuActions.paste },
      { separator: true },
      { label: 'Find', icon: Search, shortcut: 'Ctrl+F', action: menuActions.findInEditor },
      { label: 'Replace', icon: Replace, shortcut: 'Ctrl+H', action: menuActions.replaceInEditor },
      { separator: true },
      { label: 'Select All', icon: MousePointerClick, shortcut: 'Ctrl+A', action: menuActions.selectAll },
    ]
  },
  {
    label: 'View',
    icon: Eye,
    items: [
      { label: 'Command Palette...', icon: Command, shortcut: 'Ctrl+Shift+P', action: () => alert('Command Palette coming soon!') },
      { separator: true },
      { label: 'Explorer', icon: FolderTree, shortcut: 'Ctrl+Shift+E', action: () => console.log('Toggle Explorer') },
      { label: 'Search', icon: Search, shortcut: 'Ctrl+Shift+F', action: () => alert('File Search coming soon!') },
      { separator: true },
      { label: 'Terminal', icon: Terminal, shortcut: 'Ctrl+`', action: () => console.log('Toggle Terminal') },
      { label: 'AI Chat', icon: MessageSquare, action: () => console.log('Toggle AI Chat') },
      { separator: true },
      { label: 'Reset Panel Arrangement', icon: RotateCcw, action: () => {
        if (resetLayoutArrangement) {
          resetLayoutArrangement();
        }
      } },
    ]
  },
  {
    label: 'Run',
    icon: PlayCircle,
    items: [
      { label: 'Run File', icon: Play, shortcut: 'F5', action: () => alert('Run File feature coming soon!') },
      { label: 'Debug', icon: Bug, shortcut: 'F9', action: () => alert('Debug feature coming soon!') },
      { separator: true },
      { label: 'Run Task...', icon: ListTodo, shortcut: 'Ctrl+Shift+B', action: () => alert('Run Task feature coming soon!') },
    ]
  },
  {
    label: 'Help',
    icon: HelpCircle,
    items: [
      { label: 'Welcome', icon: Home, action: () => {
        if (projectStore.currentProject) {
          projectStore.setCurrentProject(null);
        }
      }},
      { label: 'Documentation', icon: BookOpen, action: () => window.open('https://github.com/your-repo/docs', '_blank') },
      { separator: true },
      { label: 'About', icon: Info, action: () => alert('Mercury Coder\nAI-Powered Code Editor\nVersion 1.0.0') },
    ]
  }
]);

const handleMenuClick = (item) => {
  if (item.action) {
    item.action();
  }
};
</script>

<style scoped>
.title-bar {
  -webkit-app-region: drag;
  height: var(--header-sm);
  background: var(--muted);
  color: var(--foreground);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-5);
  user-select: none;
  z-index: 1000;
}

.title-bar-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
  -webkit-app-region: no-drag;
}

.app-icon {
  width: var(--icon-xl);
  height: var(--icon-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ring);
  flex-shrink: 0;
  -webkit-app-region: no-drag;
  cursor: pointer;
  transition: opacity 0.2s;
}

.app-icon:hover {
  opacity: 0.7;
}

.title-bar-spacer {
  flex: 1;
  -webkit-app-region: drag;
  height: 100%;
}

.title-bar-right {
  -webkit-app-region: no-drag;
  display: flex;
  gap: var(--space-6);
  flex: 0 0 auto;
  align-items: center;
  padding-right: var(--space-2);
}

.title-bar-btn {
  -webkit-app-region: no-drag;
  width: var(--size-md);
  height: var(--size-md);
  min-width: var(--size-md);
  min-height: var(--size-md);
  max-width: var(--size-md);
  max-height: var(--size-md);
  border: none;
  background: var(--muted);
  color: var(--foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  transition: background-color 0.2s;
  flex-shrink: 0;
  padding: 0;
  box-sizing: border-box;
}

.title-bar-btn:hover {
  background: var(--accent);
}

.close-btn:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.theme-toggle-btn {
  margin-right: var(--space-2);
}

</style>