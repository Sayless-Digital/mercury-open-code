import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useOpencode } from '@/composables/useOpencode'
import { useProjectStore } from '@/stores/project'

export const useSessionStore = defineStore('session', () => {
  const opencode = useOpencode()
  const projectStore = useProjectStore()
  
  // List of all sessions
  const sessions = ref([])
  const activeSessionId = ref(null)
  // List of session IDs that are currently opened in tabs
  const openedSessions = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Computed: active session
  const activeSession = computed(() => {
    if (!activeSessionId.value) return null
    return sessions.value.find(s => s.id === activeSessionId.value) || null
  })

  // Computed: sessions sorted by updated time (newest first)
  const sortedSessions = computed(() => {
    return [...sessions.value].sort((a, b) => {
      const timeA = a.time?.updated || a.time?.created || 0
      const timeB = b.time?.updated || b.time?.created || 0
      return timeB - timeA
    })
  })

  // Computed: opened sessions (for tabs)
  const openedSessionsList = computed(() => {
    return openedSessions.value
      .map(id => sessions.value.find(s => s.id === id))
      .filter(Boolean)
      .sort((a, b) => {
        // Sort by order they were opened (maintain order in openedSessions array)
        const indexA = openedSessions.value.indexOf(a.id)
        const indexB = openedSessions.value.indexOf(b.id)
        return indexA - indexB
      })
  })

  /**
   * Load all sessions for the current project
   */
  async function loadSessions() {
    try {
      loading.value = true
      error.value = null
      
      const sessionList = await opencode.listSessions()
      sessions.value = sessionList || []
      
      // If no active session is set but we have sessions, use the most recent one
      if (!activeSessionId.value && sessions.value.length > 0) {
        const mostRecent = sortedSessions.value[0]
        // Add to opened sessions if not already there
        if (!openedSessions.value.includes(mostRecent.id)) {
          openedSessions.value.push(mostRecent.id)
        }
        await switchSession(mostRecent.id)
      } else if (!activeSessionId.value && sessions.value.length === 0) {
        // No sessions exist, create a new one
        await createNewSession()
      }
      
      return sessions.value
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Load sessions error:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new session
   */
  async function createNewSession(title = null) {
    try {
      loading.value = true
      error.value = null
      
      // Generate title if not provided
      if (!title) {
        const date = new Date()
        title = `Session ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
      }
      
      const newSession = await opencode.createSession(title)
      
      // Add to sessions list
      sessions.value.push(newSession)
      
      // Add to opened sessions
      if (!openedSessions.value.includes(newSession.id)) {
        openedSessions.value.push(newSession.id)
      }
      
      // Switch to the new session
      await switchSession(newSession.id)
      
      return newSession
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Create session error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Switch to a different session
   */
  async function switchSession(sessionId) {
    try {
      loading.value = true
      error.value = null
      
      // Verify session exists
      const session = sessions.value.find(s => s.id === sessionId)
      if (!session) {
        throw new Error(`Session ${sessionId} not found`)
      }
      
      // Switch in opencode composable
      await opencode.switchSession(sessionId)
      
      // Update active session
      activeSessionId.value = sessionId
      
      // Add to opened sessions if not already there
      if (!openedSessions.value.includes(sessionId)) {
        openedSessions.value.push(sessionId)
      }
      
      // Load messages for the new session
      // This will be handled by ChatPanel watching the sessionId
      
      return true
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Switch session error:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a session
   */
  async function deleteSession(sessionId) {
    try {
      loading.value = true
      error.value = null
      
      const success = await opencode.deleteSession(sessionId)
      
      if (success) {
        // Remove from sessions list
        sessions.value = sessions.value.filter(s => s.id !== sessionId)
        
        // If we deleted the active session, switch to another or create new
        if (activeSessionId.value === sessionId) {
          if (sessions.value.length > 0) {
            await switchSession(sortedSessions.value[0].id)
          } else {
            activeSessionId.value = null
            // Create a new session automatically
            await createNewSession()
          }
        }
      }
      
      return success
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Delete session error:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Update session title
   */
  async function updateSessionTitle(sessionId, title) {
    try {
      // Update via API
      const result = await opencode.client.value.session.update({
        path: { id: sessionId },
        body: { title }
      })
      
      if (result.data) {
        // Update in local list
        const index = sessions.value.findIndex(s => s.id === sessionId)
        if (index !== -1) {
          sessions.value[index] = { ...sessions.value[index], ...result.data }
        }
      }
      
      return result.data
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Update session title error:', err)
      throw err
    }
  }

  /**
   * Open a session (add to opened tabs)
   */
  function openSession(sessionId) {
    if (!openedSessions.value.includes(sessionId)) {
      openedSessions.value.push(sessionId)
    }
    // Switch to the session
    switchSession(sessionId)
  }

  /**
   * Close a session (remove from opened tabs, but don't delete)
   */
  function closeSession(sessionId) {
    const index = openedSessions.value.indexOf(sessionId)
    if (index !== -1) {
      openedSessions.value.splice(index, 1)
      
      // If we closed the active session, switch to another opened session
      if (activeSessionId.value === sessionId) {
        if (openedSessions.value.length > 0) {
          // Switch to the last opened session
          switchSession(openedSessions.value[openedSessions.value.length - 1])
        } else {
          // No more opened sessions, clear active
          activeSessionId.value = null
        }
      }
    }
  }

  /**
   * Initialize: Load sessions when project changes
   */
  watch(
    () => projectStore.currentProject?.path,
    async (newPath) => {
      if (newPath) {
        await loadSessions()
      } else {
        sessions.value = []
        activeSessionId.value = null
      }
    },
    { immediate: true }
  )

  return {
    sessions: computed(() => sessions.value),
    sortedSessions,
    openedSessions: computed(() => openedSessions.value),
    openedSessionsList,
    activeSessionId: computed(() => activeSessionId.value),
    activeSession,
    loading: computed(() => loading.value),
    error: computed(() => error.value),
    loadSessions,
    createNewSession,
    switchSession,
    deleteSession,
    updateSessionTitle,
    openSession,
    closeSession
  }
})

