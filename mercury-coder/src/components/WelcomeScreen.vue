<template>
  <div class="welcome-screen">
    <div class="welcome-content">
      <div class="welcome-header">
        <div class="app-logo">
          <svg width="100" height="100" viewBox="0 0 80 80" fill="none">
            <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="6"/>
            <circle cx="40" cy="40" r="14" stroke="currentColor" stroke-width="6"/>
          </svg>
        </div>
        <h1>Mercury Coder</h1>
        <p class="tagline">AI-Powered Code Editor</p>
      </div>

      <div class="recent-projects" v-if="recentProjects.length > 0">
        <h2>Recent Projects</h2>
        <div class="project-list">
          <div
            v-for="project in recentProjects"
            :key="project.id"
            class="project-card"
            @click="openProject(project)"
          >
            <Folder class="project-icon" :size="32" />
            <div class="project-info">
              <div class="project-name">{{ project.name }}</div>
              <div class="project-path">{{ project.path }}</div>
            </div>
            <button 
              class="project-delete"
              @click.stop="deleteProject(project.id)"
              title="Delete project"
            >
              <X :size="20" />
            </button>
          </div>
        </div>
      </div>

      <div class="actions">
        <button class="primary-btn" @click="openProjectDialog">
          <FolderOpen :size="18" /> Open Project
        </button>
        <button class="secondary-btn" @click="createProject">
          <FilePlus :size="18" /> New Project
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { Folder, X, FolderOpen, FilePlus } from 'lucide-vue-next';

const emit = defineEmits(['project-opened']);

const recentProjects = ref([]);

const loadProjects = async () => {
  try {
    if (!window.electronAPI) {
      console.error('Electron API is not available. Make sure you are running this app in Electron.');
      return;
    }
    const projects = await window.electronAPI.getProjects();
    if (projects) {
      recentProjects.value = projects.slice(0, 3); // Show last 3
    }
  } catch (error) {
    console.error('Failed to load projects:', error);
  }
};

const openProjectDialog = async () => {
  try {
    if (!window.electronAPI) {
      alert('Electron API is not available. Make sure you are running this app in Electron.');
      return;
    }
    const result = await window.electronAPI.openFolderDialog();
    if (result && result.path) {
      const projectName = result.path.split(/[/\\]/).pop();
      const addResult = await window.electronAPI.addProject(projectName, result.path);
      if (addResult && addResult.success) {
        const project = {
          id: addResult.id,
          name: projectName,
          path: result.path,
        };
        emit('project-opened', project);
      }
    }
  } catch (error) {
    console.error('Failed to open project:', error);
    alert('Failed to open project folder. Please try again.');
  }
};

const openProject = async (project) => {
  if (!window.electronAPI) {
    alert('Electron API is not available. Make sure you are running this app in Electron.');
    return;
  }
  try {
    console.log('WelcomeScreen: Opening project:', project);
    await window.electronAPI.openProject(project.id);
    const updatedProject = await window.electronAPI.getProject(project.id);
    console.log('WelcomeScreen: Got project from database:', updatedProject);
    console.log('WelcomeScreen: Project path:', updatedProject?.path);
    if (updatedProject) {
      // Ensure we have the path property
      if (!updatedProject.path) {
        console.error('WelcomeScreen: Project missing path property!', updatedProject);
        alert('Error: Project path is missing. Please re-add this project.');
        return;
      }
      emit('project-opened', updatedProject);
      loadProjects();
    } else {
      console.error('WelcomeScreen: getProject returned null/undefined');
      alert('Failed to load project details. Please try again.');
    }
  } catch (error) {
    console.error('Failed to open project:', error);
    alert('Failed to open project. Please try again.');
  }
};

const deleteProject = async (projectId) => {
  if (!window.electronAPI) {
    alert('Electron API is not available. Make sure you are running this app in Electron.');
    return;
  }
  if (confirm('Are you sure you want to delete this project from your recent list?')) {
    try {
      await window.electronAPI.deleteProject(projectId);
      loadProjects();
    } catch (error) {
      console.error('Failed to delete project:', error);
      alert('Failed to delete project. Please try again.');
    }
  }
};

const createProject = () => {
  // Implement create project dialog
  alert('Create project feature coming soon!');
};

onMounted(() => {
  loadProjects();
});
</script>

<style scoped>
.welcome-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100vw;
  height: 100vh;
  background: var(--background, #f9f9f9);
  padding: var(--space-20);
  overflow: auto;
  position: relative;
}

.welcome-content {
  max-width: 800px;
  width: 100%;
}

.welcome-header {
  text-align: center;
  margin-bottom: var(--space-24);
}

.app-logo {
  margin: 0 auto var(--space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.welcome-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: var(--foreground, #202020);
  margin-bottom: var(--space-4);
}

.tagline {
  font-size: 18px;
  color: var(--muted-foreground);
}

.recent-projects {
  margin-bottom: var(--space-20);
}

.recent-projects h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--foreground);
  margin-bottom: var(--space-10);
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.project-card {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-8);
  background: var(--card);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.project-card:hover {
  background: var(--muted);
}

.project-icon {
  flex-shrink: 0;
  color: var(--muted-foreground);
}

.project-info {
  flex: 1;
}

.project-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--foreground);
  margin-bottom: var(--space-2);
}

.project-path {
  font-size: 12px;
  color: var(--muted-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-delete {
  background: none;
  border: none;
  color: var(--muted-foreground);
  font-size: 24px;
  cursor: pointer;
  width: var(--button-md);
  height: var(--button-md);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.project-delete:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.actions {
  display: flex;
  gap: var(--space-8);
  justify-content: center;
}

.primary-btn,
.secondary-btn {
  padding: var(--space-6) var(--space-16);
  border-radius: var(--radius-lg);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  transition: all 0.2s;
  border: none;
}

.primary-btn {
  background: var(--primary);
  color: var(--primary-foreground);
}

.primary-btn:hover {
  background: var(--primary);
    transform: translateY(calc(-1 * var(--space-1)));
  box-shadow: var(--shadow-lg);
}

.secondary-btn {
  background: var(--sidebar);
  color: var(--foreground);
  border: none;
}

.secondary-btn:hover {
  background: var(--muted);
}
</style>

