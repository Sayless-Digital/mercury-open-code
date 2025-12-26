/**
 * OpenCode Composable
 * Provides reactive access to OpenCode client functionality
 */

import { ref, computed, onUnmounted } from 'vue'
import { createOpencodeClient } from '@opencode-ai/sdk/client'
import { useProjectStore } from '@/stores/project'
import { useOpencodeEvents } from './useOpencodeEvents'

const OPENCODE_URL = 'http://127.0.0.1:4096'

// Shared events instance - exported so chat store can set it
let sharedEvents = null

export function setSharedEvents(events) {
  sharedEvents = events
}

// Singleton state shared across all useOpencode() calls
// This ensures SessionStore and ChatStore use the same sessionId
let sharedState = null

function getSharedState() {
  if (!sharedState) {
    console.log('[useOpencode] Creating shared state singleton')
    sharedState = {
      sessionId: ref(null),
      loading: ref(false),
      error: ref(null),
      abortController: ref(new AbortController()),
      currentDirectory: ref(null),
      clientInstance: ref(null)
    }
  }
  return sharedState
}

export function useOpencode() {
  const projectStore = useProjectStore()
  // Use shared events instance if available (set by chat store)
  // Otherwise create a new one (fallback)
  const events = sharedEvents || useOpencodeEvents()
  
  // Get shared state - this ensures all stores use the same sessionId
  const state = getSharedState()
  const { sessionId, loading, error, abortController, currentDirectory, clientInstance } = state
  
  // Create client once and only recreate when directory changes
  const getClient = () => {
    const directory = projectStore.currentProject?.path || process.cwd()
    
    // Only recreate client if directory changed
    if (!clientInstance.value || currentDirectory.value !== directory) {
      // Abort old controller if it exists
      if (abortController.value && !abortController.value.signal.aborted) {
        abortController.value.abort()
      }
      
      // Create new controller and client
      abortController.value = new AbortController()
      currentDirectory.value = directory
      clientInstance.value = createOpencodeClient({
        baseUrl: OPENCODE_URL,
        throwOnError: false,
        directory: directory,
        signal: abortController.value.signal
      })
    }
    
    return clientInstance.value
  }
  
  const client = computed(() => getClient())
  
  // Cleanup on unmount
  onUnmounted(() => {
    if (abortController.value && !abortController.value.signal.aborted) {
      abortController.value.abort()
    }
  })

  /**
   * Create a new chat session
   */
  async function createSession(title = 'Chat Session') {
    try {
      loading.value = true
      error.value = null
      
      const result = await client.value.session.create({
        body: { title }
      })
      
      console.log('[useOpencode] Create session result:', result)
      console.log('[useOpencode] Result type:', typeof result)
      console.log('[useOpencode] Result keys:', result ? Object.keys(result) : 'null/undefined')
      console.log('[useOpencode] Result.data:', result?.data)
      console.log('[useOpencode] Result.error:', result?.error)
      
      // With responseStyle: "fields" (default), the SDK returns { data: Session, error, response }
      // Session has { id, title, directory, time, ... }
      if (result?.error) {
        throw new Error(result.error.message || 'Failed to create session')
      }
      
      if (result?.data && result.data.id) {
        sessionId.value = result.data.id
        console.log('[useOpencode] Session created successfully:', result.data.id)
        return result.data
      }
      
      throw new Error('Failed to create session: invalid response structure')
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Create session error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }


  /**
   * Send a message to the current session
   * Following OpenCode official pattern: don't await prompt(), rely on events
   */
  async function sendMessage(text, options = {}) {
    if (!sessionId.value) {
      await createSession()
    } else {
      // Validate that the session actually exists in the backend
      try {
        const sessionsResult = await client.value.session.list()
        const sessionExists = sessionsResult?.data?.some(s => s.id === sessionId.value)
        
        if (!sessionExists) {
          console.error('[useOpencode] Session mismatch - UI session not in backend')
          
          // Use first available session or create new one
          if (sessionsResult?.data && sessionsResult.data.length > 0) {
            sessionId.value = sessionsResult.data[0].id
            
            try {
              const { useSessionStore } = await import('@/stores/session')
              const sessionStore = useSessionStore()
              await sessionStore.switchSession(sessionsResult.data[0].id)
            } catch (err) {
              console.error('[useOpencode] Failed to sync SessionStore:', err)
            }
          } else {
            await createSession()
          }
        }
      } catch (err) {
        console.warn('[useOpencode] Session validation failed:', err)
      }
    }
    
    // Always use Claude 4.5 by passing model directly in prompt
    // OpenCode expects model as an object with providerID and modelID
    const correctModel = {
      providerID: 'amazon-bedrock',
      modelID: 'anthropic.claude-sonnet-4-5-20250929-v1:0'
    }

    try {
      loading.value = true
      error.value = null


      // ALWAYS pass the model in the prompt body to override config
      // This ensures we use Claude 4.5 regardless of config file state
      const promptBody = {
        parts: [{ type: 'text', text }],
        model: correctModel  // Always use Claude 4.5 as object
      }
      
      // Debug: Verify model format before sending
      console.log('[useOpencode] Sending prompt with model:', JSON.stringify(correctModel))
      console.log('[useOpencode] Full promptBody before sending:', JSON.stringify(promptBody, null, 2))
      
      // Only include optional properties if they have values
      if (options.agent) promptBody.agent = options.agent
      if (options.tools) promptBody.tools = options.tools
      if (options.noReply) promptBody.noReply = options.noReply
      
      console.log('[useOpencode] Final promptBody with options:', JSON.stringify(promptBody, null, 2))
      
      const promptPromise = client.value.session.prompt({
        path: { id: sessionId.value },
        body: promptBody
      })
      
      // Handle the prompt result
      promptPromise.then((result) => {
        if (result?.error) {
          console.error('[useOpencode] Prompt error - Message:', result.error.message)
          console.error('[useOpencode] Prompt error - Code:', result.error.code)
          console.error('[useOpencode] Prompt error - Status:', result.error.status)
          console.error('[useOpencode] Prompt error - Full error:', JSON.stringify(result.error, null, 2))
          error.value = result.error.message || 'Failed to send message'
          loading.value = false
        } else if (result?.data && Object.keys(result.data).length > 0) {
          // The prompt() returns { info: AssistantMessage, parts: Part[] } when successful
          // Add it to events for immediate display
          if (result.data.info && result.data.info.role === 'assistant') {
            events.addMessageFromPrompt(result.data)
          }
        } else {
          // Empty response - events will handle the messages
          // This is normal for OpenCode - prompt() doesn't always return full message data
        }
      }).catch((err) => {
        // Log errors - this could indicate the prompt failed to send
        console.error('[useOpencode] Prompt request error:', err)
        console.error('[useOpencode] Error details:', {
          message: err.message,
          stack: err.stack,
          name: err.name
        })
        error.value = err.message || 'Failed to send message'
        loading.value = false // Set loading to false on error
      })

      // Don't set loading to false here - let session status events manage it
      // Loading will be set to false when session.idle event arrives
      // Return success immediately - events will update the UI with the assistant message
      return { success: true }
    } catch (err) {
      error.value = err.message
      loading.value = false
      console.error('[useOpencode] Send message error:', err)
      throw err
    }
  }

  /**
   * Get messages from a session (can specify sessionId or use current)
   */
  async function getMessages(limit = 100, sessionIdParam = null) {
    const targetSessionId = sessionIdParam || sessionId.value
    if (!targetSessionId) {
      console.warn('[useOpencode] No sessionId provided for getMessages')
      return []
    }

    try {
      const result = await client.value.session.messages({
        path: { id: targetSessionId },
        query: { limit }
      })
      
      const messages = result.data || []
      // Removed logging - was causing spam when called frequently
      
      return messages
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Get messages error:', err)
      console.error('[useOpencode] Error details:', {
        sessionId: targetSessionId,
        error: err.message,
        stack: err.stack
      })
      return []
    }
  }

  /**
   * Abort the current session
   */
  async function abortSession() {
    if (!sessionId.value) return

    try {
      await client.value.session.abort({
        path: { id: sessionId.value }
      })
    } catch (err) {
      console.error('[useOpencode] Abort session error:', err)
    }
  }

  /**
   * Clear current session and create a new one
   */
  async function clearSession() {
    sessionId.value = null
    error.value = null
    await createSession()
  }

  /**
   * Get available providers and models from OpenCode
   * Use this for model selection in the GUI
   */
  async function getProviders() {
    try {
      const result = await client.value.config.providers()
      return result.data || { providers: [], default: {} }
    } catch (err) {
      console.error('[useOpencode] Get providers error:', err)
      return { providers: [], default: {} }
    }
  }

  /**
   * Get current config (including selected model)
   */
  async function getConfig() {
    try {
      const directory = projectStore.currentProject?.path || process.cwd()
      const result = await client.value.config.get({
        query: { directory }
      })
      return result.data || null
    } catch (err) {
      console.error('[useOpencode] Get config error:', err)
      return null
    }
  }

  /**
   * Set model in OpenCode config
   * Note: We now pass model directly in prompt() calls instead of relying on config files
   */
  async function setModel(modelString) {
    try {
      const directory = projectStore.currentProject?.path || process.cwd()
      const result = await client.value.config.update({
        query: { directory },
        body: { model: modelString }
      })
      console.log('[useOpencode] Model config updated to:', modelString)
      return result.data || { model: modelString }
    } catch (err) {
      console.error('[useOpencode] Set model error:', err)
      throw err
    }
  }
  
  /**
   * Initialize: Set default model to Claude Sonnet 4.5
   * Note: Model is now passed directly in prompt() calls, but we still update config for consistency
   */
  async function ensureDefaultModel() {
    try {
      const correctModel = 'amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0'
      await setModel(correctModel)
      console.log('[useOpencode] Default model set to Claude 4.5')
    } catch (err) {
      console.warn('[useOpencode] Could not set default model (non-critical):', err)
    }
  }

  // Set default model on initialization
  ensureDefaultModel().catch(err => {
    console.warn('[useOpencode] Background model setup failed:', err)
  })

  /**
   * Clear loading state manually (useful when session.idle event fires)
   */
  function clearLoading() {
    loading.value = false
    console.log('[useOpencode] Loading state cleared manually')
  }

  /**
   * List all sessions for the current project
   */
  async function listSessions() {
    try {
      const result = await client.value.session.list()
      return result.data || []
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] List sessions error:', err)
      return []
    }
  }

  /**
   * Get a specific session by ID
   */
  async function getSession(sessionIdParam) {
    try {
      const result = await client.value.session.get({
        path: { id: sessionIdParam }
      })
      return result.data || null
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Get session error:', err)
      return null
    }
  }

  /**
   * Switch to a different session
   */
  async function switchSession(sessionIdParam) {
    try {
      // Only log if actually switching to a different session
      if (sessionId.value !== sessionIdParam) {
        console.log('[useOpencode] Switching sessionId from', sessionId.value, 'to', sessionIdParam)
      }
      sessionId.value = sessionIdParam
      // Don't load messages here - let the ChatPanel watch handle it
      // This prevents conflicts and ensures messages are loaded for the correct session
      return true
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Switch session error:', err)
      return false
    }
  }

  /**
   * Delete a session
   */
  async function deleteSession(sessionIdParam) {
    try {
      await client.value.session.delete({
        path: { id: sessionIdParam }
      })
      // If we deleted the current session, clear it
      if (sessionId.value === sessionIdParam) {
        sessionId.value = null
      }
      return true
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Delete session error:', err)
      return false
    }
  }

  /**
   * Update session properties (e.g., title)
   */
  async function updateSession(sessionIdParam, updates) {
    try {
      const result = await client.value.session.update({
        path: { id: sessionIdParam },
        body: updates
      })
      // Removed logging - session updates are frequent and cause spam
      return result.data || null
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Update session error:', err)
      return null
    }
  }

  /**
   * Rename a session using AI to generate a title from conversation
   * This sends a message to the AI asking it to summarize the conversation
   */
  async function renameSessionWithAI(sessionIdParam) {
    try {
      // Track which sessions we've already renamed to avoid repeated calls
      if (!renameSessionWithAI.renamedSessions) {
        renameSessionWithAI.renamedSessions = new Set()
      }
      
      // Skip if we've already renamed this session
      if (renameSessionWithAI.renamedSessions.has(sessionIdParam)) {
        return null
      }
      
      // Get messages from the session
      const messages = await getMessages(100, sessionIdParam)
      if (!messages || messages.length === 0) {
        return await updateSession(sessionIdParam, { title: 'New Chat' })
      }
      
      // Get first user message to base title on
      const firstUserMessage = messages.find(msg => msg.info?.role === 'user')
      if (!firstUserMessage) {
        return await updateSession(sessionIdParam, { title: 'New Chat' })
      }
      
      // Extract text from the first user message
      const firstMessageText = firstUserMessage.parts
        ?.filter(part => part.type === 'text')
        ?.map(part => part.text)
        ?.join(' ') || ''
      
      if (!firstMessageText) {
        return await updateSession(sessionIdParam, { title: 'New Chat' })
      }
      
      // Generate a short title (max 50 chars) from first message
      let title = firstMessageText.trim()
      
      // Truncate if too long
      if (title.length > 50) {
        title = title.substring(0, 47) + '...'
      }
      
      // Clean up the title (remove newlines, extra spaces)
      title = title.replace(/\s+/g, ' ').trim()
      
      // If title is empty after cleanup, use default
      if (!title) {
        title = 'New Chat'
      }
      
      // Mark as renamed before updating (to prevent loops)
      renameSessionWithAI.renamedSessions.add(sessionIdParam)
      
      // Update the session with the new title
      return await updateSession(sessionIdParam, { title })
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Rename session with AI error:', err)
      return null
    }
  }

  return {
    client,
    sessionId,
    loading,
    error,
    createSession,
    sendMessage,
    getMessages,
    abortSession,
    clearSession,
    getProviders,
    getConfig,
    setModel,
    ensureDefaultModel,
    clearLoading,
    listSessions,
    getSession,
    switchSession,
    deleteSession,
    updateSession,
    renameSessionWithAI
  }
}
