<template>
  <div class="workflow-summary-card">
    <!-- Header -->
    <div class="summary-header" @click="toggleExpanded">
      <div class="header-left">
        <component :is="statusIcon" :size="20" class="status-icon" :class="statusClass" />
        <div class="header-text">
          <h4 class="summary-title">{{ workflowTitle }}</h4>
          <p class="summary-subtitle">{{ workflowSubtitle }}</p>
        </div>
      </div>
      <button class="expand-btn">
        <ChevronDown :size="16" :class="{ 'rotated': isExpanded }" />
      </button>
    </div>

    <!-- Expanded Content -->
    <div v-if="isExpanded" class="summary-content">
      <!-- Tasks Executed -->
      <div v-if="tasks && tasks.length > 0" class="section">
        <div class="section-header">
          <ListChecks :size="16" />
          <h5>Tasks Executed</h5>
          <span class="badge">{{ completedTasksCount }}/{{ tasks.length }}</span>
        </div>
        <div class="tasks-list">
          <div
            v-for="(task, index) in tasks"
            :key="task.id"
            class="task-item"
            :class="getTaskStatusClass(task.status)"
          >
            <div class="task-number">{{ index + 1 }}</div>
            <div class="task-content">
              <div class="task-description">{{ task.description }}</div>
              <div class="task-meta">
                <span class="task-agent">{{ task.agent }}</span>
                <span v-if="task.started_at" class="task-time">
                  {{ formatDuration(task.started_at, task.completed_at) }}
                </span>
              </div>
            </div>
            <component
              :is="getTaskStatusIcon(task.status)"
              :size="16"
              class="task-status-icon"
            />
          </div>
        </div>
      </div>

      <!-- Files Modified -->
      <div v-if="filesModified && filesModified.length > 0" class="section">
        <div class="section-header">
          <FileEdit :size="16" />
          <h5>Files Modified</h5>
          <span class="badge">{{ filesModified.length }}</span>
        </div>
        <div class="files-list">
          <div
            v-for="file in filesModified"
            :key="file.path"
            class="file-item"
            @click="openFile(file.path)"
          >
            <FileText :size="14" />
            <span class="file-path">{{ file.path }}</span>
            <span class="file-action">{{ file.action }}</span>
          </div>
        </div>
      </div>

      <!-- Tool Calls -->
      <div v-if="toolCalls && toolCalls.length > 0" class="section">
        <div class="section-header">
          <Wrench :size="16" />
          <h5>Actions Performed</h5>
          <span class="badge">{{ toolCalls.length }}</span>
        </div>
        <div class="tools-list">
          <div
            v-for="(tool, index) in toolCalls"
            :key="index"
            class="tool-item"
          >
            <component
              :is="getToolIcon(tool.name)"
              :size="14"
              class="tool-icon"
            />
            <div class="tool-content">
              <div class="tool-name">{{ formatToolName(tool.name) }}</div>
              <div class="tool-details">{{ getToolDetails(tool) }}</div>
            </div>
            <span
              class="tool-status"
              :class="getToolStatusClass(tool.status)"
            >
              {{ tool.status }}
            </span>
          </div>
        </div>
      </div>

      <!-- Workflow Stats -->
      <div class="section stats-section">
        <div class="stat-item">
          <Clock :size="14" />
          <span class="stat-label">Duration:</span>
          <span class="stat-value">{{ totalDuration }}</span>
        </div>
        <div class="stat-item" v-if="exploration">
          <Search :size="14" />
          <span class="stat-label">Files Explored:</span>
          <span class="stat-value">{{ exploration.filesRead || 0 }}</span>
        </div>
        <div class="stat-item" v-if="validation">
          <Shield :size="14" />
          <span class="stat-label">Validation:</span>
          <span class="stat-value">{{ validation.success ? 'Passed' : 'Failed' }}</span>
        </div>
      </div>

      <!-- Error Details (if any) -->
      <div v-if="error" class="section error-section">
        <div class="section-header">
          <AlertCircle :size="16" />
          <h5>Error Details</h5>
        </div>
        <div class="error-content">
          <p class="error-message">{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  ChevronDown, ListChecks, FileEdit, FileText, Wrench, Clock,
  Search, Shield, AlertCircle, CheckCircle, XCircle, Loader,
  Play, Pause, FileCode, FolderOpen, Terminal, Code
} from 'lucide-vue-next';

const props = defineProps({
  workflow: {
    type: Object,
    required: true
  }
});

const isExpanded = ref(true);

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value;
};

// Computed properties
const statusIcon = computed(() => {
  const status = props.workflow.status || 'completed';
  const icons = {
    completed: CheckCircle,
    failed: XCircle,
    cancelled: XCircle,
    running: Loader
  };
  return icons[status] || CheckCircle;
});

const statusClass = computed(() => {
  const status = props.workflow.status || 'completed';
  return `status-${status}`;
});

const workflowTitle = computed(() => {
  // Check if there are any failed tools
  const hasFailedTools = toolCalls.value.some(t =>
    t.status === 'error' || t.status === 'failed' || t.status === 'ERROR'
  );
  
  // Check if there are any failed tasks
  const hasFailedTasks = tasks.value.some(t => t.status === 'failed');
  
  const status = props.workflow.status || 'completed';
  
  // Override status if there are failures
  if (hasFailedTools || hasFailedTasks) {
    return 'Workflow Completed with Errors';
  }
  
  const titles = {
    completed: 'Workflow Completed Successfully',
    failed: 'Workflow Failed',
    cancelled: 'Workflow Cancelled',
    running: 'Workflow In Progress'
  };
  return titles[status] || 'Workflow Result';
});

const workflowSubtitle = computed(() => {
  if (props.workflow.goal) {
    return props.workflow.goal;
  }
  return `${completedTasksCount.value} tasks completed`;
});

const tasks = computed(() => props.workflow.plan?.tasks || []);

const completedTasksCount = computed(() => {
  return tasks.value.filter(t => t.status === 'completed').length;
});

const filesModified = computed(() => {
  const files = [];
  
  // Extract files from task results
  tasks.value.forEach(task => {
    if (task.result && task.result.result) {
      const result = task.result.result;
      if (result.files_modified) {
        result.files_modified.forEach(file => {
          files.push({
            path: file,
            action: 'modified'
          });
        });
      }
      if (result.files_created) {
        result.files_created.forEach(file => {
          files.push({
            path: file,
            action: 'created'
          });
        });
      }
    }
  });
  
  // Remove duplicates
  const uniqueFiles = Array.from(
    new Map(files.map(f => [f.path, f])).values()
  );
  
  return uniqueFiles;
});

const toolCalls = computed(() => props.workflow.tools || []);

const exploration = computed(() => props.workflow.exploration);

const validation = computed(() => props.workflow.validation);

const error = computed(() => props.workflow.error);

const totalDuration = computed(() => {
  if (!props.workflow.execution) return 'N/A';
  
  const execution = props.workflow.execution;
  if (execution.started_at && execution.completed_at) {
    const start = new Date(execution.started_at);
    const end = new Date(execution.completed_at);
    const diff = end - start;
    return formatMilliseconds(diff);
  }
  
  return 'N/A';
});

// Helper functions
const getTaskStatusClass = (status) => {
  return `task-status-${status}`;
};

const getTaskStatusIcon = (status) => {
  const icons = {
    completed: CheckCircle,
    failed: XCircle,
    in_progress: Loader,
    pending: Clock,
    cancelled: XCircle
  };
  return icons[status] || Clock;
};

const formatDuration = (startTime, endTime) => {
  if (!startTime || !endTime) return '';
  
  const start = new Date(startTime);
  const end = new Date(endTime);
  const diff = end - start;
  
  return formatMilliseconds(diff);
};

const formatMilliseconds = (ms) => {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

const getToolIcon = (toolName) => {
  const icons = {
    read_file: FileText,
    write_file: FileCode,
    read_directory_tree: FolderOpen,
    execute_command: Terminal,
    default: Code
  };
  return icons[toolName] || icons.default;
};

const formatToolName = (toolName) => {
  return toolName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getToolDetails = (tool) => {
  if (tool.name === 'read_file') {
    return tool.input?.path || tool.input?.file_path || '';
  } else if (tool.name === 'write_file') {
    return tool.input?.file_path || tool.input?.path || '';
  } else if (tool.name === 'read_directory_tree') {
    return tool.input?.path || '';
  } else if (tool.name === 'execute_command') {
    return tool.input?.command || '';
  }
  return JSON.stringify(tool.input).substring(0, 50);
};

const getToolStatusClass = (status) => {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus === 'success' || normalizedStatus === 'completed') {
    return 'tool-status-success';
  } else if (normalizedStatus === 'error' || normalizedStatus === 'failed') {
    return 'tool-status-error';
  } else if (normalizedStatus === 'executing' || normalizedStatus === 'in_progress') {
    return 'tool-status-executing';
  }
  return `tool-status-${normalizedStatus}`;
};

const openFile = (filePath) => {
  // Emit event to open file in editor
  // This would be handled by parent component
  console.log('Open file:', filePath);
};
</script>

<style scoped>
.workflow-summary-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin: var(--space-4) 0;
  overflow: hidden;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  cursor: pointer;
  transition: background 0.2s;
}

.summary-header:hover {
  background: var(--accent);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.status-icon {
  flex-shrink: 0;
}

.status-icon.status-completed {
  color: var(--success, #22c55e);
}

.status-icon.status-failed {
  color: var(--destructive);
}

.status-icon.status-cancelled {
  color: var(--muted-foreground);
}

.status-icon.status-running {
  color: var(--primary);
  animation: spin 1s linear infinite;
}

.header-text {
  flex: 1;
}

.summary-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--foreground);
}

.summary-subtitle {
  margin: var(--space-1) 0 0 0;
  font-size: 12px;
  color: var(--muted-foreground);
}

.expand-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.expand-btn:hover {
  background: var(--muted);
  color: var(--foreground);
}

.expand-btn svg {
  transition: transform 0.3s;
}

.expand-btn svg.rotated {
  transform: rotate(180deg);
}

.summary-content {
  border-top: 1px solid var(--border);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--foreground);
  font-weight: 600;
  font-size: 13px;
}

.section-header h5 {
  margin: 0;
  flex: 1;
}

.badge {
  background: var(--muted);
  color: var(--muted-foreground);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.task-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--muted);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--border);
}

.task-item.task-status-completed {
  border-left-color: var(--success, #22c55e);
}

.task-item.task-status-failed {
  border-left-color: var(--destructive);
}

.task-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: var(--background);
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  color: var(--muted-foreground);
  flex-shrink: 0;
}

.task-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.task-description {
  font-size: 13px;
  color: var(--foreground);
  line-height: 1.4;
}

.task-meta {
  display: flex;
  gap: var(--space-3);
  font-size: 11px;
  color: var(--muted-foreground);
}

.task-agent {
  text-transform: capitalize;
  font-weight: 500;
}

.task-status-icon {
  flex-shrink: 0;
  color: var(--muted-foreground);
}

.files-list,
.tools-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--muted);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
  font-size: 12px;
}

.file-item:hover {
  background: var(--accent);
}

.file-path {
  flex: 1;
  color: var(--foreground);
  font-family: var(--font-mono);
}

.file-action {
  color: var(--muted-foreground);
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--muted);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.tool-icon {
  color: var(--primary);
  flex-shrink: 0;
}

.tool-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.tool-name {
  font-weight: 600;
  color: var(--foreground);
}

.tool-details {
  color: var(--muted-foreground);
  font-size: 11px;
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.tool-status-icon {
  font-size: 11px;
  line-height: 1;
  display: flex;
  align-items: center;
}

.tool-status-text {
  text-transform: uppercase;
  line-height: 1;
  display: flex;
  align-items: center;
}

.tool-status-success {
  background: color-mix(in srgb, var(--success, #22c55e) 20%, transparent 80%);
  color: var(--success, #22c55e);
}

.tool-status-error {
  background: color-mix(in srgb, var(--destructive) 20%, transparent 80%);
  color: var(--destructive);
}

.tool-status-executing {
  background: color-mix(in srgb, var(--primary) 20%, transparent 80%);
  color: var(--primary);
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--muted);
  border-radius: var(--radius-md);
  font-size: 12px;
}

.stat-label {
  color: var(--muted-foreground);
  font-weight: 500;
}

.stat-value {
  color: var(--foreground);
  font-weight: 600;
  margin-left: auto;
}

.error-section {
  background: color-mix(in srgb, var(--destructive) 10%, transparent 90%);
  border: 1px solid color-mix(in srgb, var(--destructive) 30%, transparent 70%);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.error-content {
  padding: var(--space-2) 0;
}

.error-message {
  margin: 0;
  font-size: 12px;
  color: var(--destructive);
  line-height: 1.5;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>