import { ref, computed, watch, reactive } from 'vue'
import { useOpencode } from './useOpencode'
import { useOpencodeEvents } from './useOpencodeEvents'

/**
 * OpenCode Sync Composable
 * Mirrors OpenCode's sync.data structure:
 * - messagesBySession[sessionID] = Message[]
 * - partsByMessage[messageID] = Part[]
 * - sessions = Session[]
 * 
 * This matches OpenCode's pattern in desktop/src/context/sync.tsx
 * 
 * IMPORTANT: This is a singleton - all stores share the same sync instance
 * 
 * Uses reactive() for nested objects to ensure deep reactivity (like SolidJS stores)
 */

// Shared sync instance - exported so stores can share it
let sharedSync = null

export function setSharedSync(sync) {
  sharedSync = sync
}

export function useOpencodeSync() {
  // Return shared instance if available, otherwise create new one
  if (sharedSync) {
    return sharedSync
  }
  
  const opencode = useOpencode()
  const events = useOpencodeEvents()
  
  // Store structure matching OpenCode's sync.data
  // Use reactive() for nested objects to ensure deep reactivity (like SolidJS stores)
  const sessions = ref([])
  const messagesBySession = reactive({}) // { [sessionID]: Message[] } - reactive for deep reactivity
  const partsByMessage = reactive({})    // { [messageID]: Part[] } - reactive for deep reactivity
  const todosBySession = reactive({})    // { [sessionID]: Todo[] } - reactive for deep reactivity
  const diffsBySession = reactive({})    // { [sessionID]: FileDiff[] } - reactive for deep reactivity
  const sessionStatus = reactive({})      // { [sessionID]: SessionStatus } - reactive for deep reactivity
  
  // Create syncInstance early so we can reference it in watch callbacks
  const syncInstance = {
    _lastEventIndex: -1,
    _syncInterval: null
  }
  
  /**
   * Sync a session (load messages, todo, diff)
   * Equivalent to OpenCode's sync.session.sync(sessionID)
   */
  async function syncSession(sessionID) {
    if (!sessionID) return
    
    try {
      console.log('[OpencodeSync] Syncing session:', sessionID)
      
      // Fetch all data for the session in parallel (like OpenCode does)
      const [sessionResult, messagesResult, todoResult, diffResult] = await Promise.all([
        opencode.client.value.session.get({ path: { id: sessionID }, throwOnError: true }).catch(() => null),
        opencode.client.value.session.messages({ path: { id: sessionID }, query: { limit: 100 } }),
        opencode.client.value.session.todo({ path: { id: sessionID } }),
        opencode.client.value.session.diff({ path: { id: sessionID } })
      ])
      
      // Update session in list
      if (sessionResult?.data) {
        const index = sessions.value.findIndex(s => s.id === sessionID)
        if (index !== -1) {
          sessions.value[index] = sessionResult.data
        } else {
          sessions.value.push(sessionResult.data)
        }
      }
      
      // Store messages per session (like OpenCode: draft.message[sessionID] = messages.data.map(x => x.info))
      // MERGE instead of replace to avoid clearing messages added via events
      if (messagesResult?.data) {
        const apiMessages = messagesResult.data.map(x => x.info)
        
        // Initialize if needed
        if (!messagesBySession[sessionID]) {
          messagesBySession[sessionID] = []
        }
        
        // Merge API messages with existing messages (events might have added some already)
        const existingMessages = messagesBySession[sessionID]
        const existingIds = new Set(existingMessages.map(m => m.id))
        
        // Add new messages from API that we don't already have
        apiMessages.forEach(msgInfo => {
          if (!existingIds.has(msgInfo.id)) {
            existingMessages.push(msgInfo)
          } else {
            // Update existing message with API data (might have more complete info)
            const index = existingMessages.findIndex(m => m.id === msgInfo.id)
            if (index !== -1) {
              existingMessages[index] = msgInfo
            }
          }
        })
        
        // Sort by ID (like OpenCode)
        existingMessages.sort((a, b) => a.id.localeCompare(b.id))
        
        // Store parts separately (like OpenCode: draft.part[message.info.id] = message.parts)
        // Direct assignment to reactive object - Vue tracks this automatically
        messagesResult.data.forEach(message => {
          if (message.info && message.parts) {
            partsByMessage[message.info.id] = message.parts
              .sort((a, b) => a.id.localeCompare(b.id))
          }
        })
        
        console.log('[OpencodeSync] Synced', apiMessages.length, 'messages from API for session', sessionID, 'total now:', existingMessages.length)
      }
      
      // Store todo, diff - direct assignment to reactive objects
      if (todoResult?.data) {
        todosBySession[sessionID] = todoResult.data
      }
      if (diffResult?.data) {
        diffsBySession[sessionID] = diffResult.data
      }
      
    } catch (err) {
      console.error('[OpencodeSync] Error syncing session:', err)
    }
  }
  
  /**
   * Load all sessions
   */
  async function loadSessions() {
    try {
      const result = await opencode.client.value.session.list()
      sessions.value = result.data || []
      console.log('[OpencodeSync] Loaded', sessions.value.length, 'sessions')
      return sessions.value
    } catch (err) {
      console.error('[OpencodeSync] Error loading sessions:', err)
      return []
    }
  }
  
  /**
   * Get messages for a session
   * Equivalent to OpenCode's: sync.data.message[params.id]
   */
  function getMessages(sessionID) {
    return messagesBySession[sessionID] || []
  }
  
  /**
   * Get parts for a message
   * Equivalent to OpenCode's: sync.data.part[messageID]
   */
  function getParts(messageID) {
    return partsByMessage[messageID] || []
  }
  
  // Helper function to update sync structure from events map
  function updateFromEventsMap() {
    const newMessageMap = events.messages.value
    if (!newMessageMap || newMessageMap.size === 0) {
      console.log('[OpencodeSync] Events map is empty, skipping update')
      return
    }
    
    console.log('[OpencodeSync] Updating from events map, size:', newMessageMap.size)
    let updatedCount = 0
    let skippedCount = 0
    
    newMessageMap.forEach((msg, messageId) => {
      if (!msg || !msg.info) {
        console.warn('[OpencodeSync] Invalid message in events map:', messageId, msg)
        skippedCount++
        return
      }
      
      const sessionID = msg.info?.sessionID
      if (!sessionID) {
        console.warn('[OpencodeSync] Message missing sessionID:', messageId, msg.info)
        skippedCount++
        return
      }
      
      // Update messagesBySession (like OpenCode's message.updated event)
      // Direct assignment to reactive object - Vue tracks this automatically
      if (!messagesBySession[sessionID]) {
        messagesBySession[sessionID] = []
        console.log('[OpencodeSync] Created new session array for', sessionID)
      }
      
      const messages = messagesBySession[sessionID]
      const index = messages.findIndex(m => m.id === messageId)
      
      if (index !== -1) {
        // Update existing message - direct assignment to reactive array
        messages[index] = msg.info
        console.log('[OpencodeSync] Updated existing message', messageId, 'role:', msg.info.role, 'in session', sessionID)
      } else {
        // Insert new message (sorted) - push to reactive array
        messages.push(msg.info)
        messages.sort((a, b) => a.id.localeCompare(b.id))
        updatedCount++
        console.log('[OpencodeSync] Added new message', messageId, 'role:', msg.info.role, 'to session', sessionID, 'total:', messages.length)
      }
      
      // Update partsByMessage - direct assignment to reactive object
      if (msg.parts && msg.parts.length > 0) {
        partsByMessage[messageId] = [...msg.parts].sort((a, b) => a.id.localeCompare(b.id))
        console.log('[OpencodeSync] Updated parts for message', messageId, 'parts:', msg.parts.length)
      }
    })
    
    console.log('[OpencodeSync] Update complete - added:', updatedCount, 'skipped:', skippedCount)
    console.log('[OpencodeSync] Current messagesBySession keys:', Object.keys(messagesBySession))
    Object.keys(messagesBySession).forEach(sid => {
      console.log('[OpencodeSync] Session', sid, 'has', messagesBySession[sid].length, 'messages')
    })
  }
  
  // Handle events directly like OpenCode's global-sync (listening to sdk.event.listen)
  // Watch the events array and handle message.updated and message.part.updated directly
  watch(() => events.events.value, (eventList) => {
    if (!eventList || eventList.length === 0) {
      console.log('[OpencodeSync] Events list is empty')
      return
    }
    
    // Process new events (only the ones we haven't seen)
    const lastProcessedIndex = syncInstance._lastEventIndex || -1
    const newEvents = eventList.slice(lastProcessedIndex + 1)
    
    if (newEvents.length === 0) {
      console.log('[OpencodeSync] No new events to process (lastIndex:', lastProcessedIndex, 'total:', eventList.length, ')')
      return
    }
    
    console.log('[OpencodeSync] Processing', newEvents.length, 'new events (lastIndex:', lastProcessedIndex, 'total:', eventList.length, ')')
    
    newEvents.forEach(event => {
      const payload = event.payload || event
      const eventType = payload.type
      
      // Handle message.updated events directly (like OpenCode)
      if (eventType === 'message.updated' && payload.properties?.info) {
        const messageInfo = payload.properties.info
        const sessionID = messageInfo.sessionID
        
        if (!sessionID) {
          console.warn('[OpencodeSync] message.updated missing sessionID:', messageInfo)
          return
        }
        
        // Initialize session array if needed (reactive object, direct assignment)
        if (!messagesBySession[sessionID]) {
          messagesBySession[sessionID] = []
        }
        
        const messages = messagesBySession[sessionID]
        const index = messages.findIndex(m => m.id === messageInfo.id)
        
        if (index !== -1) {
          // Update existing message - direct assignment to reactive array (Vue tracks this)
          messages[index] = messageInfo
          console.log('[OpencodeSync] Updated message', messageInfo.id, 'role:', messageInfo.role, 'in session', sessionID)
        } else {
          // Insert new message (sorted by ID, like OpenCode)
          // Push to reactive array - Vue tracks this automatically
          messages.push(messageInfo)
          messages.sort((a, b) => a.id.localeCompare(b.id))
          console.log('[OpencodeSync] Added message', messageInfo.id, 'role:', messageInfo.role, 'to session', sessionID, 'total:', messages.length)
        }
      }
      
      // Handle message.part.updated events directly (like OpenCode)
      if (eventType === 'message.part.updated' && payload.properties?.part) {
        const part = payload.properties.part
        const messageID = part.messageID
        
        if (!messageID) {
          console.warn('[OpencodeSync] message.part.updated missing messageID:', part)
          return
        }
        
        // Initialize parts array if needed (reactive object, direct assignment)
        if (!partsByMessage[messageID]) {
          partsByMessage[messageID] = []
        }
        
        const parts = partsByMessage[messageID]
        const index = parts.findIndex(p => p.id === part.id)
        
        if (index !== -1) {
          // Update existing part - direct assignment to reactive array (Vue tracks this)
          parts[index] = part
        } else {
          // Insert new part (sorted by ID, like OpenCode)
          // Push to reactive array - Vue tracks this automatically
          parts.push(part)
          parts.sort((a, b) => a.id.localeCompare(b.id))
        }
      }
      
      // Handle session.updated events
      if (eventType === 'session.updated' && payload.properties?.info) {
        const session = payload.properties.info
        const index = sessions.value.findIndex(s => s.id === session.id)
        if (index !== -1) {
          sessions.value[index] = session
        } else {
          sessions.value.push(session)
        }
      }
    })
    
    // Update last processed index
    syncInstance._lastEventIndex = eventList.length - 1
    
    // Also update from events map as a fallback (for messages added via addMessageFromPrompt)
    // This ensures messages from events.messages.value are synced to messagesBySession
    if (events.messages.value.size > 0) {
      console.log('[OpencodeSync] Calling updateFromEventsMap after processing events (map size:', events.messages.value.size, ')')
      updateFromEventsMap()
    }
  }, { deep: true, immediate: true })
  
  // Watch the messages map to catch direct additions (like addMessageFromPrompt)
  // We need to watch the Map itself, not just the size, because Vue's reactivity with Maps is tricky
  // Use a computed to track changes more reliably
  let lastMapSize = 0
  watch(() => {
    // Access the Map to create a dependency
    const map = events.messages.value
    const currentSize = map.size
    // Also access keys to ensure reactivity
    const keys = Array.from(map.keys())
    return { size: currentSize, keys }
  }, (newVal, oldVal) => {
    const newSize = newVal.size
    const oldSize = oldVal?.size || lastMapSize
    
    if (newSize > 0 && newSize !== oldSize) {
      console.log('[OpencodeSync] Messages map changed, size:', oldSize, '->', newSize, '- calling updateFromEventsMap')
      lastMapSize = newSize
      updateFromEventsMap()
    }
  }, { deep: true, immediate: true })
  
  // Also watch events array more aggressively - call updateFromEventsMap after processing events
  watch(() => events.events.value.length, (newLength, oldLength) => {
    if (newLength > oldLength && newLength > 0) {
      console.log('[OpencodeSync] Events array length changed from', oldLength, 'to', newLength, '- calling updateFromEventsMap')
      // Small delay to ensure events are processed first
      setTimeout(() => {
        updateFromEventsMap()
      }, 50)
    }
  }, { immediate: false })
  
  // Initial update from events map
  console.log('[OpencodeSync] Initializing, current messages map size:', events.messages.value.size)
  updateFromEventsMap()
  
  // Periodic sync to ensure messages are always synced (fallback in case watches don't trigger)
  // This ensures messages from events.messages.value are copied to messagesBySession
  const syncInterval = setInterval(() => {
    if (events.messages.value.size > 0) {
      const currentMessagesBySession = Object.keys(messagesBySession).reduce((acc, sid) => {
        acc[sid] = messagesBySession[sid].length
        return acc
      }, {})
      
      // Check if we need to sync
      let needsSync = false
      events.messages.value.forEach((msg, messageId) => {
        if (msg?.info?.sessionID) {
          const sessionID = msg.info.sessionID
          const existingMessages = messagesBySession[sessionID] || []
          if (!existingMessages.find(m => m.id === messageId)) {
            needsSync = true
          }
        }
      })
      
      if (needsSync) {
        console.log('[OpencodeSync] Periodic sync detected missing messages, calling updateFromEventsMap')
        updateFromEventsMap()
      }
    }
  }, 500) // Check every 500ms
  
  // Store interval ID for cleanup (if needed)
  syncInstance._syncInterval = syncInterval
  
  
  /**
   * Clear messages for a session
   */
  function clearSessionMessages(sessionID) {
    if (sessionID) {
      // Get message IDs before deleting
      const messageIds = messagesBySession[sessionID]?.map(m => m.id) || []
      
      // Delete session messages (reactive object, Vue tracks this)
      delete messagesBySession[sessionID]
      
      // Clear parts associated with messages from this session
      messageIds.forEach(messageId => {
        delete partsByMessage[messageId]
      })
      console.log('[OpencodeSync] Cleared messages for session', sessionID)
    } else {
      // Clear everything - need to clear all keys in reactive object
      Object.keys(messagesBySession).forEach(key => delete messagesBySession[key])
      Object.keys(partsByMessage).forEach(key => delete partsByMessage[key])
      console.log('[OpencodeSync] Cleared all messages')
    }
  }
  
  // Add computed properties and methods to syncInstance
  // For reactive objects, expose them directly (not as computed) so mutations work
  syncInstance.sessions = computed(() => sessions.value)
  syncInstance.messagesBySession = messagesBySession // Direct access to reactive object
  syncInstance.partsByMessage = partsByMessage // Direct access to reactive object
  syncInstance.todosBySession = todosBySession // Direct access to reactive object
  syncInstance.diffsBySession = diffsBySession // Direct access to reactive object
  syncInstance.sessionStatus = sessionStatus // Direct access to reactive object
  
  syncInstance.syncSession = syncSession
  syncInstance.loadSessions = loadSessions
  syncInstance.getMessages = getMessages
  syncInstance.getParts = getParts
  syncInstance.clearSessionMessages = clearSessionMessages
  
  // Store as shared instance
  sharedSync = syncInstance
  return syncInstance
}

