/**
 * OpenCode Events Composable
 * Handles real-time Server-Sent Events (SSE) from OpenCode
 */

import { ref, onUnmounted } from 'vue'
import { createOpencodeClient } from '@opencode-ai/sdk/client'

const OPENCODE_URL = 'http://127.0.0.1:4096'

export function useOpencodeEvents() {
  const client = createOpencodeClient({ baseUrl: OPENCODE_URL })
  
  const events = ref([])
  const messages = ref(new Map()) // message ID → { info, parts: [] }
  const tools = ref(new Map())    // call ID → tool state
  const connected = ref(false)
  
  let abortController = null
  let eventStream = null
  
  /**
   * Add a message from prompt() response directly to the messages map
   * This ensures messages from prompt() are available even if events haven't arrived yet
   */
  function addMessageFromPrompt(promptResponse) {
    if (!promptResponse?.info) {
      console.warn('[useOpencodeEvents] Invalid prompt response:', promptResponse)
      return
    }
    
    const messageId = promptResponse.info.id
    console.log('[useOpencodeEvents] Adding message from prompt() response:', messageId, promptResponse.info.role)
    
    // Add or update the message in the map
    messages.value.set(messageId, {
      info: promptResponse.info,
      parts: promptResponse.parts || []
    })
    
    console.log('[useOpencodeEvents] Message added, total messages:', messages.value.size)
  }
  
  /**
   * Subscribe to OpenCode events for a specific session
   */
  async function subscribe(sessionId = null) {
    // Cleanup existing subscription
    if (abortController) {
      abortController.abort()
    }
    
    abortController = new AbortController()
    
    try {
      // Subscribe to event stream - following official OpenCode pattern
      // This matches: sdk.global.event().then(async (events) => { for await (const event of events.stream) { ... } })
      const eventsResult = await client.global.event({
        query: sessionId ? { session: sessionId } : {}
      })
      
      console.log('[useOpencodeEvents] Event result type:', typeof eventsResult)
      console.log('[useOpencodeEvents] Event result keys:', Object.keys(eventsResult || {}))
      
      // SDK returns { stream: AsyncGenerator } for SSE
      // Following official pattern: events.stream
      const stream = eventsResult?.stream || eventsResult?.data?.stream
      
      if (!stream) {
        console.error('[useOpencodeEvents] No stream in result:', eventsResult)
        throw new Error('No stream in event response')
      }
      
      connected.value = true
      eventStream = stream
      
      console.log('[useOpencodeEvents] Subscribed to event stream', sessionId ? `for session ${sessionId}` : '(global)')
      console.log('[useOpencodeEvents] Starting to consume stream...')
      
      // Iterate over the SSE events - matches official pattern exactly
      let eventCount = 0
      for await (const event of stream) {
        eventCount++
        console.log(`[useOpencodeEvents] Received event #${eventCount}:`, event)
        events.value.push(event)
        handleEvent(event)
        
        if (abortController.signal.aborted) break
      }
      
      console.log('[useOpencodeEvents] Stream ended after', eventCount, 'events')
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('[useOpencodeEvents] Stream error:', err)
        connected.value = false
      }
    }
  }
  
  /**
   * Handle individual event
   */
  function handleEvent(event) {
    console.log('[useOpencodeEvents] Full event object:', JSON.stringify(event, null, 2))
    console.log('[useOpencodeEvents] Event keys:', Object.keys(event))
    
    // OpenCode wraps events with { directory, payload: { type, properties } }
    const payload = event.payload || event
    const eventType = payload.type
    const properties = payload.properties
    
    console.log('[useOpencodeEvents] Event type:', eventType, 'Properties:', properties)
    
    switch (eventType) {
      case 'server.connected':
        console.log('[OpenCode] Connected to server')
        break
        
      case 'message.created':
      case 'message.updated':
        // Message info update - create or update message with info
        if (properties && properties.info) {
          const info = properties.info
          const existing = messages.value.get(info.id) || { parts: [] }
          messages.value.set(info.id, {
            info,
            parts: existing.parts
          })
          console.log('[useOpencodeEvents] Message updated:', info.role, info.id)
        } else {
          console.warn('[useOpencodeEvents] Invalid message.updated event:', event)
        }
        break
        
      case 'message.part.updated':
        // Part update - add or update a part in the message
        if (properties && properties.part) {
          const part = properties.part
          const messageId = part.messageID
          const existing = messages.value.get(messageId) || { info: null, parts: [] }
          
          // Find and update existing part, or add new one
          const partIndex = existing.parts.findIndex(p => p.id === part.id)
          if (partIndex >= 0) {
            existing.parts[partIndex] = part
          } else {
            existing.parts.push(part)
          }
          
          messages.value.set(messageId, existing)
          console.log('[useOpencodeEvents] Part updated:', part.type, 'in message', messageId)
        } else {
          console.warn('[useOpencodeEvents] Invalid message.part.updated event:', event)
        }
        break
        
      case 'tool.started':
      case 'tool.call.started':
        if (properties && properties.callID) {
          tools.value.set(properties.callID, {
            ...properties,
            status: 'running',
            startTime: Date.now()
          })
        }
        break
        
      case 'tool.finished':
      case 'tool.call.finished':
        if (properties && properties.callID) {
          const existing = tools.value.get(properties.callID)
          if (existing) {
            tools.value.set(properties.callID, {
              ...existing,
              ...properties,
              status: properties.error ? 'error' : 'success',
              endTime: Date.now()
            })
          }
        }
        break
        
      case 'permission.request':
        console.log('[OpenCode] Permission requested:', properties)
        break
        
      case 'session.error':
        // Session error event - important for debugging
        console.error('[OpenCode] Session error:', properties)
        if (properties?.error) {
          console.error('[OpenCode] Error details:', {
            name: properties.error.name,
            message: properties.error.message || 'Unknown error'
          })
        }
        break
        
      case 'session.updated':
        // Session state events
        console.log('[OpenCode] Session event: session.updated')
        break
        
      case 'session.status':
        // Session status: busy, idle, retry, etc.
        if (properties?.status) {
          const statusType = properties.status.type
          console.log('[OpenCode] Session status:', statusType)
          // Update loading state based on session status
          // This will be handled by the chat store if needed
        }
        break
        
      case 'session.idle':
        // Session is idle - processing complete
        console.log('[OpenCode] Session idle - processing complete')
        // Emit a custom event that the chat store can listen to
        // This ensures loading state is cleared when session completes
        // The chat store will handle this via the watch on latestSessionStatus
        break
        
      default:
        // Log unknown event types for debugging
        console.log('[OpenCode] Unknown event type:', eventType, event)
    }
  }
  
  /**
   * Disconnect from event stream
   */
  function disconnect() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    connected.value = false
    eventStream = null
    console.log('[useOpencodeEvents] Disconnected')
  }
  
  /**
   * Clear all stored events and state
   */
  function clear() {
    events.value = []
    messages.value.clear()
    tools.value.clear()
  }
  
  // Cleanup on component unmount
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    events,
    messages,
    tools,
    connected,
    subscribe,
    disconnect,
    clear,
    addMessageFromPrompt
  }
}
