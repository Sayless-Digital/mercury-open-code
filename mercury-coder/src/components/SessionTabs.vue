<template>
  <div class="session-tabs">
    <div class="session-tabs-container">
      <button 
        class="session-tab-new"
        @click="handleNewSession"
        title="New Session"
      >
        <Plus :size="14" />
      </button>
      <div 
        v-for="session in openedSessions" 
        :key="session.id"
        class="session-tab"
        :class="{ active: session.id === activeSessionId }"
        @click="handleTabClick(session.id)"
        @contextmenu.prevent="handleContextMenu($event, session)"
      >
        <span class="session-tab-title">{{ getSessionTitle(session) }}</span>
        <button 
          v-if="openedSessions.length > 0"
          class="session-tab-close"
          @click.stop="handleClose(session.id)"
        >
          <X :size="12" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useSessionStore } from '@/stores/session'
import { X, Plus } from 'lucide-vue-next'

const sessionStore = useSessionStore()

const openedSessions = computed(() => sessionStore.openedSessionsList)
const activeSessionId = computed(() => sessionStore.activeSessionId)

function getSessionTitle(session) {
  if (session.title && !session.title.startsWith('New session - ') && !session.title.startsWith('Child session - ')) {
    return session.title
  }
  
  // Generate a friendly title from the date
  if (session.time?.created) {
    const date = new Date(session.time.created)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  
  return 'Session'
}

async function handleTabClick(sessionId) {
  if (sessionId !== activeSessionId.value) {
    await sessionStore.switchSession(sessionId)
  }
}

async function handleNewSession() {
  await sessionStore.createNewSession()
}

function handleClose(sessionId) {
  sessionStore.closeSession(sessionId)
}

function handleContextMenu(event, session) {
  // Could add context menu for rename/delete here
  event.preventDefault()
}

// Load sessions on mount
onMounted(async () => {
  await sessionStore.loadSessions()
})
</script>

<style scoped>
.session-tabs {
  border-bottom: none;
  background: transparent;
  height: 100%;
}

.session-tabs-container {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: var(--muted) transparent;
  height: 100%;
  flex: 1;
  min-width: 0;
}

.session-tabs-container::-webkit-scrollbar {
  height: 4px;
}

.session-tabs-container::-webkit-scrollbar-track {
  background: transparent;
}

.session-tabs-container::-webkit-scrollbar-thumb {
  background: var(--muted);
  border-radius: var(--radius-sm);
}

.session-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full);
  border-bottom: none;
  background: transparent;
  color: var(--muted-foreground);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: 0;
  flex-shrink: 0;
  position: relative;
  height: 24px;
}

.session-tab:hover {
  background: color-mix(in srgb, var(--muted) 80%, var(--accent) 20%);
  color: var(--foreground);
}

.session-tab.active {
  background: var(--primary);
  color: var(--primary-foreground);
  font-weight: 500;
}

.session-tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.session-tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  border-radius: var(--radius-sm);
  opacity: 1;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.session-tab-close:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.session-tab-new {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  min-width: 24px;
  padding: 0;
  border: none;
  background: var(--accent);
  color: var(--muted-foreground);
  cursor: pointer;
  border-radius: var(--radius-full);
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.session-tab-new:hover {
  background: var(--muted);
  color: var(--foreground);
}
</style>

