import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useOpencodeProviders } from '@/composables/useOpencodeProviders'

export const useModelsStore = defineStore('models', () => {
  const providersComposable = useOpencodeProviders()
  
  const providerModels = ref({}) // providerId → models[]
  
  // Expose providers composable state as computed
  const providers = computed(() => providersComposable.providers.value)
  const connectedProviders = computed(() => providersComposable.connectedProviders.value)
  const currentModel = computed(() => providersComposable.currentModel.value)
  const loading = computed(() => providersComposable.loading.value)
  const error = computed(() => providersComposable.error.value)
  
  /**
   * Load all providers from OpenCode
   */
  async function loadProviders() {
    await providersComposable.loadProviders()
    
    // Load models for ALL providers (they're already in the API response)
    for (const provider of providers.value) {
      await loadModelsForProvider(provider.id)
    }
    
    console.log('[ModelsStore] Loaded providers:', providers.value.length)
    console.log('[ModelsStore] Connected providers:', connectedProviders.value)
    console.log('[ModelsStore] Provider models:', Object.keys(providerModels.value))
  }
  
  /**
   * Load models for a specific provider
   */
  async function loadModelsForProvider(providerId) {
    try {
      const models = await providersComposable.getModels(providerId)
      providerModels.value[providerId] = models
      return models
    } catch (err) {
      console.error(`[ModelsStore] Failed to load models for ${providerId}:`, err)
      return []
    }
  }
  
  /**
   * Set the active model
   */
  async function setModel(providerId, modelId) {
    try {
      await providersComposable.setModel(providerId, modelId)
    } catch (err) {
      console.error('[ModelsStore] Failed to set model:', err)
      throw err
    }
  }
  
  /**
   * Set API key for a provider
   */
  async function setApiKey(providerId, apiKey) {
    try {
      await providersComposable.setAuth(providerId, apiKey)
      // Reload models after successful authentication
      await loadModelsForProvider(providerId)
    } catch (err) {
      console.error('[ModelsStore] Failed to set API key:', err)
      throw err
    }
  }
  
  /**
   * Grouped models by provider for UI display
   */
  const groupedModels = computed(() => {
    return providers.value.map(provider => ({
      provider: provider.id,
      providerName: provider.name,
      connected: connectedProviders.value.includes(provider.id),
      models: providerModels.value[provider.id] || []
    }))
  })
  
  /**
   * Model options for dropdown (legacy compatibility)
   */
  const modelGroupOptions = computed(() => {
    return groupedModels.value
      .filter(g => g.connected && g.models.length > 0)
      .map(group => ({
        provider: group.providerName,
        models: group.models.map(model => ({
          id: `${group.provider}/${model.id}`,
          displayName: model.name || model.id,
          name: model.name || model.id,
          status: model.status || 'active'
        }))
      }))
  })
  
  /**
   * Current model name (legacy compatibility)
   */
  const currentModelName = computed(() => {
    if (!currentModel.value) return ''
    
    const models = providerModels.value[currentModel.value.providerId] || []
    const model = models.find(m => m.id === currentModel.value.modelId)
    
    return model?.name || currentModel.value.modelId
  })
  
  /**
   * Preload models (legacy compatibility)
   */
  async function preloadModels() {
    return loadProviders()
  }
  
  /**
   * Check if provider is connected
   */
  function isProviderConnected(providerId) {
    return connectedProviders.value.includes(providerId)
  }
  
  return {
    // State
    providers,
    connectedProviders,
    currentModel,
    providerModels,
    groupedModels,
    modelGroupOptions,
    currentModelName,
    loading,
    error,
    
    // Actions
    loadProviders,
    loadModelsForProvider,
    setModel,
    setApiKey,
    preloadModels,
    isProviderConnected
  }
})
