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
    
    <!-- Context Menu -->
    <div 
      v-if="contextMenu.show"
      ref="contextMenuRef"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
    >
      <button @click="handleRenameManual" class="context-menu-item">
        <Edit3 :size="14" />
        Rename Manually
      </button>
      <button @click="handleRenameAI" class="context-menu-item">
        <Sparkles :size="14" />
        Rename with AI
      </button>
      <button @click="handleDeleteSession" class="context-menu-item destructive">
        <Trash2 :size="14" />
        Delete Session
      </button>
    </div>
    
    <!-- Rename Dialog -->
    <div v-if="renameDialog.show" class="dialog-overlay" @click="closeRenameDialog">
      <div class="dialog" @click.stop>
        <h3>Rename Session</h3>
        <input 
          ref="renameInputRef"
          v-model="renameDialog.title"
          type="text"
          class="rename-input"
          placeholder="Enter new session name"
          @keyup.enter="saveRename"
          @keyup.esc="closeRenameDialog"
        />
        <div class="dialog-buttons">
          <button @click="closeRenameDialog" class="btn btn-secondary">Cancel</button>
          <button @click="saveRename" class="btn btn-primary">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, nextTick, onBeforeUnmount } from 'vue'
import { useSessionStore } from '@/stores/session'
import { X, Plus, Edit3, Sparkles, Trash2 } from 'lucide-vue-next'

const sessionStore = useSessionStore()

const openedSessions = computed(() => sessionStore.openedSessionsList)
const activeSessionId = computed(() => sessionStore.activeSessionId)

// Context menu state
const contextMenu = ref({
  show: false,
  x: 0,
  y: 0,
  session: null
})

// Rename dialog state
const renameDialog = ref({
  show: false,
  title: '',
  sessionId: null
})

const contextMenuRef = ref(null)
const renameInputRef = ref(null)

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
  event.preventDefault()
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    session: session
  }
}

function closeContextMenu() {
  contextMenu.value.show = false
}

function handleRenameManual() {
  renameDialog.value = {
    show: true,
    title: contextMenu.value.session.title || '',
    sessionId: contextMenu.value.session.id
  }
  closeContextMenu()
  
  // Focus input after it's rendered
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

async function handleRenameAI() {
  const sessionId = contextMenu.value.session.id
  closeContextMenu()
  
  try {
    await sessionStore.renameSessionWithAI(sessionId)
  } catch (err) {
    console.error('Failed to rename session with AI:', err)
    alert('Failed to rename session. Please try again.')
  }
}

async function handleDeleteSession() {
  const sessionId = contextMenu.value.session.id
  closeContextMenu()
  
  if (confirm('Are you sure you want to delete this session?')) {
    await sessionStore.deleteSession(sessionId)
  }
}

function closeRenameDialog() {
  renameDialog.value.show = false
}

async function saveRename() {
  const { sessionId, title } = renameDialog.value
  if (title.trim()) {
    try {
      await sessionStore.updateSessionTitle(sessionId, title.trim())
      closeRenameDialog()
    } catch (err) {
      console.error('Failed to rename session:', err)
      alert('Failed to rename session. Please try again.')
    }
  }
}

// Close context menu when clicking outside
function handleClickOutside(event) {
  if (contextMenu.value.show && contextMenuRef.value && !contextMenuRef.value.contains(event.target)) {
    closeContextMenu()
  }
}

onMounted(async () => {
  await sessionStore.loadSessions()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
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

/* Context Menu */
.context-menu {
  position: fixed;
  z-index: 1000;
  background: var(--popover);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: var(--space-1);
  min-width: 180px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  color: var(--foreground);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.2s ease;
}

.context-menu-item:hover {
  background: var(--accent);
}

.context-menu-item.destructive {
  color: var(--destructive);
}

.context-menu-item.destructive:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

/* Dialog Overlay */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.dialog {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  min-width: 400px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.dialog h3 {
  margin: 0 0 var(--space-4) 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--foreground);
}

.rename-input {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--background);
  color: var(--foreground);
  font-size: 14px;
  font-family: inherit;
  margin-bottom: var(--space-4);
}

.rename-input:focus {
  outline: none;
  border-color: var(--primary);
}

.dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--primary);
  color: var(--primary-foreground);
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-secondary {
  background: var(--secondary);
  color: var(--secondary-foreground);
}

.btn-secondary:hover {
  background: var(--muted);
}
</style>

