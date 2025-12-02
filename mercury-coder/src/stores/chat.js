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
  const messageMap = ref(new Map()) // message ID → { info, parts: [] }
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
      } else {
        // Remove messages that don't belong to current session (in case session switched)
        if (messageMap.value.has(messageId)) {
          messageMap.value.delete(messageId)
          removedCount++
          console.log('[ChatStore] Removed message from map (wrong session):', messageId)
        }
      }
    })
    
    // Also remove any messages in messageMap that are no longer in events.messages
    // (handles case where messages were deleted)
    for (const [messageId, msg] of messageMap.value.entries()) {
      if (msg.info?.sessionID !== currentSessionId || !newMessageMap.has(messageId)) {
        messageMap.value.delete(messageId)
        removedCount++
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
  // Watch the local sessionId computed (which wraps opencode.sessionId.value)
  // This ensures we're watching the same value that turns computed uses
  watch(sessionId, async (newSessionId, oldSessionId) => {
    console.log('[ChatStore] Watch fired - newSessionId:', newSessionId, 'oldSessionId:', oldSessionId)
    
    if (newSessionId && newSessionId !== oldSessionId) {
      console.log('[ChatStore] Session changed from', oldSessionId, 'to', newSessionId)
      
      // Clear messageMap when switching sessions
      messageMap.value.clear()
      console.log('[ChatStore] Cleared messageMap for new session')
      
      // Mark that we're loading this session (for race condition handling)
      loadingSessionId = newSessionId
    }
    
    if (newSessionId) {
      const targetSessionId = newSessionId // Capture for async operations
      
      // Load existing messages from API (like OpenCode's sync.session.sync)
      // This ensures we have historical messages, not just new events
      try {
        console.log('[ChatStore] Loading messages from API for session:', targetSessionId)
        const apiMessages = await opencode.getMessages(100, targetSessionId)
        console.log('[ChatStore] Loaded', apiMessages.length, 'messages from API')
        
        // Check if session switched again during load (race condition)
        if (opencode.sessionId.value !== targetSessionId) {
          console.log('[ChatStore] Session switched during load, ignoring results for', targetSessionId)
          return
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
        console.log('[ChatStore] messageMap now has', messageMap.value.size, 'messages')
        
        // Also run syncMessagesFromEvents to catch any event-driven messages we might have missed
        // This ensures consistency between events.messages and messageMap
        syncMessagesFromEvents()
        
        console.log('[ChatStore] After sync, messageMap has', messageMap.value.size, 'messages')
        console.log('[ChatStore] Turns computed will show', turns.value.length, 'turns')
        
      } catch (err) {
        console.error('[ChatStore] Failed to load messages from API:', err)
        // Continue anyway - events might still provide messages
      }
      
      // Check session again before subscribing (handle race condition)
      // If session switched during API load, don't subscribe to old session
      if (opencode.sessionId.value !== targetSessionId) {
        console.log('[ChatStore] Session switched before subscribe, skipping subscription for', targetSessionId)
        return
      }
      
      // Subscribe to session-specific events for future updates
      // This provides real-time updates going forward
      console.log('[ChatStore] Subscribing to session-specific events:', targetSessionId)
      events.subscribe(targetSessionId)
      
      // Clear loading flag
      if (loadingSessionId === targetSessionId) {
        loadingSessionId = null
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
    // Expose for advanced usage
    opencode,
    events,
    messageMap // Expose for debugging
  }
})
