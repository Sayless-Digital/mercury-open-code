<template>
  <div ref="editorContainer" class="code-editor"></div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import * as monaco from 'monaco-editor';
import { useProjectStore } from '@/stores/project';
import { useEditorStore } from '@/stores/editor';
import { useTheme } from '@/composables/useTheme';

const props = defineProps({
  filePath: {
    type: String,
    default: null,
  },
});

const projectStore = useProjectStore();
const editorStore = useEditorStore();
const { isDark } = useTheme();
const editorContainer = ref(null);
let editor = null;
let currentContent = '';

const getEditorBackground = () => {
  const root = document.documentElement;
  const styles = getComputedStyle(root);
  return styles.getPropertyValue('--sidebar').trim() || (root.classList.contains('dark') ? '#191919' : '#fcfcfc');
};

const initEditor = () => {
  if (!editorContainer.value) return;

  const bgColor = getEditorBackground();
  
  // Define custom theme with sidebar background
  monaco.editor.defineTheme('mercury-coder', {
    base: isDark.value ? 'vs-dark' : 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': bgColor,
    },
  });

  editor = monaco.editor.create(editorContainer.value, {
    value: '',
    language: 'javascript',
    theme: 'mercury-coder',
    automaticLayout: true,
    minimap: { enabled: true },
    fontSize: 14,
    lineNumbers: 'on',
    roundedSelection: false,
    scrollBeyondLastLine: false,
    readOnly: false,
    cursorStyle: 'line',
    wordWrap: 'on',
    scrollbar: {
      vertical: 'auto',
      horizontal: 'auto',
      verticalScrollbarSize: 8,
      horizontalScrollbarSize: 8,
      useShadows: false,
      alwaysConsumeMouseWheel: true,
      verticalHasArrows: false,
      horizontalHasArrows: false,
    },
  });

  // Expose editor instance to store
  editorStore.setEditorInstance(editor);

  // Save file on content change (debounced)
  let saveTimeout;
  editor.onDidChangeModelContent(() => {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      saveFile();
    }, 1000);
  });
};

const detectLanguage = (filePath) => {
  const ext = filePath.split('.').pop().toLowerCase();
  const langMap = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    java: 'java',
    c: 'c',
    cpp: 'cpp',
    html: 'html',
    css: 'css',
    scss: 'scss',
    json: 'json',
    xml: 'xml',
    yaml: 'yaml',
    yml: 'yaml',
    md: 'markdown',
    vue: 'html',
    sh: 'shell',
    bash: 'shell',
  };
  return langMap[ext] || 'plaintext';
};

const loadFile = async () => {
  if (!props.filePath || !editor) return;

  try {
    const content = await window.electronAPI.readFile(props.filePath);
    currentContent = content;
    const language = detectLanguage(props.filePath);
    
    editor.setValue(content);
    monaco.editor.setModelLanguage(editor.getModel(), language);
  } catch (error) {
    console.error('Failed to load file:', error);
    editor.setValue(`// Error loading file: ${error.message}`);
  }
};

const saveFile = async () => {
  if (!props.filePath || !editor) return;

  const content = editor.getValue();
  if (content === currentContent) return;

  try {
    await window.electronAPI.writeFile(props.filePath, content);
    currentContent = content;
    
    // Add to recent files
    if (projectStore.currentProject) {
      await window.electronAPI.addRecentFile(
        projectStore.currentProject.id,
        props.filePath
      );
    }
  } catch (error) {
    console.error('Failed to save file:', error);
  }
};

watch(() => props.filePath, loadFile, { immediate: true });

// Watch for theme changes and update editor theme
watch(isDark, (dark) => {
  if (editor) {
    const bgColor = getEditorBackground();
    monaco.editor.defineTheme('mercury-coder', {
      base: dark ? 'vs-dark' : 'vs',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': bgColor,
      },
    });
    monaco.editor.setTheme('mercury-coder');
  }
});

onMounted(() => {
  initEditor();
  if (props.filePath) {
    loadFile();
  }
});

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose();
  }
});
</script>

<style scoped>
.code-editor {
  width: 100%;
  height: 100%;
  border-radius: 0 0 12px 12px;
  overflow: hidden;
  position: relative;
  padding-right: 0;
}

.code-editor :deep(.monaco-editor .overflow-guard) {
  border-radius: 0 0 12px 12px !important;
  overflow: hidden !important;
}

.code-editor :deep(.monaco-editor .monaco-scrollable-element > .shadow) {
  display: none !important;
}

.code-editor :deep(.monaco-editor .view-overlays) {
  border-radius: 0 0 12px 12px !important;
}

.code-editor :deep(.monaco-editor .view-lines) {
  border-radius: 0 0 12px 12px !important;
}

.code-editor :deep(.monaco-editor .current-line) {
  border-radius: 0 0 12px 12px !important;
}

.code-editor :deep(.monaco-editor) {
  border-radius: 0 0 12px 12px !important;
  overflow: hidden !important;
}

.code-editor :deep(.monaco-editor .monaco-editor-background) {
  border-radius: 0 0 12px 12px !important;
}

.code-editor :deep(.monaco-editor .margin) {
  border-radius: 0 0 0 12px !important;
}

.code-editor :deep(.monaco-scrollable-element) {
  overflow: hidden !important;
  border-radius: 0 0 12px 12px !important;
  padding-right: 0 !important;
  margin-right: 0 !important;
}

.code-editor :deep(.monaco-editor .content) {
  border-radius: 0 0 12px 12px !important;
  overflow: hidden !important;
}

.code-editor :deep(.monaco-editor .lines-content) {
  border-radius: 0 0 12px 12px !important;
}

/* Round minimap bottom right corner */
.code-editor :deep(.monaco-editor .minimap) {
  border-radius: 0 0 12px 0 !important;
  overflow: hidden !important;
}

.code-editor :deep(.monaco-editor .minimap .minimap-shadow-visible) {
  border-radius: 0 0 12px 0 !important;
}

.code-editor :deep(.monaco-editor .minimap .minimap-slider) {
  border-radius: 0 0 12px 0 !important;
}

.code-editor :deep(.monaco-editor .minimap .minimap-slider-mouseover) {
  border-radius: 0 0 12px 0 !important;
}

.code-editor :deep(.monaco-editor .minimap canvas) {
  border-radius: 0 0 12px 0 !important;
}

.code-editor :deep(.monaco-editor .minimap-slider) {
  border-radius: 0 0 12px 0 !important;
}

.code-editor :deep(.monaco-editor .minimap-decoration-layer) {
  border-radius: 0 0 12px 0 !important;
}

/* Hide scrollbar completely */
.code-editor :deep(.monaco-scrollable-element > .scrollbar) {
  display: none !important;
}

.code-editor :deep(.monaco-scrollable-element > .scrollbar.vertical) {
  display: none !important;
}

.code-editor :deep(.monaco-scrollable-element > .scrollbar.horizontal) {
  display: none !important;
}
</style>


