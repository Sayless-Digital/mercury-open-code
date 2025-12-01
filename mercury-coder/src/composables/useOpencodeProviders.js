/**
 * OpenCode Providers Composable
 * Manages AI providers, models, and authentication
 */

import { ref, computed } from 'vue'
import { createOpencodeClient } from '@opencode-ai/sdk/client'

const OPENCODE_URL = 'http://127.0.0.1:4096'

export function useOpencodeProviders() {
  const client = createOpencodeClient({ baseUrl: OPENCODE_URL })
  
  const providers = ref([])
  const connectedProviders = ref([])
  const currentConfig = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  /**
   * Load all available providers
   */
  async function loadProviders() {
    try {
      loading.value = true
      error.value = null
      
      const result = await client.config.providers()
      
      if (result.data) {
        providers.value = result.data.providers || []
        
        // Get current config to check which providers are connected
        await getConfig()
        
        // Extract connected providers (those with options.key set in config)
        if (currentConfig.value?.provider) {
          connectedProviders.value = Object.keys(currentConfig.value.provider)
            .filter(id => currentConfig.value.provider[id]?.options?.key)
        } else {
          connectedProviders.value = []
        }
        
        console.log('[useOpencodeProviders] Connected providers:', connectedProviders.value)
        return result.data
      }
    } catch (err) {
      error.value = err.message
      console.error('[useOpencodeProviders] Load providers error:', err)
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Get models for a specific provider
   */
  async function getModels(providerId) {
    try {
      // Models are already included in the provider object from loadProviders
      const provider = providers.value.find(p => p.id === providerId)
      console.log(`[useOpencodeProviders] Getting models for ${providerId}`, {
        providerFound: !!provider,
        hasModels: !!provider?.models,
        modelCount: provider?.models ? Object.keys(provider.models).length : 0
      })
      
      if (!provider || !provider.models) {
        return []
      }
      
      // Convert models object to array
      const modelArray = Object.values(provider.models)
      console.log(`[useOpencodeProviders] Returning ${modelArray.length} models for ${providerId}`)
      return modelArray
    } catch (err) {
      console.error(`[useOpencodeProviders] Get models error for ${providerId}:`, err)
      return []
    }
  }
  
  /**
   * Set API key for a provider
   */
  async function setAuth(providerId, apiKey) {
    try {
      loading.value = true
      error.value = null
      
      const result = await client.auth.set({
        path: { id: providerId },
        body: { key: apiKey }
      })
      
      // Refresh providers to update connected status
      await loadProviders()
      
      return result.data
    } catch (err) {
      error.value = err.message
      console.error(`[useOpencodeProviders] Set auth error for ${providerId}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Get current OpenCode configuration
   */
  async function getConfig() {
    try {
      const result = await client.config.get()
      
      if (result.data) {
        currentConfig.value = result.data
        return result.data
      }
    } catch (err) {
      console.error('[useOpencodeProviders] Get config error:', err)
    }
  }
  
  /**
   * Update OpenCode configuration
   */
  async function updateConfig(updates) {
    try {
      loading.value = true
      error.value = null
      
      const result = await client.config.update({
        body: updates
      })
      
      if (result.data) {
        currentConfig.value = result.data
      }
      
      return result.data
    } catch (err) {
      error.value = err.message
      console.error('[useOpencodeProviders] Update config error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Set the default model
   */
  async function setModel(providerId, modelId) {
    const modelString = `${providerId}/${modelId}`
    return updateConfig({ model: modelString })
  }
  
  // Computed helpers
  const isProviderConnected = computed(() => {
    return (providerId) => connectedProviders.value.includes(providerId)
  })
  
  const currentModel = computed(() => {
    if (!currentConfig.value?.model) return null
    
    const [providerId, modelId] = currentConfig.value.model.split('/')
    return { providerId, modelId, full: currentConfig.value.model }
  })
  
  return {
    providers,
    connectedProviders,
    currentConfig,
    currentModel,
    loading,
    error,
    loadProviders,
    getModels,
    setAuth,
    getConfig,
    updateConfig,
    setModel,
    isProviderConnected
  }
}
