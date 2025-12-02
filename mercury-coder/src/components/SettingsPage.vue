<template>
  <div class="settings-page">
    <div class="settings-panel">
      <!-- Header -->
      <div class="settings-header">
        <div class="header-left">
          <button class="back-button" @click="goBack" title="Back">
            <ArrowLeft :size="16" />
          </button>
          <SettingsIcon class="settings-icon" :size="14" />
          <span class="settings-title">Settings</span>
        </div>
      </div>
      
      <!-- Tabs -->
      <div class="settings-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="tab-button"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" :size="14" />
          {{ tab.label }}
        </button>
      </div>
      
      <!-- Content -->
      <div class="settings-content">
        <!-- Providers Tab -->
        <div v-if="activeTab === 'providers'" class="tab-content">
          <div class="settings-section">
            <h2>AI Provider Configuration</h2>
            <p class="section-description">
              Configure AI providers and set API keys for chat functionality
            </p>
            
            <!-- Provider Cards -->
            <div class="provider-cards">
              <div 
                v-for="provider in availableProviders" 
                :key="provider.id"
                class="provider-card"
                :class="{ 
                  connected: isProviderConnected(provider.id),
                  active: currentProviderId === provider.id
                }"
              >
                <div class="provider-header">
                  <div class="provider-left">
                    <div class="provider-icon">
                      <component :is="getProviderIcon(provider.id)" :size="24" />
                    </div>
                    <div class="provider-info">
                      <h3>{{ provider.name || provider.id }}</h3>
                    </div>
                  </div>
                  <span class="provider-status">
                    <span v-if="isProviderConnected(provider.id)" class="status-badge connected">
                      ✓ Connected
                    </span>
                    <span v-else class="status-badge disconnected">
                      ○ Not configured
                    </span>
                  </span>
                </div>
                
                <!-- API Key Input (if not connected) -->
                <div v-if="!isProviderConnected(provider.id)" class="provider-auth">
                  <label :for="`api-key-${provider.id}`">API Key</label>
                  <div class="api-key-input-group">
                    <input
                      :id="`api-key-${provider.id}`"
                      type="password"
                      :placeholder="`Enter ${provider.name || provider.id} API key`"
                      v-model="apiKeys[provider.id]"
                      class="api-key-input"
                      @keydown.enter="saveApiKey(provider.id)"
                    />
                    <button 
                      class="btn btn-primary"
                      @click="saveApiKey(provider.id)"
                      :disabled="!apiKeys[provider.id] || connecting"
                    >
                      {{ connecting ? 'Connecting...' : 'Connect' }}
                    </button>
                  </div>
                  <p class="help-text">
                    Get your API key from 
                    <a :href="getProviderUrl(provider.id)" target="_blank">
                      {{ provider.name || provider.id }} Dashboard
                    </a>
                  </p>
                </div>
                
                <!-- Model Selection (if connected) -->
                <div v-else class="provider-models">
                  <label>Model</label>
                  <CustomDropdown
                    v-model="selectedModels[provider.id]"
                    :options="getModelOptions(provider.id)"
                    placeholder="Select a model..."
                    option-label="name"
                    option-value="id"
                    searchable
                    @change="setModel(provider.id, selectedModels[provider.id])"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <!-- Current Configuration Display -->
          <div v-if="currentModel" class="settings-section">
            <h2>Active Configuration</h2>
            <div class="config-display">
              <div class="config-item">
                <span class="config-label">Provider:</span>
                <span class="config-value">{{ currentProviderId || 'None' }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">Model:</span>
                <span class="config-value">{{ currentModel?.modelId || 'None' }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">Agent:</span>
                <span class="config-value">{{ defaultAgent }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Audio Tab -->
        <div v-if="activeTab === 'audio'" class="tab-content">
          <div class="settings-section">
            <h2>Voice Recorder</h2>
            <p class="section-description">Configure voice recording behavior</p>
            
            <div class="setting-item">
              <div class="setting-content">
                <div class="setting-info">
                  <label class="setting-label">Enable Auto Record Mode</label>
                  <p class="setting-description">
                    When enabled, recording will automatically start when you click into the input area
                  </p>
                </div>
                <div class="switch-container">
                  <input
                    type="checkbox"
                    v-model="autoRecordMode"
                    class="switch-input"
                    id="auto-record-mode"
                  />
                  <label for="auto-record-mode" class="switch-slider"></label>
                </div>
              </div>
            </div>
          </div>

          <div class="settings-section">
            <h2>Whisper Transcription Models</h2>
            <p class="section-description">Select and manage Whisper models for voice transcriptions</p>
            
            <div v-if="loadingWhisperModels" class="loading">Loading models...</div>
            <div v-else-if="whisperModelsError" class="error-message">
              {{ whisperModelsError }}
            </div>
            <div v-else class="whisper-models-list">
              <div 
                v-for="model in whisperModels" 
                :key="model.id"
                class="whisper-model-item"
                :class="{ 
                  active: selectedWhisperModel === model.id,
                  downloaded: model.downloaded
                }"
              >
                <div class="model-info">
                  <div class="model-header">
                    <span class="model-name">{{ model.name }}</span>
                    <span v-if="model.downloaded" class="downloaded-badge">✓ Downloaded</span>
                    <span v-else class="not-downloaded-badge">○ Not downloaded</span>
                  </div>
                  <div class="model-details">
                    <span class="model-size">{{ model.size }}</span>
                    <span class="model-separator">•</span>
                    <span class="model-description">{{ model.description }}</span>
                  </div>
                </div>
                <div class="model-actions">
                  <button
                    v-if="!model.downloaded"
                    class="btn btn-sm btn-primary"
                    @click="downloadModel(model.id)"
                    :disabled="downloadingModel === model.id"
                  >
                    <Download v-if="downloadingModel !== model.id" :size="14" />
                    <Loader2 v-else class="spinner" :size="14" />
                    {{ downloadingModel === model.id ? 'Downloading...' : 'Download' }}
                  </button>
                  <button
                    v-else
                    class="btn btn-sm"
                    :class="{ 'btn-active': selectedWhisperModel === model.id }"
                    @click="selectModel(model.id)"
                  >
                    {{ selectedWhisperModel === model.id ? 'Selected' : 'Select' }}
                  </button>
                </div>
                <div v-if="downloadingModel === model.id && downloadProgress" class="download-progress">
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: downloadProgress + '%' }"></div>
                  </div>
                  <span class="progress-text">{{ downloadProgress }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Advanced Tab -->
        <div v-if="activeTab === 'advanced'" class="tab-content">
          <div class="settings-section">
            <h2>Default Agent</h2>
            <p class="section-description">
              Choose which agent to use by default for new conversations
            </p>
            
            <div class="agent-list">
              <div 
                v-for="agent in agents" 
                :key="agent.id"
                class="agent-item"
                :class="{ active: defaultAgent === agent.id }"
                @click="setDefaultAgent(agent.id)"
              >
                <div class="agent-icon">{{ agent.icon }}</div>
                <div class="agent-content">
                  <h3>{{ agent.name }}</h3>
                  <p>{{ agent.description }}</p>
                  <div class="agent-tools">
                    <span v-for="tool in agent.tools" :key="tool" class="tool-badge">
                      {{ tool }}
                    </span>
                  </div>
                </div>
                <div class="agent-check">
                  <div v-if="defaultAgent === agent.id" class="check-icon">✓</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Cloud, Mic, Settings as SettingsIcon, ArrowLeft, Cpu, Sparkles, Box, Wrench, Download, Loader2 } from 'lucide-vue-next'
import { useProjectStore } from '@/stores/project'
import { useSettingsStore } from '@/stores/settings'
import { useModelsStore } from '@/stores/models'
import CustomDropdown from './CustomDropdown.vue'

const projectStore = useProjectStore()
const settingsStore = useSettingsStore()
const modelsStore = useModelsStore()

const activeTab = ref('providers')
const tabs = [
  { id: 'providers', label: 'Providers', icon: Cloud },
  { id: 'audio', label: 'Audio', icon: Mic },
  { id: 'advanced', label: 'Advanced', icon: Wrench }
]

const apiKeys = ref({})
const selectedModels = ref({})
const connecting = ref(false)

// Provider management
const availableProviders = computed(() => modelsStore.providers)
const connectedProviders = computed(() => modelsStore.connectedProviders)
const providerModels = computed(() => modelsStore.providerModels)
const currentModel = computed(() => modelsStore.currentModel)
const currentProviderId = computed(() => currentModel.value?.providerId)

function isProviderConnected(providerId) {
  return modelsStore.isProviderConnected(providerId)
}

async function saveApiKey(providerId) {
  const key = apiKeys.value[providerId]
  if (!key) return
  
  try {
    connecting.value = true
    await modelsStore.setApiKey(providerId, key)
    apiKeys.value[providerId] = '' // Clear input after success
    alert(`Successfully connected to ${providerId}!`)
  } catch (err) {
    alert(`Failed to connect: ${err.message}`)
  } finally {
    connecting.value = false
  }
}

async function setModel(providerId, modelId) {
  if (!modelId) return
  try {
    await modelsStore.setModel(providerId, modelId)
  } catch (err) {
    alert(`Failed to set model: ${err.message}`)
  }
}

function getProviderIcon(providerId) {
  const icons = {
    anthropic: Cpu,
    openai: Sparkles,
    'aws-bedrock': Cloud
  }
  return icons[providerId] || Box
}

function getProviderUrl(providerId) {
  const urls = {
    anthropic: 'https://console.anthropic.com/',
    openai: 'https://platform.openai.com/api-keys',
    'aws-bedrock': 'https://console.aws.amazon.com/bedrock'
  }
  return urls[providerId] || '#'
}

function getModelOptions(providerId) {
  const models = providerModels.value[providerId] || []
  return models.map(model => ({
    id: model.id,
    name: model.name || model.id,
    value: model.id
  }))
}

// Agents
const agents = ref([
  {
    id: 'build',
    name: 'Build',
    icon: '🔨',
    description: 'General-purpose coding with full tool access',
    tools: ['read', 'write', 'edit', 'bash']
  },
  {
    id: 'explore',
    name: 'Explore',
    icon: '🔍',
    description: 'Fast read-only agent for understanding code',
    tools: ['read', 'search', 'glob', 'grep']
  },
  {
    id: 'plan',
    name: 'Plan',
    icon: '📋',
    description: 'Creates execution plans',
    tools: ['read', 'search']
  },
  {
    id: 'architect',
    name: 'Architect',
    icon: '🏗️',
    description: 'System design and architecture',
    tools: ['read', 'search']
  },
  {
    id: 'fix',
    name: 'Fix',
    icon: '🔧',
    description: 'Bug fixing specialist',
    tools: ['read', 'write', 'edit', 'bash']
  }
])

const defaultAgent = computed(() => settingsStore.defaultAgent)

function setDefaultAgent(agentId) {
  settingsStore.setDefaultAgent(agentId)
}

// Audio/Whisper settings
const autoRecordMode = computed({
  get: () => settingsStore.autoRecordMode,
  set: (value) => settingsStore.setAutoRecordMode(value)
})

const whisperModels = ref([])
const loadingWhisperModels = ref(false)
const whisperModelsError = ref(null)
const selectedWhisperModel = ref('')
const downloadingModel = ref(null)
const downloadProgress = ref(0)
let downloadEventSource = null

async function loadWhisperModels() {
  try {
    loadingWhisperModels.value = true
    const response = await fetch('http://127.0.0.1:8001/api/whisper/models')
    const data = await response.json()
    if (data.success) {
      whisperModels.value = data.models
      selectedWhisperModel.value = settingsStore.whisperModelId || data.current_model || 'base'
    }
  } catch (err) {
    whisperModelsError.value = err.message
    console.error('Failed to load Whisper models:', err)
  } finally {
    loadingWhisperModels.value = false
  }
}

function selectModel(modelId) {
  selectedWhisperModel.value = modelId
  onWhisperModelChange(modelId)
}

async function downloadModel(modelId) {
  if (downloadingModel.value) {
    return // Already downloading
  }
  
  try {
    downloadingModel.value = modelId
    downloadProgress.value = 0
    
    const response = await fetch('http://127.0.0.1:8001/api/whisper/download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ model_id: modelId })
    })
    
    if (!response.ok) {
      throw new Error(`Failed to start download: ${response.statusText}`)
    }
    
    // Handle SSE stream
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.progress !== undefined) {
              downloadProgress.value = data.progress
            }
            if (data.type === 'complete') {
              downloadProgress.value = 100
              await loadWhisperModels() // Reload to update download status
              downloadingModel.value = null
              downloadProgress.value = 0
              return
            }
            if (data.type === 'error') {
              throw new Error(data.message || 'Download failed')
            }
          } catch (e) {
            // Ignore JSON parse errors for incomplete chunks
          }
        }
      }
    }
  } catch (err) {
    alert(`Failed to download model: ${err.message}`)
    downloadingModel.value = null
    downloadProgress.value = 0
  }
}

function onWhisperModelChange(modelId) {
  settingsStore.setWhisperModelId(modelId)
}

function goBack() {
  projectStore.showSettings = false
}

// Load data on mount
onMounted(async () => {
  console.log('[SettingsPage] Loading providers and config...')
  await modelsStore.loadProviders()
  await loadWhisperModels()
  
  console.log('[SettingsPage] Current model:', currentModel.value)
  console.log('[SettingsPage] Available providers:', availableProviders.value.length)
  console.log('[SettingsPage] Connected providers:', connectedProviders.value)
  console.log('[SettingsPage] Provider models:', Object.keys(providerModels.value))
  
  // Set initial selected models
  if (currentModel.value) {
    selectedModels.value[currentModel.value.providerId] = currentModel.value.modelId
  }
})

onUnmounted(() => {
  if (downloadEventSource) {
    downloadEventSource.close()
    downloadEventSource = null
  }
})
</script>

<style scoped>
.settings-page {
  height: 100vh;
  display: flex;
  background: var(--background);
}

.settings-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--sidebar);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
  height: var(--header-md);
  min-height: var(--header-md);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.back-button {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  transition: all 0.2s;
}

.back-button:hover {
  background: var(--accent);
  color: var(--foreground);
}

.settings-icon {
  color: var(--muted-foreground);
}

.settings-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--foreground);
}

.settings-tabs {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
  background: var(--muted);
}

.tab-button {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  border-radius: var(--radius-md);
  font-size: 12px;
  transition: all 0.2s;
}

.tab-button:hover {
  background: var(--accent);
  color: var(--foreground);
}

.tab-button.active {
  background: var(--primary);
  color: var(--primary-foreground);
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

.tab-content {
  max-width: 900px;
  margin: 0 auto;
}

.settings-section {
  margin-bottom: var(--space-8);
}

.settings-section h2 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: var(--space-2);
  color: var(--foreground);
}

.section-description {
  color: var(--muted-foreground);
  margin-bottom: var(--space-6);
  line-height: 1.5;
  font-size: 12px;
}

/* Provider Cards */
.provider-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.provider-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: all 0.2s;
  background: var(--card);
}

.provider-card:hover {
  border-color: var(--ring);
}

.provider-card.connected {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 5%, var(--card) 95%);
}

.provider-card.active {
  box-shadow: 0 0 0 2px var(--primary);
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-4);
}

.provider-left {
  display: flex;
  gap: var(--space-3);
  flex: 1;
}

.provider-icon {
  flex-shrink: 0;
  color: var(--primary);
}

.provider-info h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--foreground);
}

.provider-status {
  flex-shrink: 0;
}

.status-badge {
  font-size: 11px;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.status-badge.connected {
  background: var(--primary);
  color: var(--primary-foreground);
}

.status-badge.disconnected {
  background: var(--muted);
  color: var(--muted-foreground);
}

.provider-auth {
  margin-top: var(--space-4);
}

.provider-auth label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
  margin-bottom: var(--space-2);
}

.api-key-input-group {
  display: flex;
  gap: var(--space-2);
}

.api-key-input {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-family: monospace;
  font-size: 12px;
  background: var(--background);
  color: var(--foreground);
}

.api-key-input:focus {
  outline: none;
  border-color: var(--ring);
}

.btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 500;
  font-size: 12px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-primary {
  background: var(--primary);
  color: var(--primary-foreground);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: var(--space-2) var(--space-3);
  font-size: 11px;
}

.btn-active {
  background: var(--primary);
  color: var(--primary-foreground);
}

.help-text {
  font-size: 11px;
  color: var(--muted-foreground);
  margin-top: var(--space-2);
}

.help-text a {
  color: var(--primary);
  text-decoration: none;
}

.help-text a:hover {
  text-decoration: underline;
}

.provider-models label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
  margin-bottom: var(--space-2);
}

.config-display {
  background: var(--muted);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border);
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  font-weight: 500;
  color: var(--muted-foreground);
  font-size: 12px;
}

.config-value {
  font-family: monospace;
  color: var(--foreground);
  font-size: 12px;
}

/* Agent List - Compact */
.agent-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.agent-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  background: var(--card);
}

.agent-item:hover {
  border-color: var(--ring);
  background: var(--accent);
}

.agent-item.active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, var(--card) 90%);
}

.agent-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.agent-content {
  flex: 1;
}

.agent-content h3 {
  margin: 0 0 var(--space-1) 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--foreground);
}

.agent-content p {
  font-size: 11px;
  color: var(--muted-foreground);
  margin: 0 0 var(--space-2) 0;
  line-height: 1.4;
}

.agent-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.tool-badge {
  font-size: 10px;
  padding: 2px var(--space-2);
  background: var(--muted);
  border-radius: var(--radius-sm);
  color: var(--muted-foreground);
}

.agent-check {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.check-icon {
  color: var(--primary);
  font-weight: bold;
  font-size: 14px;
}

/* Audio Settings */
.setting-item {
  margin-bottom: var(--space-6);
}

.setting-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}

.setting-info {
  flex: 1;
}

.setting-label {
  font-weight: 500;
  color: var(--foreground);
  display: block;
  margin-bottom: var(--space-1);
  font-size: 12px;
}

.setting-description {
  font-size: 11px;
  color: var(--muted-foreground);
  line-height: 1.4;
}

.switch-container {
  position: relative;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch-input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--muted);
  transition: 0.3s;
  border-radius: 24px;
}

.switch-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: var(--background);
  transition: 0.3s;
  border-radius: 50%;
}

.switch-input:checked + .switch-slider {
  background-color: var(--primary);
}

.switch-input:checked + .switch-slider:before {
  transform: translateX(20px);
}

/* Whisper Models List */
.whisper-models-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.whisper-model-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--card);
  transition: all 0.2s;
}

.whisper-model-item:hover {
  border-color: var(--ring);
}

.whisper-model-item.active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, var(--card) 90%);
}

.whisper-model-item.downloaded {
  border-color: var(--primary);
}

.model-info {
  flex: 1;
}

.model-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.model-name {
  font-weight: 500;
  color: var(--foreground);
  font-size: 12px;
}

.downloaded-badge {
  font-size: 10px;
  padding: 2px var(--space-2);
  background: var(--primary);
  color: var(--primary-foreground);
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.not-downloaded-badge {
  font-size: 10px;
  padding: 2px var(--space-2);
  background: var(--muted);
  color: var(--muted-foreground);
  border-radius: var(--radius-sm);
}

.model-details {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 11px;
  color: var(--muted-foreground);
}

.model-separator {
  color: var(--muted-foreground);
}

.model-actions {
  flex-shrink: 0;
}

.download-progress {
  width: 100%;
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--muted);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s;
}

.progress-text {
  font-size: 10px;
  color: var(--muted-foreground);
  min-width: 40px;
  text-align: right;
}

.loading,
.error-message {
  text-align: center;
  padding: var(--space-8);
  color: var(--muted-foreground);
  font-size: 12px;
}

.error-message {
  color: var(--destructive);
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
