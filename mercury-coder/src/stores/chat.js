import { defineStore } from 'pinia'
import { ref, computed, watch, nextTick } from 'vue'
import { useOpencode, setSharedEvents } from '@/composables/useOpencode'
import { useOpencodeEvents } from '@/composables/useOpencodeEvents'

export const useChatStore = defineStore('chat', () => {
  // Create shared events instance FIRST, before useOpencode
  // This ensures useOpencode uses the same instance
  const events = useOpencodeEvents()
  setSharedEvents(events)
  
  const opencode = useOpencode()
  
  // Store messages similar to OpenCode structure: message ID → { info, parts: [] }
  // NOTE: We keep ALL messages from ALL sessions in this map, and filter by sessionID when displaying
  // This prevents data loss when switching between sessions quickly
  const messageMap = ref(new Map()) // message ID → { info, parts: [] }
  
  // Track which sessions have had their messages loaded from API
  const loadedSessions = ref(new Set())
  
  const internalLoading = ref(false)
  // Loading is true if OpenCode is loading OR if we're waiting for assistant response
  const loading = computed(() => opencode.loading.value || internalLoading.value)
  const error = computed(() => opencode.error.value)
  const sessionId = computed(() => opencode.sessionId.value)
  
  // Interrupt state - tracks how many times interrupt was pressed (like TUI)
  const interruptCount = ref(0)
  let interruptTimeout = null
  
  // Organize messages into "turns" (user message + assistant response)
  // Similar to OpenCode's SessionTurn structure
  const turns = computed(() => {
    const currentSessionId = sessionId.value
    if (!currentSessionId) {
      return []
    }
    
    // Filter messages by current session ID
    const allMessages = Array.from(messageMap.value.values())
      .filter(msg => msg.info?.sessionID === currentSessionId)
    
    const userMessages = allMessages
      .filter(m => m.info?.role === 'user')
      .sort((a, b) => {
        const timeA = a.info?.time?.created || 0
        const timeB = b.info?.time?.created || 0
        return timeA - timeB
      })
    
    const turnsResult = userMessages.map(userMsg => {
      // Find assistant messages that are children of this user message
      const assistantMessages = allMessages
        .filter(m => {
          const isAssistant = m.info?.role === 'assistant'
          const hasParentID = m.info?.parentID === userMsg.info.id
          return isAssistant && hasParentID
        })
        .sort((a, b) => {
          const timeA = a.info?.time?.created || 0
          const timeB = b.info?.time?.created || 0
          return timeA - timeB
        })
      
      return {
        id: userMsg.info.id,
        userMessage: userMsg,
        assistantMessages: assistantMessages,
        timestamp: new Date(userMsg.info?.time?.created || Date.now())
      }
    })
    
    return turnsResult
  })
  
  // Legacy messages array for backward compatibility
  const messages = computed(() => {
    const currentSessionId = sessionId.value
    if (!currentSessionId) return []
    
    return Array.from(messageMap.value.values())
      .filter(msg => msg.info?.sessionID === currentSessionId)
      .map(msg => transformMessage(msg))
      .filter(Boolean)
      .sort((a, b) => a.timestamp - b.timestamp)
  })
  
  // Subscribe to global events immediately to catch all events
  // This ensures we don't miss events that arrive before session-specific subscription
  events.subscribe() // Global subscription (no session filter)
  
  /**
   * Sync messages from events.messages to messageMap, filtering by current sessionID
   * This ensures messageMap only contains messages for the current session
   */
  function syncMessagesFromEvents() {
    const currentSessionId = opencode.sessionId.value
    if (!currentSessionId) return
    
    const newMessageMap = events.messages.value
    
    // Filter messages by current sessionID BEFORE copying to messageMap
    newMessageMap.forEach((msg, messageId) => {
      if (msg.info?.sessionID === currentSessionId) {
        messageMap.value.set(messageId, msg)
      }
    })
    
    // Remove messages from messageMap that don't belong to current session
    // NOTE: We don't check if messages are in events.messages because:
    // 1. events.messages is a global Map with ALL sessions' messages
    // 2. messageMap should only contain current session's messages
    // 3. When switching sessions, we want to keep messages in messageMap that we loaded from API
    //    even if they're not yet in events.messages
    for (const [messageId, msg] of messageMap.value.entries()) {
      if (msg.info?.sessionID !== currentSessionId) {
        messageMap.value.delete(messageId)
      }
    }
    
    // DON'T clear loading here - let session.status events handle that
    // Loading should stay true while session is busy, not just when assistant message arrives
    // The session can be busy even after assistant message starts (e.g., tools executing)
    const assistantMessages = Array.from(messageMap.value.values())
      .filter(msg => msg.info?.role === 'assistant' && msg.info?.sessionID === currentSessionId)
    
    // Auto-name session if this is the first assistant message (indicating first complete turn)
    if (assistantMessages.length > 0) {
      // Auto-name session if this is the first assistant message (indicating first complete turn)
      const userMessages = Array.from(messageMap.value.values())
        .filter(msg => msg.info?.role === 'user' && msg.info?.sessionID === currentSessionId)
      
      if (userMessages.length === 1 && assistantMessages.length === 1) {
        // This is the first complete turn - auto-name the session
        setTimeout(async () => {
          try {
            await opencode.renameSessionWithAI(currentSessionId)
            
            // Trigger session list refresh to update UI
            try {
              const { useSessionStore } = await import('./session')
              const sessionStore = useSessionStore()
              await sessionStore.loadSessions()
            } catch (err) {
              console.warn('[ChatStore] Could not refresh session list:', err)
            }
          } catch (err) {
            console.warn('[ChatStore] Failed to auto-name session:', err)
            // Non-critical, don't throw
          }
        }, 1000) // Wait 1 second to ensure message is fully saved
      }
    }
  }

  // Track the current loading session to handle race conditions
  let loadingSessionId = null
  
  // Watch for session changes - load messages from API and subscribe to events
  // Following OpenCode's pattern: sync.session.sync(sessionID) loads messages, then events handle updates
  // Watch opencode.sessionId directly - it's a computed ref, so watch it as a source
  watch(opencode.sessionId, async (newSessionId, oldSessionId) => {
    // Reduced logging spam - commented out verbose session switch logs
    // console.log('[ChatStore] ======================================')
    // console.log('[ChatStore] SESSION WATCH TRIGGERED')
    // console.log('[ChatStore] New session:', newSessionId)
    // console.log('[ChatStore] Old session:', oldSessionId)
    // console.log('[ChatStore] ======================================')
    
    if (newSessionId && newSessionId !== oldSessionId) {
      // console.log('[ChatStore] Session changed from', oldSessionId, 'to', newSessionId)
      
      // DON'T clear messageMap - keep all messages for all sessions
      // The turns computed property will filter by sessionID
      // console.log('[ChatStore] Keeping existing messages in messageMap (', messageMap.value.size, 'messages)')
      
      // Mark that we're loading this session (for race condition handling)
      loadingSessionId = newSessionId
    }
    
    if (newSessionId) {
      const targetSessionId = newSessionId // Capture for async operations
      
      // Check if we've already loaded messages for this session
      if (loadedSessions.value.has(targetSessionId)) {
        // console.log('[ChatStore] Session', targetSessionId, 'already loaded, skipping API call')
        // Just sync from events in case there are new messages
        syncMessagesFromEvents()
        return
      }
      
      // Load existing messages from API (like OpenCode's sync.session.sync)
      // This ensures we have historical messages, not just new events
      try {
        // console.log('[ChatStore] Loading messages from API for session:', targetSessionId)
        const apiMessages = await opencode.getMessages(100, targetSessionId)
        // console.log('[ChatStore] Loaded', apiMessages.length, 'messages from API for session', targetSessionId)
        
        // Check if session switched again during load (race condition)
        if (opencode.sessionId.value !== targetSessionId) {
          // console.log('[ChatStore] Session switched during load, but keeping results for', targetSessionId, 'in cache')
          // Continue processing - we want to cache these messages even if user switched away
        }
        
        // Add messages directly to both events.messages and messageMap
        // This ensures immediate UI update and maintains consistency
        let addedToEvents = 0
        let addedToMap = 0
        
        apiMessages.forEach(msg => {
          const messageId = msg.info?.id
          if (!messageId) {
            console.warn('[ChatStore] Message missing ID:', msg)
            return
          }
          
          if (msg.info?.sessionID !== targetSessionId) {
            console.warn('[ChatStore] Message sessionID mismatch:', {
              messageId,
              messageSessionID: msg.info?.sessionID,
              targetSessionId
            })
            return
          }
          
          const messageData = {
            info: msg.info,
            parts: msg.parts || []
          }
          
          // Add to events.messages (for consistency with event-driven messages)
          const existingInEvents = events.messages.value.get(messageId)
          if (existingInEvents) {
            // Merge parts if events has more complete data
            const mergedParts = existingInEvents.parts.length > messageData.parts.length
              ? existingInEvents.parts
              : messageData.parts
            events.messages.value.set(messageId, {
              info: msg.info,
              parts: mergedParts
            })
          } else {
            events.messages.value.set(messageId, messageData)
          }
          addedToEvents++
          
          // Also add directly to messageMap (immediate UI update)
          messageMap.value.set(messageId, messageData)
          addedToMap++
        })
        
        console.log('[ChatStore] Added', addedToEvents, 'messages to events.messages and', addedToMap, 'to messageMap for session', targetSessionId)
        console.log('[ChatStore] messageMap now has', messageMap.value.size, 'total messages (all sessions)')
        console.log('[ChatStore] events.messages now has', events.messages.value.size, 'messages')
        
        // Mark this session as loaded
        loadedSessions.value.add(targetSessionId)
        console.log('[ChatStore] Marked session', targetSessionId, 'as loaded')
        
        // Log the messages we just added for debugging
        const messagesForTarget = Array.from(messageMap.value.values())
          .filter(msg => msg.info?.sessionID === targetSessionId)
        console.log('[ChatStore] Verified', messagesForTarget.length, 'messages belong to target session', targetSessionId)
        
        if (messagesForTarget.length > 0) {
          console.log('[ChatStore] Messages for target session:')
          messagesForTarget.forEach(msg => {
            console.log('  -', msg.info?.id, msg.info?.role)
          })
        }
        
        // Also run syncMessagesFromEvents to catch any event-driven messages we might have missed
        // This ensures consistency between events.messages and messageMap
        syncMessagesFromEvents()
        
        console.log('[ChatStore] After sync, messageMap has', messageMap.value.size, 'total messages')
        console.log('[ChatStore] Turns for current session:', turns.value.length)
        
      } catch (err) {
        console.error('[ChatStore] Failed to load messages from API:', err)
        // Continue anyway - events might still provide messages
      }
    }
  }, { immediate: true })
  
  // Watch for message updates from event stream
  // Update messageMap directly (similar to OpenCode's global-sync)
  // CRITICAL: Filter by current sessionID BEFORE copying to messageMap
  watch(() => events.messages.value, () => {
    syncMessagesFromEvents()
  }, { deep: true })
  
  // Watch for session status events to manage loading state
  // Use a computed to track the latest session status
  const latestSessionStatus = computed(() => {
    const eventList = events.events.value
    if (eventList.length === 0) return null
    
    // Find the most recent session.idle or session.status event
    for (let i = eventList.length - 1; i >= 0; i--) {
      const event = eventList[i]
      const eventType = event?.payload?.type
      
      if (eventType === 'session.idle') {
        return 'idle'
      } else if (eventType === 'session.status') {
        const statusType = event?.payload?.properties?.status?.type
        if (statusType === 'idle') {
          return 'idle'
        } else if (statusType === 'busy') {
          return 'busy'
        }
      }
    }
    return null
  })
  
  // Watch for session status changes and update loading state
  watch(latestSessionStatus, (status) => {
    if (status === 'idle') {
      internalLoading.value = false
      if (opencode.clearLoading) {
        opencode.clearLoading()
      }
    } else if (status === 'busy') {
      internalLoading.value = true
      // Also ensure opencode.loading is true
      if (!opencode.loading.value) {
        // Set it via the composable if there's a way, or just track it
        // The opencode.loading should be managed by the session status
      }
    }
  }, { immediate: true })
  
  // Also watch for session.status events directly to catch busy state
  watch(() => events.events.value, (eventList) => {
    // Find the most recent session.status event
    for (let i = eventList.length - 1; i >= 0; i--) {
      const event = eventList[i]
      const payload = event?.payload
      if (payload?.type === 'session.status' && payload?.properties?.status) {
        const statusType = payload.properties.status.type
        if (statusType === 'busy') {
          internalLoading.value = true
          break
        } else if (statusType === 'idle') {
          internalLoading.value = false
          if (opencode.clearLoading) {
            opencode.clearLoading()
          }
          break
        }
      }
      // Also check for session.error events (abort triggers this)
      if (payload?.type === 'session.error') {
        internalLoading.value = false
        if (opencode.clearLoading) {
          opencode.clearLoading()
        }
        break
      }
    }
  }, { deep: true })
  
  /**
   * Transform OpenCode message format to UI format
   */
  function transformMessage(opencodeMsg) {
    if (!opencodeMsg?.info) {
      console.warn('[ChatStore] Invalid message:', opencodeMsg)
      return null
    }
    
    // Handle assistant messages - only log errors or first-time transformations
    if (opencodeMsg.info.role === 'assistant') {
      const hasError = !!opencodeMsg.info.error
      const isAborted = opencodeMsg.info.error?.name === 'MessageAbortedError'
      
      // Only log actual errors (not aborted messages - those are expected)
      if (hasError && !isAborted) {
        console.error('[ChatStore] Assistant message has error:', opencodeMsg.info.error)
      } else if (isAborted) {
        // Aborted messages are expected when user interrupts - don't log them
        // Mark message as finished when aborted (so status indicators stop)
        // Use a special finish value to indicate it was aborted
        if (opencodeMsg.info.finish === undefined) {
          // Set finish to a truthy value so the status indicator stops
          opencodeMsg.info.finish = 'aborted'
        }
        // Clear loading state when message is aborted
        internalLoading.value = false
        if (opencode.clearLoading) {
          opencode.clearLoading()
        }
      }
      // Removed the general log for every transformation - it was causing thousands of logs
    }
    
    return {
      id: opencodeMsg.info.id,
      role: opencodeMsg.info.role || 'assistant',
      content: extractTextParts(opencodeMsg.parts || []),
      tools: extractToolParts(opencodeMsg.parts || []),
      streaming: opencodeMsg.info.finish === undefined,
      timestamp: new Date(opencodeMsg.info.time?.created || Date.now()),
      model: opencodeMsg.info.model,
      tokens: opencodeMsg.info.tokens,
      cost: opencodeMsg.info.cost,
      finish: opencodeMsg.info.finish,
      error: opencodeMsg.info.error // Include error if present
    }
  }
  
  /**
   * Extract text content from message parts
   */
  function extractTextParts(parts) {
    return parts
      .filter(p => p.type === 'text')
      .map(p => p.text)
      .join('')
  }
  
  /**
   * Extract tool calls from message parts
   */
  function extractToolParts(parts) {
    return parts
      .filter(p => p.type === 'tool')
      .map(p => ({
        id: p.callID,
        name: p.tool,
        input: p.state?.input,
        status: p.state?.status || 'running',
        output: p.state?.output,
        error: p.state?.error
      }))
  }
  
  /**
   * Send a message to OpenCode
   */
  async function sendMessage(text, options = {}) {
    if (!text.trim()) return
    
    try {
      // Set loading state - will be cleared when assistant message arrives or session goes idle
      internalLoading.value = true
      
      // Send message through OpenCode (creates session if needed)
      await opencode.sendMessage(text, {
        agent: options.agent || 'build',
        tools: options.tools || {},
        noReply: options.noReply || false
      })
      
      // Note: Auto-naming is handled in the syncMessagesFromEvents function
      // when we detect this is the first user message in a session
      
      // Note: The user and assistant messages will arrive via message.updated and message.part.updated events
      // Loading will be set to false when assistant message arrives or session.idle event fires
      
      // Note: Event subscription is handled by watch() on sessionId above
      // No need to subscribe here - it's already set up
    } catch (err) {
      console.error('[ChatStore] Send message failed:', err)
      internalLoading.value = false
      throw err
    }
  }
  
  /**
   * Send streaming message (compatible with old API)
   */
  async function sendMessageStream(text, context = {}, onChunk) {
    // OpenCode handles streaming automatically via events
    return sendMessage(text, context)
  }
  
  /**
   * Clear all messages (without creating a new session)
   */
  async function clearMessages() {
    try {
      await opencode.clearSession()
      messageMap.value.clear()
      events.clear() // Clear events as well
    } catch (err) {
      console.error('[ChatStore] Clear messages failed:', err)
    }
  }
  
  /**
   * Cancel current workflow/operation
   */
  async function cancelWorkflow() {
    try {
      await opencode.abortSession()
    } catch (err) {
      console.error('[ChatStore] Cancel workflow failed:', err)
    }
  }
  
  /**
   * Interrupt the current session
   * Following OpenCode TUI pattern: first press increments counter, second press (within 5s) aborts
   */
  async function interruptSession() {
    if (!sessionId.value) return
    
    // Clear any existing timeout
    if (interruptTimeout) {
      clearTimeout(interruptTimeout)
    }
    
    // Increment interrupt count
    interruptCount.value = interruptCount.value + 1
    
    console.log('[ChatStore] Interrupt pressed, count:', interruptCount.value)
    
    // If interrupted twice (or more), abort the session
    if (interruptCount.value >= 2) {
      console.log('[ChatStore] Interrupt count >= 2, aborting session')
      interruptCount.value = 0
      try {
        await opencode.abortSession()
        // Clear loading state immediately after abort
        internalLoading.value = false
        if (opencode.clearLoading) {
          opencode.clearLoading()
        }
      } catch (err) {
        console.error('[ChatStore] Interrupt abort failed:', err)
        // Still clear loading even if abort fails
        internalLoading.value = false
        if (opencode.clearLoading) {
          opencode.clearLoading()
        }
      }
      return
    }
    
    // Reset interrupt count after 5 seconds (like TUI)
    interruptTimeout = setTimeout(() => {
      interruptCount.value = 0
      console.log('[ChatStore] Interrupt count reset')
    }, 5000)
  }
  
  /**
   * Pause workflow (compatibility stub)
   */
  async function pauseWorkflow() {
    console.warn('[ChatStore] Pause not supported in OpenCode')
  }
  
  /**
   * Resume workflow (compatibility stub)
   */
  async function resumeWorkflow() {
    console.warn('[ChatStore] Resume not supported in OpenCode')
  }
  
  /**
   * Get workflow status (compatibility stub)
   */
  async function getWorkflowStatus() {
    return {
      success: true,
      status: {
        state: 'running',
        statusMessage: 'Active'
      }
    }
  }
  
  /**
   * Manually load messages for a specific session
   * This is called by SessionStore when switching sessions
   */
  async function loadMessagesForSession(sessionId) {
    if (!sessionId) {
      return
    }
    
    // Wait a tick for reactivity to settle
    await nextTick()
    
    const targetSessionId = sessionId
    
    // Check if we've already loaded this session
    if (loadedSessions.value.has(targetSessionId)) {
      // Just sync from events and return
      syncMessagesFromEvents()
      return
    }
    
    // DON'T clear messageMap - keep all messages for all sessions
      // Load existing messages from API
      try {
        const apiMessages = await opencode.getMessages(100, targetSessionId)
      
      // Add messages directly to both events.messages and messageMap
      let addedToEvents = 0
      let addedToMap = 0
      
      apiMessages.forEach(msg => {
        const messageId = msg.info?.id
        if (!messageId) {
          console.warn('[ChatStore] Message missing ID:', msg)
          return
        }
        
        if (msg.info?.sessionID !== targetSessionId) {
          console.warn('[ChatStore] Message sessionID mismatch:', {
            messageId,
            messageSessionID: msg.info?.sessionID,
            targetSessionId
          })
          return
        }
        
        const messageData = {
          info: msg.info,
          parts: msg.parts || []
        }
        
        // Add to events.messages
        const existingInEvents = events.messages.value.get(messageId)
        if (existingInEvents) {
          const mergedParts = existingInEvents.parts.length > messageData.parts.length
            ? existingInEvents.parts
            : messageData.parts
          events.messages.value.set(messageId, {
            info: msg.info,
            parts: mergedParts
          })
        } else {
          events.messages.value.set(messageId, messageData)
        }
        addedToEvents++
        
        // Also add directly to messageMap
        messageMap.value.set(messageId, messageData)
        addedToMap++
      })
      
        // Mark this session as loaded
        loadedSessions.value.add(targetSessionId)
        
        // Sync from events
        syncMessagesFromEvents()
      
    } catch (err) {
      console.error('[ChatStore] Failed to load messages from API:', err)
    }
    
    // Subscribe to session-specific events
    console.log('[ChatStore] Subscribing to session-specific events:', targetSessionId)
    events.subscribe(targetSessionId)
  }
  
  return {
    // Legacy messages array (for backward compatibility)
    messages,
    // New turn-based structure (matches OpenCode's SessionTurn)
    turns,
    loading,
    error,
    sessionId,
    sendMessage,
    sendMessageStream,
    clearMessages,
    cancelWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    getWorkflowStatus,
    loadMessagesForSession, // For manual session switching
    interruptSession, // Interrupt running session
    interruptCount, // Expose interrupt count for UI feedback
    // Expose for advanced usage
    opencode,
    events,
    messageMap // Expose for debugging
  }
})
