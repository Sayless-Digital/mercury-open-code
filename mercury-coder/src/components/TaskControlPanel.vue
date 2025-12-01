<template>
  <div v-if="showControls" class="task-control-panel">
    <!-- Task Status Display -->
    <div class="task-status">
      <div class="status-indicator" :class="statusClass">
        <component :is="statusIcon" :size="16" />
        <span class="status-text">{{ statusMessage }}</span>
      </div>
      <div v-if="showProgress" class="progress-info">
        {{ progressText }}
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="task-actions">
      <button
        v-if="canPause"
        @click="handlePause"
        class="action-btn pause-btn"
        :disabled="actionPending"
        title="Pause workflow at next checkpoint"
      >
        <Pause :size="14" />
        Pause
      </button>

      <button
        v-if="canResume"
        @click="handleResume"
        class="action-btn resume-btn"
        :disabled="actionPending"
        title="Resume from checkpoint"
      >
        <Play :size="14" />
        Resume
      </button>

      <button
        v-if="canCancel"
        @click="handleCancel"
        class="action-btn cancel-btn"
        :disabled="actionPending"
        title="Cancel workflow"
      >
        <XCircle :size="14" />
        Cancel
      </button>
    </div>

    <!-- Confirmation Dialog -->
    <div v-if="showConfirmDialog" class="confirmation-overlay" @click="closeConfirmDialog">
      <div class="confirmation-dialog" @click.stop>
        <div class="dialog-header">
          <h3>{{ confirmDialog.title }}</h3>
          <button @click="closeConfirmDialog" class="close-btn">
            <X :size="16" />
          </button>
        </div>
        <div class="dialog-body">
          <p>{{ confirmDialog.message }}</p>
          <div v-if="confirmDialog.details" class="dialog-details">
            <div v-for="(value, key) in confirmDialog.details" :key="key" class="detail-item">
              <span class="detail-label">{{ key }}:</span>
              <span class="detail-value">{{ value }}</span>
            </div>
          </div>
        </div>
        <div class="dialog-actions">
          <button @click="closeConfirmDialog" class="dialog-btn cancel-dialog-btn">
            {{ confirmDialog.cancelText || 'Cancel' }}
          </button>
          <button
            @click="confirmAction"
            class="dialog-btn confirm-dialog-btn"
            :class="confirmDialog.variant"
          >
            {{ confirmDialog.confirmText || 'Confirm' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Notification Toast -->
    <transition name="toast">
      <div v-if="showNotification" class="notification-toast" :class="notification.type">
        <component :is="getNotificationIcon(notification.type)" :size="16" />
        <div class="notification-content">
          <div class="notification-title">{{ notification.title }}</div>
          <div v-if="notification.message" class="notification-message">{{ notification.message }}</div>
        </div>
        <button @click="closeNotification" class="notification-close">
          <X :size="14" />
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import {
  Pause, Play, XCircle, X, Clock, CheckCircle, AlertCircle, Info, AlertTriangle
} from 'lucide-vue-next';
import { useChatStore } from '@/stores/chat';

const chatStore = useChatStore();

const actionPending = ref(false);
const showConfirmDialog = ref(false);
const confirmDialog = ref({});
const pendingAction = ref(null);
const showNotification = ref(false);
const notification = ref({});
let notificationTimeout = null;

// Compute task management state
const workflowId = computed(() => chatStore.currentWorkflowId);
const taskState = computed(() => chatStore.taskManagementState || {});
const workflowState = computed(() => taskState.value.state || 'created');
const isRunning = computed(() => workflowState.value === 'running');
const isPaused = computed(() => workflowState.value === 'paused');
const isCancelling = computed(() => workflowState.value === 'cancelling');
const isCancelled = computed(() => workflowState.value === 'cancelled');
const isCompleted = computed(() => workflowState.value === 'completed');
const isFailed = computed(() => workflowState.value === 'failed');

const showControls = computed(() => {
  return workflowId.value && !isCompleted.value && !isCancelled.value;
});

const canPause = computed(() => isRunning.value && !actionPending.value);
const canResume = computed(() => isPaused.value && !actionPending.value);
const canCancel = computed(() => (isRunning.value || isPaused.value) && !isCancelling.value && !actionPending.value);

// Status display
const statusClass = computed(() => {
  if (isRunning.value) return 'status-running';
  if (isPaused.value) return 'status-paused';
  if (isCancelling.value) return 'status-cancelling';
  if (isCancelled.value) return 'status-cancelled';
  if (isCompleted.value) return 'status-completed';
  if (isFailed.value) return 'status-failed';
  return 'status-unknown';
});

const statusIcon = computed(() => {
  if (isRunning.value) return Clock;
  if (isPaused.value) return Pause;
  if (isCancelling.value) return XCircle;
  if (isCancelled.value) return XCircle;
  if (isCompleted.value) return CheckCircle;
  if (isFailed.value) return AlertCircle;
  return Info;
});

const statusMessage = computed(() => {
  const state = taskState.value;
  if (state.statusMessage) return state.statusMessage;
  
  // Default messages based on state
  const messages = {
    running: '⏳ Executing workflow...',
    paused: '⏸️ Workflow paused',
    cancelling: '🛑 Cancelling...',
    cancelled: '❌ Workflow cancelled',
    completed: '✅ Completed',
    failed: '⚠️ Failed'
  };
  return messages[workflowState.value] || 'Ready';
});

const showProgress = computed(() => {
  return taskState.value.plan_progress && isRunning.value;
});

const progressText = computed(() => {
  const progress = taskState.value.plan_progress;
  if (!progress) return '';
  
  const { completed = 0, total = 0, failed = 0 } = progress;
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  
  let text = `${completed}/${total} tasks (${percentage}%)`;
  if (failed > 0) text += ` | ${failed} failed`;
  
  return text;
});

// Action handlers
const handlePause = () => {
  confirmDialog.value = {
    title: 'Pause Workflow?',
    message: 'The workflow will be paused at the next safe checkpoint. You can resume it later from this point.',
    confirmText: 'Pause',
    cancelText: 'Keep Running',
    variant: 'warning'
  };
  pendingAction.value = 'pause';
  showConfirmDialog.value = true;
};

const handleResume = async () => {
  try {
    actionPending.value = true;
    await chatStore.resumeWorkflow(workflowId.value);
    showNotificationToast({
      title: 'Workflow Resumed',
      message: 'Continuing from last checkpoint',
      type: 'success'
    });
  } catch (error) {
    console.error('Resume failed:', error);
    showNotificationToast({
      title: 'Resume Failed',
      message: error.message || 'Could not resume workflow',
      type: 'error'
    });
  } finally {
    actionPending.value = false;
  }
};

const handleCancel = () => {
  confirmDialog.value = {
    title: 'Cancel Workflow?',
    message: 'This will stop all running tasks and clean up resources. This action cannot be undone.',
    confirmText: 'Cancel Workflow',
    cancelText: 'Keep Running',
    variant: 'danger'
  };
  pendingAction.value = 'cancel';
  showConfirmDialog.value = true;
};

const confirmAction = async () => {
  const action = pendingAction.value;
  closeConfirmDialog();
  
  if (!action) return;
  
  try {
    actionPending.value = true;
    
    if (action === 'pause') {
      await chatStore.pauseWorkflow(workflowId.value);
      showNotificationToast({
        title: 'Workflow Paused',
        message: 'Saved at checkpoint',
        type: 'info'
      });
    } else if (action === 'cancel') {
      await chatStore.cancelWorkflow(workflowId.value);
      showNotificationToast({
        title: 'Workflow Cancelled',
        message: 'All tasks stopped',
        type: 'warning'
      });
    }
  } catch (error) {
    console.error(`${action} failed:`, error);
    showNotificationToast({
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} Failed`,
      message: error.message || `Could not ${action} workflow`,
      type: 'error'
    });
  } finally {
    actionPending.value = false;
  }
};

const closeConfirmDialog = () => {
  showConfirmDialog.value = false;
  pendingAction.value = null;
  confirmDialog.value = {};
};

const showNotificationToast = (notif) => {
  notification.value = notif;
  showNotification.value = true;
  
  if (notificationTimeout) {
    clearTimeout(notificationTimeout);
  }
  
  notificationTimeout = setTimeout(() => {
    closeNotification();
  }, 5000);
};

const closeNotification = () => {
  showNotification.value = false;
  if (notificationTimeout) {
    clearTimeout(notificationTimeout);
    notificationTimeout = null;
  }
};

const getNotificationIcon = (type) => {
  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info
  };
  return icons[type] || Info;
};

// Watch for state changes and show notifications
watch(() => taskState.value.state, (newState, oldState) => {
  if (newState !== oldState) {
    if (newState === 'completed') {
      showNotificationToast({
        title: 'Workflow Completed',
        message: 'All tasks completed successfully',
        type: 'success'
      });
    } else if (newState === 'failed') {
      showNotificationToast({
        title: 'Workflow Failed',
        message: taskState.value.error || 'Workflow execution failed',
        type: 'error'
      });
    }
  }
});
</script>

<style scoped>
.task-control-panel {
  padding: var(--space-4);
  background: var(--card);
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.task-status {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  font-weight: 500;
}

.status-running {
  color: var(--primary);
}

.status-paused {
  color: var(--warning);
}

.status-cancelling,
.status-cancelled {
  color: var(--destructive);
}

.status-completed {
  color: var(--success, #22c55e);
}

.status-failed {
  color: var(--destructive);
}

.progress-info {
  font-size: 12px;
  color: var(--muted-foreground);
  padding-left: calc(16px + var(--space-2));
}

.task-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  font-family: inherit;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pause-btn {
  background: var(--warning);
  color: var(--warning-foreground);
  border-color: var(--warning);
}

.pause-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.resume-btn {
  background: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}

.resume-btn:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.cancel-btn {
  background: var(--destructive);
  color: var(--destructive-foreground);
  border-color: var(--destructive);
}

.cancel-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.confirmation-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.confirmation-dialog {
  background: var(--card);
  border-radius: var(--radius-lg);
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5);
  border-bottom: 1px solid var(--border);
}

.dialog-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--foreground);
}

.close-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-1);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--accent);
  color: var(--foreground);
}

.dialog-body {
  padding: var(--space-5);
}

.dialog-body p {
  margin: 0;
  color: var(--foreground);
  line-height: 1.6;
  font-size: 14px;
}

.dialog-details {
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--muted);
  border-radius: var(--radius-sm);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: var(--space-1) 0;
}

.detail-label {
  color: var(--muted-foreground);
  font-weight: 500;
}

.detail-value {
  color: var(--foreground);
}

.dialog-actions {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-5);
  border-top: 1px solid var(--border);
  justify-content: flex-end;
}

.dialog-btn {
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  font-family: inherit;
}

.cancel-dialog-btn {
  background: var(--background);
  color: var(--foreground);
}

.cancel-dialog-btn:hover {
  background: var(--accent);
}

.confirm-dialog-btn {
  background: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}

.confirm-dialog-btn:hover {
  background: var(--primary-hover);
}

.confirm-dialog-btn.warning {
  background: var(--warning);
  border-color: var(--warning);
}

.confirm-dialog-btn.danger {
  background: var(--destructive);
  border-color: var(--destructive);
}

.notification-toast {
  position: fixed;
  top: var(--space-5);
  right: var(--space-5);
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  min-width: 300px;
  max-width: 400px;
  z-index: 1001;
  border-left: 3px solid var(--primary);
}

.notification-toast.success {
  border-left-color: var(--success, #22c55e);
}

.notification-toast.error {
  border-left-color: var(--destructive);
}

.notification-toast.warning {
  border-left-color: var(--warning);
}

.notification-toast.info {
  border-left-color: var(--primary);
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--foreground);
  margin-bottom: var(--space-1);
}

.notification-message {
  font-size: 12px;
  color: var(--muted-foreground);
  line-height: 1.4;
}

.notification-close {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-1);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  flex-shrink: 0;
}

.notification-close:hover {
  background: var(--accent);
  color: var(--foreground);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>