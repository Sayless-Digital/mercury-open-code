import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useOpencode } from '@/composables/useOpencode'
import { useProjectStore } from '@/stores/project'

export const useSessionStore = defineStore('session', () => {
  const opencode = useOpencode()
  const projectStore = useProjectStore()
  
  // Simple: just store sessions locally
  const sessions = ref([])
  const activeSessionId = ref(null)
  const openedSessions = ref([])
  const loading = ref(false)
  const error = ref(null)

  /**
   * Get storage key for current project
   */
  function getStorageKey() {
    const projectPath = projectStore.currentProject?.path
    if (!projectPath) return null
    // Create a safe key from project path
    return `mercury-session-state:${projectPath}`
  }

  /**
   * Save session state to localStorage
   */
  function saveSessionState() {
    const key = getStorageKey()
    if (!key) return
    
    try {
      const state = {
        activeSessionId: activeSessionId.value,
        openedSessions: openedSessions.value,
        timestamp: Date.now()
      }
      localStorage.setItem(key, JSON.stringify(state))
      console.log('[SessionStore] Saved session state for project:', projectStore.currentProject?.path)
    } catch (err) {
      console.warn('[SessionStore] Failed to save session state:', err)
    }
  }

  /**
   * Load session state from localStorage
   */
  function loadSessionState() {
    const key = getStorageKey()
    if (!key) return null
    
    try {
      const stored = localStorage.getItem(key)
      if (!stored) return null
      
      const state = JSON.parse(stored)
      console.log('[SessionStore] Loaded session state for project:', projectStore.currentProject?.path, state)
      return state
    } catch (err) {
      console.warn('[SessionStore] Failed to load session state:', err)
      return null
    }
  }

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
   * Load all sessions for the current project - simple approach
   */
  async function loadSessions() {
    try {
      loading.value = true
      error.value = null
      
      // Simple: just fetch sessions from opencode
      const result = await opencode.client.value.session.list()
      sessions.value = result.data || []
      
      // Try to restore persisted state
      const persistedState = loadSessionState()
      
      if (persistedState && persistedState.activeSessionId && persistedState.openedSessions) {
        // Verify persisted sessions still exist
        const validOpenedSessions = persistedState.openedSessions.filter(id => 
          sessions.value.some(s => s.id === id)
        )
        const validActiveSession = sessions.value.some(s => s.id === persistedState.activeSessionId)
        
        if (validOpenedSessions.length > 0) {
          // Restore opened sessions
          openedSessions.value = validOpenedSessions
          console.log('[SessionStore] Restored', validOpenedSessions.length, 'opened sessions')
          
          // Restore active session if it's still valid
          if (validActiveSession) {
            await switchSession(persistedState.activeSessionId)
            console.log('[SessionStore] Restored active session:', persistedState.activeSessionId)
            return sessions.value
          } else if (validOpenedSessions.length > 0) {
            // Active session is gone, but we have opened sessions - use first one
            await switchSession(validOpenedSessions[0])
            console.log('[SessionStore] Active session no longer exists, switched to first opened session')
            return sessions.value
          }
        }
      }
      
      // No persisted state or invalid persisted state - use default behavior
      // If no active session is set but we have sessions, use the most recent one
      if (!activeSessionId.value && sessions.value.length > 0) {
        const mostRecent = sortedSessions.value[0]
        // Add to opened sessions if not already there
        if (!openedSessions.value.includes(mostRecent.id)) {
          openedSessions.value.push(mostRecent.id)
        }
        await switchSession(mostRecent.id)
      } else if (!activeSessionId.value && sessions.value.length === 0) {
        // No sessions exist - don't create automatically, let user decide
        console.log('[SessionStore] No sessions exist and no persisted state - waiting for user to create session')
      }
      
      // Save state after loading
      saveSessionState()
      
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
      
      // Add the newly created session to sessions immediately
      const existingIndex = sessions.value.findIndex(s => s.id === newSession.id)
      if (existingIndex === -1) {
        sessions.value.push(newSession)
        console.log('[SessionStore] Added new session:', newSession.id)
      } else {
        // Update if it already exists (shouldn't happen for new sessions, but just in case)
        sessions.value[existingIndex] = newSession
      }
      
      // Add to opened sessions
      if (!openedSessions.value.includes(newSession.id)) {
        openedSessions.value.push(newSession.id)
      }
      
      // Switch to the new session
      await switchSession(newSession.id)
      
      // Save state after creating
      saveSessionState()
      
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
      
      console.log('[SessionStore] Switching to session:', sessionId)
      
      // Update active session FIRST
      activeSessionId.value = sessionId
      
      // Add to opened sessions if not already there
      if (!openedSessions.value.includes(sessionId)) {
        openedSessions.value.push(sessionId)
      }
      
      // Switch the session ID in opencode
      await opencode.switchSession(sessionId)
      
      // Wait for Vue reactivity to settle
      await new Promise(resolve => setTimeout(resolve, 0))
      
      // Manually trigger message loading in ChatStore
      // This is needed because the watch in ChatStore doesn't fire for some reason
      const { useChatStore } = await import('./chat')
      const chatStore = useChatStore()
      await chatStore.loadMessagesForSession(sessionId)
      
      // Save state after switching
      saveSessionState()
      
      console.log('[SessionStore] Session switched successfully to:', sessionId)
      
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
        const index = sessions.value.findIndex(s => s.id === sessionId)
        if (index !== -1) {
          sessions.value.splice(index, 1)
        }
        
        // Remove from opened sessions
        const openedIndex = openedSessions.value.indexOf(sessionId)
        if (openedIndex !== -1) {
          openedSessions.value.splice(openedIndex, 1)
        }
        
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
      const result = await opencode.updateSession(sessionId, { title })
      
      if (result) {
        // Update in sessions list
        const index = sessions.value.findIndex(s => s.id === sessionId)
        if (index !== -1) {
          sessions.value[index] = result
        }
        
        // Save state
        saveSessionState()
      }
      
      return result
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Update session title error:', err)
      throw err
    }
  }

  /**
   * Rename session using AI (generates title from conversation)
   */
  async function renameSessionWithAI(sessionId) {
    try {
      loading.value = true
      console.log('[SessionStore] Renaming session with AI:', sessionId)
      
      const result = await opencode.renameSessionWithAI(sessionId)
      
      if (result) {
        // Update in sessions list
        const index = sessions.value.findIndex(s => s.id === sessionId)
        if (index !== -1) {
          sessions.value[index] = result
        }
        
        // Save state
        saveSessionState()
        
        console.log('[SessionStore] Session renamed to:', result.title)
      }
      
      return result
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Rename session with AI error:', err)
      throw err
    } finally {
      loading.value = false
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
      
      // Save state after closing
      saveSessionState()
    }
  }

  /**
   * Clear all sessions (delete all sessions from the backend)
   */
  async function clearAllSessions() {
    try {
      loading.value = true
      error.value = null
      
      console.log('[SessionStore] Clearing all sessions...')
      
      // Delete all sessions one by one
      const sessionsToDelete = [...sessions.value]
      for (const session of sessionsToDelete) {
        try {
          await opencode.deleteSession(session.id)
        } catch (err) {
          console.warn('[SessionStore] Failed to delete session', session.id, ':', err)
        }
      }
      
      // Clear UI state
      activeSessionId.value = null
      openedSessions.value = []
      sessions.value = []
      
      // Create a new session
      await createNewSession()
      
      console.log('[SessionStore] All sessions cleared')
      return true
    } catch (err) {
      error.value = err.message
      console.error('[SessionStore] Clear all sessions error:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Initialize: Load sessions when project changes
   */
  watch(
    () => projectStore.currentProject?.path,
    async (newPath, oldPath) => {
      // Save state for old project before switching
      if (oldPath) {
        saveSessionState()
      }
      
      if (newPath) {
        // Clear state before loading new project
        activeSessionId.value = null
        openedSessions.value = []
        await loadSessions()
      } else {
        activeSessionId.value = null
        sessions.value = []
        openedSessions.value = []
      }
    },
    { immediate: true }
  )

  return {
    // Sessions
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
    renameSessionWithAI,
    openSession,
    closeSession,
    clearAllSessions
  }
})

