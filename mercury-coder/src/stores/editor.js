import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useEditorStore = defineStore('editor', () => {
  const editorInstance = ref(null);
  const isFindVisible = ref(false);
  const isReplaceVisible = ref(false);

  function setEditorInstance(editor) {
    editorInstance.value = editor;
  }

  function saveCurrentFile() {
    if (editorInstance.value) {
      // Trigger save through the editor's save mechanism
      // The CodeEditor component will handle the actual file write
      return editorInstance.value.getValue();
    }
    return null;
  }

  return {
    editorInstance,
    isFindVisible,
    isReplaceVisible,
    setEditorInstance,
    saveCurrentFile,
  };
});








































