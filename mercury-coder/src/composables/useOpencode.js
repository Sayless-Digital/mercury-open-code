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

export function useOpencode() {
  const projectStore = useProjectStore()
  // Use shared events instance if available (set by chat store)
  // Otherwise create a new one (fallback)
  const events = sharedEvents || useOpencodeEvents()
  const abortController = ref(new AbortController())
  const currentDirectory = ref(null)
  const clientInstance = ref(null)
  
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

  const sessionId = ref(null)
  const loading = ref(false)
  const error = ref(null)

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
    }

    // Ensure model is correctly configured before sending
    // This fixes the model format if it's wrong (e.g., missing provider prefix)
    try {
      const directory = projectStore.currentProject?.path || process.cwd()
      const correctModel = 'amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0'
      
      // Force update the model via API and file system
      console.log('[useOpencode] Ensuring model is correct before send...')
      
      // 1. Update via API
      await client.value.config.update({
        query: { directory },
        body: { model: correctModel }
      })
      
      // 2. Write to Mercury Coder global config instead of project directory
      try {
        if (window.electronAPI?.writeMercuryConfig) {
          const minimalConfig = {
            $schema: "https://opencode.ai/config.json",
            model: correctModel
          }
          const result = await window.electronAPI.writeMercuryConfig(minimalConfig)
          if (result.success) {
            console.log('[useOpencode] Wrote model to Mercury global config:', result.path)
          } else {
            console.warn('[useOpencode] Could not write to Mercury config:', result.error)
          }
        }
      } catch (fsErr) {
        console.warn('[useOpencode] Could not write to Mercury config:', fsErr)
      }
      
      // 3. Wait for config to be reloaded
      await new Promise(resolve => setTimeout(resolve, 300))
      
      // 4. Verify
      const config = await getConfig()
      console.log('[useOpencode] Model after fix:', config?.model)
      
      if (config?.model !== correctModel) {
        console.warn('[useOpencode] Model still incorrect after fix attempt:', config?.model)
      }
    } catch (err) {
      console.error('[useOpencode] Error ensuring model before sending:', err)
      // Don't throw - try to continue anyway, but log the error
    }

    try {
      loading.value = true
      error.value = null

      console.log('[useOpencode] Sending message to session:', sessionId.value)
      console.log('[useOpencode] Message text:', text)
      console.log('[useOpencode] Options:', options)

      // Following official OpenCode pattern: call prompt() without awaiting
      // Events will handle the response in real-time
      // OpenCode will automatically use the model from its config - we don't need to pass it
      // This matches: sdk.client.session.prompt({...}) in prompt-input.tsx:331
      // Only pass model if explicitly provided in options (for override)
      const promptBody = {
        parts: [{ type: 'text', text }],
        agent: options.agent || undefined,
        tools: options.tools || undefined,
        noReply: options.noReply || false
      }
      
      if (options.model) {
        promptBody.model = options.model
      }
      
      const promptPromise = client.value.session.prompt({
        path: { id: sessionId.value },
        body: promptBody
      })
      
      // Log the promise result for debugging and use the data
      promptPromise.then((result) => {
        console.log('[useOpencode] Prompt promise resolved:', result)
        console.log('[useOpencode] Result keys:', result ? Object.keys(result) : [])
        console.log('[useOpencode] Result.data:', result?.data)
        console.log('[useOpencode] Result.error:', result?.error)
        
        if (result?.error) {
          console.error('[useOpencode] Prompt returned error:', result.error)
          error.value = result.error.message || 'Failed to send message'
          loading.value = false
        } else if (result?.data) {
          console.log('[useOpencode] Prompt returned data:', result.data)
          console.log('[useOpencode] Data keys:', Object.keys(result.data || {}))
          console.log('[useOpencode] Data.info:', result.data.info)
          console.log('[useOpencode] Data.parts:', result.data.parts)
          
          // The prompt() returns { info: AssistantMessage, parts: Part[] }
          // Add it to the events messages map so it's available immediately
          // Events will also update it in real-time, but this provides immediate feedback
          if (result.data.info && result.data.info.role === 'assistant') {
            events.addMessageFromPrompt(result.data)
            console.log('[useOpencode] Added assistant message from prompt() to events')
            // Don't clear loading here - wait for session.idle event to ensure all events are processed
          } else {
            // If no assistant message in response, clear loading after a delay
            // This handles edge cases where events might not arrive
            setTimeout(() => {
              if (loading.value) {
                console.log('[useOpencode] Clearing loading after timeout (no assistant message in response)')
                loading.value = false
              }
            }, 2000)
          }
        } else {
          // No data returned - this is normal for streaming
          // Loading will be cleared by session.idle event
          console.log('[useOpencode] Prompt returned no data (streaming mode)')
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
   * Get messages from the current session
   */
  async function getMessages(limit = 100) {
    if (!sessionId.value) return []

    try {
      const result = await client.value.session.messages({
        path: { id: sessionId.value },
        query: { limit }
      })
      
      return result.data || []
    } catch (err) {
      error.value = err.message
      console.error('[useOpencode] Get messages error:', err)
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
   * Model format: "providerID/modelID" (e.g., "amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0")
   * 
   * Note: OpenCode's config.update() writes to config.json, but config resolution only reads
   * opencode.json/opencode.jsonc files. So we use the API to update, which should handle this correctly.
   * If that doesn't work, we may need to write directly to opencode.json.
   */
  async function setModel(modelString) {
    try {
      const directory = projectStore.currentProject?.path || process.cwd()
      // Use OpenCode's config.update() API - it should handle writing to the correct location
      const result = await client.value.config.update({
        query: { directory },
        body: { model: modelString }
      })
      console.log('[useOpencode] Model set to:', modelString, 'Result:', result.data?.model)
      
      // Also ensure Mercury Coder global config has the correct model
      try {
        if (window.electronAPI?.writeMercuryConfig) {
          const minimalConfig = {
            $schema: "https://opencode.ai/config.json",
            model: modelString
          }
          const result = await window.electronAPI.writeMercuryConfig(minimalConfig)
          if (result.success) {
            console.log('[useOpencode] Wrote model to Mercury global config:', result.path)
          } else {
            console.warn('[useOpencode] Could not write to Mercury config (non-critical):', result.error)
          }
        }
      } catch (fsErr) {
        console.warn('[useOpencode] Could not write to Mercury config (non-critical):', fsErr)
      }
      
      return result.data || { model: modelString }
    } catch (err) {
      console.error('[useOpencode] Set model error:', err)
      throw err
    }
  }
  
  /**
   * Initialize: Set default model to Claude Sonnet 4.5
   * Always set it to ensure it's in the correct format (providerID/modelID)
   */
  async function ensureDefaultModel() {
    try {
      const config = await getConfig()
      const currentModel = config?.model
      
      // Check if model is in correct format (has provider prefix)
      const correctModel = 'amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0'
      
      if (!currentModel || !currentModel.includes('/') || currentModel !== correctModel) {
        // Set to Claude Sonnet 4.5 via Amazon Bedrock
        await setModel(correctModel)
        console.log('[useOpencode] Set default model to Claude Sonnet 4.5:', correctModel)
      } else {
        console.log('[useOpencode] Model already correctly configured:', currentModel)
      }
    } catch (err) {
      console.warn('[useOpencode] Could not ensure default model:', err)
    }
  }

  // Ensure default model is set on initialization (don't await - run in background)
  // This will fix the model format if it's incorrect
  ensureDefaultModel().catch(err => {
    console.warn('[useOpencode] Background model check failed:', err)
  })

  /**
   * Clear loading state manually (useful when session.idle event fires)
   */
  function clearLoading() {
    loading.value = false
    console.log('[useOpencode] Loading state cleared manually')
  }

  return {
    client,
    sessionId: computed(() => sessionId.value),
    loading: computed(() => loading.value),
    error: computed(() => error.value),
    createSession,
    sendMessage,
    getMessages,
    abortSession,
    clearSession,
    getProviders,
    getConfig,
    setModel,
    ensureDefaultModel,
    clearLoading
  }
}
