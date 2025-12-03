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
  
  // Organize messages into "turns" (user message + assistant response)
  // Similar to OpenCode's SessionTurn structure
  const turns = computed(() => {
    const currentSessionId = sessionId.value
    if (!currentSessionId) {
      console.log('[ChatStore] No session ID, returning empty turns')
      return []
    }
    
    // Filter messages by current session ID
    const allMessages = Array.from(messageMap.value.values())
      .filter(msg => msg.info?.sessionID === currentSessionId)
    
    console.log('[ChatStore] Computing turns from', allMessages.length, 'messages for session', currentSessionId)
    
    // Log all messages for debugging
    allMessages.forEach(msg => {
      console.log('[ChatStore] Message:', {
        id: msg.info?.id,
        role: msg.info?.role,
        sessionID: msg.info?.sessionID,
        parentID: msg.info?.parentID,
        partsCount: msg.parts?.length || 0
      })
    })
    
    const userMessages = allMessages
      .filter(m => m.info?.role === 'user')
      .sort((a, b) => {
        const timeA = a.info?.time?.created || 0
        const timeB = b.info?.time?.created || 0
        return timeA - timeB
      })
    
    console.log('[ChatStore] Found', userMessages.length, 'user messages for session', currentSessionId)
    
    const turnsResult = userMessages.map(userMsg => {
      // Find assistant messages that are children of this user message
      const assistantMessages = allMessages
        .filter(m => {
          const isAssistant = m.info?.role === 'assistant'
          const hasParentID = m.info?.parentID === userMsg.info.id
          if (isAssistant) {
            console.log('[ChatStore] Checking assistant message:', {
              id: m.info.id,
              parentID: m.info.parentID,
              userMsgId: userMsg.info.id,
              matches: hasParentID
            })
          }
          return isAssistant && hasParentID
        })
        .sort((a, b) => {
          const timeA = a.info?.time?.created || 0
          const timeB = b.info?.time?.created || 0
          return timeA - timeB
        })
      
      console.log('[ChatStore] Turn for user message', userMsg.info.id, 'has', assistantMessages.length, 'assistant messages')
      
      return {
        id: userMsg.info.id,
        userMessage: userMsg,
        assistantMessages: assistantMessages,
        timestamp: new Date(userMsg.info?.time?.created || Date.now())
      }
    })
    
    console.log('[ChatStore] Computed', turnsResult.length, 'turns for session', currentSessionId)
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
  console.log('[ChatStore] Subscribing to global events')
  events.subscribe() // Global subscription (no session filter)
  
  /**
   * Sync messages from events.messages to messageMap, filtering by current sessionID
   * This ensures messageMap only contains messages for the current session
   */
  function syncMessagesFromEvents() {
    const currentSessionId = opencode.sessionId.value
    if (!currentSessionId) {
      console.log('[ChatStore] No current session ID, skipping message sync')
      return
    }
    
    const newMessageMap = events.messages.value
    console.log('[ChatStore] Syncing messages from events:', newMessageMap.size, 'for session:', currentSessionId)
    
    // Filter messages by current sessionID BEFORE copying to messageMap
    // This ensures messageMap only contains messages for the current session
    let addedCount = 0
    let removedCount = 0
    
    newMessageMap.forEach((msg, messageId) => {
      // Only add messages that belong to the current session
      if (msg.info?.sessionID === currentSessionId) {
        if (!messageMap.value.has(messageId)) {
          console.log('[ChatStore] Adding message to map:', {
            id: messageId,
            role: msg.info?.role,
            sessionID: msg.info?.sessionID,
            parentID: msg.info?.parentID,
            partsCount: msg.parts?.length || 0
          })
        }
        messageMap.value.set(messageId, msg)
        addedCount++
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
        removedCount++
        console.log('[ChatStore] Removed message from map (wrong session):', messageId)
      }
    }
    
    console.log('[ChatStore] Synced messages: added', addedCount, 'removed', removedCount, 'for session', currentSessionId)
    
    // Check if we got any assistant messages to clear loading
    const assistantMessages = Array.from(messageMap.value.values())
      .filter(msg => msg.info?.role === 'assistant' && msg.info?.sessionID === currentSessionId)
    
    console.log('[ChatStore] Found', assistantMessages.length, 'assistant messages in current session')
    
    if (assistantMessages.length > 0) {
      console.log('[ChatStore] Assistant message received, clearing loading state')
      assistantMessages.forEach(msg => {
        console.log('[ChatStore] Assistant message details:', {
          id: msg.info.id,
          parentID: msg.info.parentID,
          partsCount: msg.parts?.length || 0
        })
      })
      internalLoading.value = false
      // Also clear opencode.loading to ensure input is enabled
      if (opencode.clearLoading) {
        opencode.clearLoading()
      }
    }
    
    console.log('[ChatStore] Total messages in map:', messageMap.value.size, 'for session', currentSessionId)
    console.log('[ChatStore] Total turns:', turns.value.length)
  }

  // Track the current loading session to handle race conditions
  let loadingSessionId = null
  
  // Watch for session changes - load messages from API and subscribe to events
  // Following OpenCode's pattern: sync.session.sync(sessionID) loads messages, then events handle updates
  // Watch opencode.sessionId directly - it's a computed ref, so watch it as a source
  watch(opencode.sessionId, async (newSessionId, oldSessionId) => {
    console.log('[ChatStore] ======================================')
    console.log('[ChatStore] SESSION WATCH TRIGGERED')
    console.log('[ChatStore] New session:', newSessionId)
    console.log('[ChatStore] Old session:', oldSessionId)
    console.log('[ChatStore] ======================================')
    
    if (newSessionId && newSessionId !== oldSessionId) {
      console.log('[ChatStore] Session changed from', oldSessionId, 'to', newSessionId)
      
      // DON'T clear messageMap - keep all messages for all sessions
      // The turns computed property will filter by sessionID
      console.log('[ChatStore] Keeping existing messages in messageMap (', messageMap.value.size, 'messages)')
      
      // Mark that we're loading this session (for race condition handling)
      loadingSessionId = newSessionId
    }
    
    if (newSessionId) {
      const targetSessionId = newSessionId // Capture for async operations
      
      // Check if we've already loaded messages for this session
      if (loadedSessions.value.has(targetSessionId)) {
        console.log('[ChatStore] Session', targetSessionId, 'already loaded, skipping API call')
        // Just sync from events in case there are new messages
        syncMessagesFromEvents()
        return
      }
      
      // Load existing messages from API (like OpenCode's sync.session.sync)
      // This ensures we have historical messages, not just new events
      try {
        console.log('[ChatStore] Loading messages from API for session:', targetSessionId)
        const apiMessages = await opencode.getMessages(100, targetSessionId)
        console.log('[ChatStore] Loaded', apiMessages.length, 'messages from API for session', targetSessionId)
        
        // Check if session switched again during load (race condition)
        if (opencode.sessionId.value !== targetSessionId) {
          console.log('[ChatStore] Session switched during load, but keeping results for', targetSessionId, 'in cache')
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
      console.log('[ChatStore] Session is idle, clearing loading state')
      internalLoading.value = false
      // Also clear opencode.loading to ensure input is enabled
      if (opencode.clearLoading) {
        opencode.clearLoading()
      }
    } else if (status === 'busy') {
      // Don't set loading to true here - it's already set when sending a message
      // This is just for tracking
    }
  }, { immediate: true })
  
  /**
   * Transform OpenCode message format to UI format
   */
  function transformMessage(opencodeMsg) {
    if (!opencodeMsg?.info) {
      console.warn('[ChatStore] Invalid message:', opencodeMsg)
      return null
    }
    
    // Log assistant messages, especially if they have errors
    if (opencodeMsg.info.role === 'assistant') {
      console.log('[ChatStore] Transforming assistant message:', {
        id: opencodeMsg.info.id,
        hasError: !!opencodeMsg.info.error,
        error: opencodeMsg.info.error,
        partsCount: opencodeMsg.parts?.length || 0,
        finish: opencodeMsg.info.finish
      })
      
      if (opencodeMsg.info.error) {
        console.error('[ChatStore] Assistant message has error:', opencodeMsg.info.error)
      }
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
      // Check if this is the first message in the session (for auto-naming)
      const currentSessionId = opencode.sessionId.value
      const messagesInSession = currentSessionId 
        ? Array.from(messageMap.value.values()).filter(msg => msg.info?.sessionID === currentSessionId)
        : []
      const isFirstMessage = messagesInSession.length === 0
      
      // Set loading state - will be cleared when assistant message arrives or session goes idle
      internalLoading.value = true
      
      // Send message through OpenCode (creates session if needed)
      // Events are already subscribed (globally and session-specific)
      // Following official OpenCode pattern: prompt() is called without await, events handle the response
      // The user message will arrive via message.updated event, so we don't need to add it manually
      await opencode.sendMessage(text, {
        agent: options.agent || 'build',
        tools: options.tools || {},
        noReply: options.noReply || false
      })
      
      // If this was the first message, auto-rename the session based on the message
      // Do this after a short delay to ensure the session exists and message is saved
      if (isFirstMessage && opencode.sessionId.value) {
        setTimeout(async () => {
          try {
            console.log('[ChatStore] Auto-naming session after first message')
            await opencode.renameSessionWithAI(opencode.sessionId.value)
            
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
        }, 2000) // Wait 2 seconds for message to be saved
      }
      
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
    console.log('[ChatStore] ======================================')
    console.log('[ChatStore] loadMessagesForSession called')
    console.log('[ChatStore] Session ID:', sessionId)
    console.log('[ChatStore] Current opencode.sessionId.value:', opencode.sessionId.value)
    console.log('[ChatStore] ======================================')
    
    if (!sessionId) {
      console.log('[ChatStore] No session ID provided, skipping load')
      return
    }
    
    // Wait a tick for reactivity to settle
    await nextTick()
    console.log('[ChatStore] After nextTick, opencode.sessionId.value:', opencode.sessionId.value)
    
    const targetSessionId = sessionId
    
    // Check if we've already loaded this session
    if (loadedSessions.value.has(targetSessionId)) {
      console.log('[ChatStore] Session', targetSessionId, 'already loaded in cache')
      // Just sync from events and return
      syncMessagesFromEvents()
      
      // Log current state
      const messagesForTarget = Array.from(messageMap.value.values())
        .filter(msg => msg.info?.sessionID === targetSessionId)
      console.log('[ChatStore] Found', messagesForTarget.length, 'cached messages for session', targetSessionId)
      console.log('[ChatStore] Current turns:', turns.value.length)
      return
    }
    
    // DON'T clear messageMap - keep all messages for all sessions
    console.log('[ChatStore] Keeping existing messages in messageMap (', messageMap.value.size, 'messages)')
    
    // Load existing messages from API
    try {
      console.log('[ChatStore] Loading messages from API for session:', targetSessionId)
      const apiMessages = await opencode.getMessages(100, targetSessionId)
      console.log('[ChatStore] Loaded', apiMessages.length, 'messages from API for session', targetSessionId)
      
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
      
      console.log('[ChatStore] Added', addedToEvents, 'messages to events.messages and', addedToMap, 'to messageMap for session', targetSessionId)
      console.log('[ChatStore] messageMap now has', messageMap.value.size, 'total messages (all sessions)')
      console.log('[ChatStore] events.messages now has', events.messages.value.size, 'messages')
      
      // Mark this session as loaded
      loadedSessions.value.add(targetSessionId)
      console.log('[ChatStore] Marked session', targetSessionId, 'as loaded')
      
      // Verify messages for target session
      const messagesForTarget = Array.from(messageMap.value.values())
        .filter(msg => msg.info?.sessionID === targetSessionId)
      console.log('[ChatStore] Verified', messagesForTarget.length, 'messages belong to target session', targetSessionId)
      
      if (messagesForTarget.length > 0) {
        console.log('[ChatStore] First few messages for', targetSessionId + ':')
        messagesForTarget.slice(0, 3).forEach(msg => {
          console.log('  -', msg.info?.id, msg.info?.role)
        })
      }
      
      // Sync from events
      syncMessagesFromEvents()
      
      // Check turns
      console.log('[ChatStore] Turns for current session:', turns.value.length)
      
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
    // Expose for advanced usage
    opencode,
    events,
    messageMap // Expose for debugging
  }
})
