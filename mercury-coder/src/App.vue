<template>
  <div id="app" :class="{ dark: isDark }">
    <div v-if="!isElectron" class="electron-warning">
      <div class="warning-content">
        <h3>⚠️ Electron Not Detected</h3>
        <p>This app needs to run in Electron, not in a browser.</p>
        <p>Please run: <code>npm run dev</code> to start the Electron app.</p>
        <p class="warning-note">If you just ran that command, wait a few seconds for Electron to launch.</p>
      </div>
    </div>
    <SettingsPage v-else-if="projectStore.showSettings" />
    <MemoryBrowser v-else-if="projectStore.showMemoryBrowser" />
    <MainLayout v-else-if="currentProject" />
    <WelcomeScreen v-else @project-opened="handleProjectOpened" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import MainLayout from './components/MainLayout.vue';
import WelcomeScreen from './components/WelcomeScreen.vue';
import SettingsPage from './components/SettingsPage.vue';
import MemoryBrowser from './components/MemoryBrowser.vue';
import { useProjectStore } from './stores/project';
import { useModelsStore } from './stores/models';
import { useTheme } from './composables/useTheme';

const { isDark } = useTheme();

const projectStore = useProjectStore();
const modelsStore = useModelsStore();

// Check if Electron is available
const isElectron = ref(typeof window !== 'undefined' && window.electronAPI !== undefined);

// Use computed to reactively watch the project store
const currentProject = computed(() => projectStore.currentProject);

onMounted(async () => {
  // Re-check Electron availability (in case it loads after page load)
  if (typeof window !== 'undefined' && !isElectron.value) {
    // Wait a bit and recheck (Electron might load after page)
    setTimeout(() => {
      isElectron.value = window.electronAPI !== undefined;
    }, 1000);
  }

  // Preload models in the background
  modelsStore.preloadModels().catch(err => {
    console.error('Failed to preload models:', err);
  });

  // Try to restore last opened project
  if (isElectron.value && window.electronAPI) {
    try {
      const projects = await window.electronAPI.getProjects();
      if (projects && projects.length > 0) {
        // You could implement logic to auto-open last project here
      }
    } catch (error) {
      console.error('Failed to load projects on mount:', error);
    }
  }
});

const handleProjectOpened = (project) => {
  console.log('App: handleProjectOpened called with project:', project);
  console.log('App: Project path:', project?.path);
  if (!project || !project.path) {
    console.error('App: Invalid project object received:', project);
    alert('Error: Invalid project data. Path is missing.');
    return;
  }
  projectStore.setCurrentProject(project);
  console.log('App: Project set in store:', projectStore.currentProject);
};
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-sans);
  overflow: hidden;
}

#app {
  width: 100vw;
  height: 100vh;
}

.electron-warning {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--background);
  padding: 40px;
}

.warning-content {
  max-width: 600px;
  background: var(--card);
  border: none;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
}

.warning-content h3 {
  color: var(--destructive);
  margin-bottom: 16px;
  font-size: 24px;
}

.warning-content p {
  color: var(--foreground);
  margin-bottom: 12px;
  line-height: 1.6;
}

.warning-content code {
  background: var(--muted);
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  color: var(--primary);
}

.warning-note {
  font-size: 14px;
  color: var(--muted-foreground);
  font-style: italic;
}
</style>


