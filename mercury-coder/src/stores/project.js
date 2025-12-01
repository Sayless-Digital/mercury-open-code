import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useProjectStore = defineStore('project', () => {
  const currentProject = ref(null);
  const activeFile = ref(null);
  const openFiles = ref([]);
  const fileTree = ref([]);
  const showSettings = ref(false);
  const showMemoryBrowser = ref(false);

  function setCurrentProject(project) {
    currentProject.value = project;
  }

  function setActiveFile(filePath) {
    activeFile.value = filePath;
    if (!openFiles.value.includes(filePath)) {
      openFiles.value.push(filePath);
    }
  }

  function closeFile(filePath) {
    const index = openFiles.value.indexOf(filePath);
    if (index > -1) {
      openFiles.value.splice(index, 1);
    }
    if (activeFile.value === filePath) {
      activeFile.value = openFiles.value[openFiles.value.length - 1] || null;
    }
  }

  function setFileTree(tree) {
    fileTree.value = tree;
  }

  return {
    currentProject,
    activeFile,
    openFiles,
    fileTree,
    showSettings,
    showMemoryBrowser,
    setCurrentProject,
    setActiveFile,
    closeFile,
    setFileTree,
  };
});


