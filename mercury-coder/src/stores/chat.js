import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
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
    const allMessages = Array.from(messageMap.value.values())
    console.log('[ChatStore] Computing turns from', allMessages.length, 'messages')
    
    // Log all messages for debugging
    allMessages.forEach(msg => {
      console.log('[ChatStore] Message:', {
        id: msg.info?.id,
        role: msg.info?.role,
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
    
    console.log('[ChatStore] Found', userMessages.length, 'user messages')
    
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
    
    console.log('[ChatStore] Computed', turnsResult.length, 'turns')
    return turnsResult
  })
  
  // Legacy messages array for backward compatibility
  const messages = computed(() => {
    return Array.from(messageMap.value.values())
      .map(msg => transformMessage(msg))
      .filter(Boolean)
      .sort((a, b) => a.timestamp - b.timestamp)
  })
  
  // Subscribe to global events immediately to catch all events
  // This ensures we don't miss events that arrive before session-specific subscription
  console.log('[ChatStore] Subscribing to global events')
  events.subscribe() // Global subscription (no session filter)
  
  // Also subscribe to session-specific events when session is created or changed
  watch(() => opencode.sessionId.value, (newSessionId, oldSessionId) => {
    if (newSessionId && newSessionId !== oldSessionId) {
      console.log('[ChatStore] Session changed, clearing messages and subscribing to new session:', newSessionId)
      // Clear messages when switching sessions
      messageMap.value.clear()
      // Subscribe to session-specific events (this will filter events by session)
      events.subscribe(newSessionId)
    } else if (newSessionId) {
      console.log('[ChatStore] Session created, subscribing to session-specific events:', newSessionId)
      // Subscribe to session-specific events (this will filter events by session)
      events.subscribe(newSessionId)
    }
  }, { immediate: true })
  
  // Watch for message updates from event stream
  // Update messageMap directly (similar to OpenCode's global-sync)
  watch(() => events.messages.value, (newMessageMap) => {
    console.log('[ChatStore] Messages updated from events:', newMessageMap.size)
    
    // Update our messageMap with messages from events
    // This matches OpenCode's pattern: store.message[sessionID] and store.part[messageID]
    newMessageMap.forEach((msg, messageId) => {
      console.log('[ChatStore] Updating message in map:', {
        id: messageId,
        role: msg.info?.role,
        parentID: msg.info?.parentID,
        partsCount: msg.parts?.length || 0
      })
      messageMap.value.set(messageId, msg)
    })
    
    // Check if we got any assistant messages to clear loading
    const assistantMessages = Array.from(newMessageMap.values())
      .filter(msg => msg.info?.role === 'assistant')
    
    console.log('[ChatStore] Found', assistantMessages.length, 'assistant messages in update')
    
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
    
    console.log('[ChatStore] Total messages in map:', messageMap.value.size)
    console.log('[ChatStore] Total turns:', turns.value.length)
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
   * Clear all messages and create new session
   */
  async function clearMessages() {
    try {
      await opencode.clearSession()
      messageMap.value.clear()
      events.clear()
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
    // Direct access to message map (for advanced usage)
    messageMap: computed(() => messageMap.value),
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
    events
  }
})
