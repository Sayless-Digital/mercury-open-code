<template>
  <div class="session-history">
    <div class="session-history-header">
      <h3 class="session-history-title">Session History</h3>
      <div class="session-history-actions">
        <button 
          class="session-history-clear"
          @click="handleClearAll"
          title="Clear All Sessions"
          :disabled="sortedSessions.length === 0"
        >
          <Trash2 :size="14" />
          <span>Clear All</span>
        </button>
        <button 
          class="session-history-new"
          @click="handleNewSession"
          title="New Session"
        >
          <Plus :size="16" />
          <span>New Session</span>
        </button>
      </div>
    </div>
    
    <div class="session-history-list">
      <div 
        v-for="session in sortedSessions" 
        :key="session.id"
        class="session-history-item"
        :class="{ 
          active: session.id === activeSessionId,
          opened: isOpened(session.id)
        }"
        @click="handleOpenSession(session.id)"
      >
        <div class="session-history-item-content">
          <div class="session-history-item-title">{{ getSessionTitle(session) }}</div>
          <div class="session-history-item-meta">
            <span class="session-history-item-date">{{ getSessionDate(session) }}</span>
            <span v-if="isOpened(session.id)" class="session-history-item-badge">Opened</span>
          </div>
        </div>
        <div class="session-history-item-actions">
          <button 
            class="session-history-item-delete"
            @click.stop="handleDelete(session.id)"
            title="Delete Session"
          >
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
      
      <div v-if="sortedSessions.length === 0" class="session-history-empty">
        <p>No sessions yet. Create your first session to get started!</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'
import { Plus, Trash2 } from 'lucide-vue-next'

const sessionStore = useSessionStore()

const sortedSessions = computed(() => sessionStore.sortedSessions)
const activeSessionId = computed(() => sessionStore.activeSessionId)
const openedSessions = computed(() => sessionStore.openedSessions)

function isOpened(sessionId) {
  return openedSessions.value.includes(sessionId)
}

function getSessionTitle(session) {
  if (session.title && !session.title.startsWith('New session - ') && !session.title.startsWith('Child session - ')) {
    return session.title
  }
  
  // Generate a friendly title from the date
  if (session.time?.created) {
    const date = new Date(session.time.created)
    return `Session ${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }
  
  return 'Session'
}

function getSessionDate(session) {
  if (session.time?.updated || session.time?.created) {
    const date = new Date(session.time?.updated || session.time?.created)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return ''
}

async function handleOpenSession(sessionId) {
  sessionStore.openSession(sessionId)
}

async function handleNewSession() {
  await sessionStore.createNewSession()
}

async function handleDelete(sessionId) {
  if (confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
    await sessionStore.deleteSession(sessionId)
  }
}

async function handleClearAll() {
  const count = sortedSessions.value.length
  if (confirm(`Are you sure you want to delete all ${count} sessions? This action cannot be undone.`)) {
    await sessionStore.clearAllSessions()
  }
}

// Load sessions on mount
onMounted(async () => {
  await sessionStore.loadSessions()
})
</script>

<style scoped>
.session-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--background);
}

.session-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.session-history-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.session-history-clear {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--background);
  color: var(--muted-foreground);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-history-clear:hover:not(:disabled) {
  background: var(--destructive);
  color: var(--destructive-foreground);
  border-color: var(--destructive);
}

.session-history-clear:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.session-history-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--foreground);
  margin: 0;
}

.session-history-new {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--background);
  color: var(--foreground);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-history-new:hover {
  background: var(--muted);
  border-color: var(--primary);
}

.session-history-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.session-history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  margin-bottom: var(--space-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--background);
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-history-item:hover {
  background: var(--muted);
  border-color: var(--primary);
}

.session-history-item.active {
  background: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}

.session-history-item.opened {
  border-left: 3px solid var(--primary);
}

.session-history-item-content {
  flex: 1;
  min-width: 0;
}

.session-history-item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--foreground);
  margin-bottom: var(--space-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-history-item.active .session-history-item-title {
  color: var(--primary-foreground);
}

.session-history-item-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 12px;
  color: var(--muted-foreground);
}

.session-history-item.active .session-history-item-meta {
  color: var(--primary-foreground);
  opacity: 0.9;
}

.session-history-item-date {
  flex-shrink: 0;
}

.session-history-item-badge {
  padding: 2px var(--space-2);
  background: var(--muted);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}

.session-history-item.active .session-history-item-badge {
  background: rgba(255, 255, 255, 0.2);
}

.session-history-item-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-2);
  flex-shrink: 0;
}

.session-history-item-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--muted-foreground);
  cursor: pointer;
  border-radius: var(--radius-sm);
  opacity: 0;
  transition: all 0.2s ease;
}

.session-history-item:hover .session-history-item-delete {
  opacity: 1;
}

.session-history-item-delete:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.session-history-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  text-align: center;
  color: var(--muted-foreground);
}
</style>

