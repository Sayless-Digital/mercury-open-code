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
                  <div class="provider-icon">
                    <component :is="getProviderIcon(provider.id)" :size="32" />
                  </div>
                  <div class="provider-info">
                    <h3>{{ provider.name || provider.id }}</h3>
                    <span class="provider-status">
                      <span v-if="isProviderConnected(provider.id)" class="status-badge connected">
                        ✓ Connected
                      </span>
                      <span v-else class="status-badge disconnected">
                        ○ Not configured
                      </span>
                    </span>
                  </div>
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
                      class="btn btn-sm btn-primary"
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
            <p class="section-description">Select which Whisper model to use for voice transcriptions</p>
            
            <div v-if="loadingWhisperModels" class="loading">Loading models...</div>
            <div v-else-if="whisperModelsError" class="error-message">
              {{ whisperModelsError }}
            </div>
            <div v-else>
              <div class="setting-item whisper-setting-item">
                <label class="setting-label" for="whisper-model-select">Transcription Model</label>
                <p class="setting-description">
                  Choose the Whisper model for transcribing your voice recordings
                </p>
                <div class="whisper-dropdown-wrapper-full">
                  <CustomDropdown
                    v-model="selectedWhisperModel"
                    :options="whisperModelOptions"
                    placeholder="Select Whisper model..."
                    option-label="name"
                    option-value="id"
                    @change="onWhisperModelChange"
                  />
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
            
            <div class="agent-grid">
              <div 
                v-for="agent in agents" 
                :key="agent.id"
                class="agent-card"
                :class="{ active: defaultAgent === agent.id }"
                @click="setDefaultAgent(agent.id)"
              >
                <div class="agent-icon">{{ agent.icon }}</div>
                <h3>{{ agent.name }}</h3>
                <p>{{ agent.description }}</p>
                <div class="agent-tools">
                  <span v-for="tool in agent.tools" :key="tool" class="tool-badge">
                    {{ tool }}
                  </span>
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
import { ref, computed, onMounted } from 'vue'
import { Cloud, Mic, Settings as SettingsIcon, ArrowLeft, Cpu, Sparkles, Box, Wrench } from 'lucide-vue-next'
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

const whisperModelOptions = computed(() => {
  return whisperModels.value.map(model => ({
    id: model.id,
    name: `${model.name}${model.downloaded ? ' ✓' : ''} - ${model.description}`
  }))
})

async function loadWhisperModels() {
  try {
    loadingWhisperModels.value = true
    const response = await fetch('http://127.0.0.1:8001/api/whisper/models')
    const data = await response.json()
    if (data.success) {
      whisperModels.value = data.models
      selectedWhisperModel.value = data.current_model || 'base'
    }
  } catch (err) {
    whisperModelsError.value = err.message
    console.error('Failed to load Whisper models:', err)
  } finally {
    loadingWhisperModels.value = false
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
</script>

<style scoped>
.settings-page {
  height: 100vh;
  display: flex;
  background: var(--bg-primary);
}

.settings-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.back-button {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.back-button:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.settings-icon {
  color: var(--text-secondary);
}

.settings-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.settings-tabs {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.tab-button:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.tab-button.active {
  background: var(--primary-color);
  color: white;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.tab-content {
  max-width: 900px;
  margin: 0 auto;
}

.settings-section {
  margin-bottom: 2rem;
}

.settings-section h2 {
  font-size: 1.3rem;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.section-description {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

/* Provider Cards */
.provider-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.provider-card {
  border: 2px solid var(--border-color);
  border-radius: 8px;
  padding: 1.5rem;
  transition: all 0.2s;
  background: var(--bg-secondary);
}

.provider-card:hover {
  border-color: var(--primary-color-dim);
}

.provider-card.connected {
  border-color: var(--success-color);
  background: rgba(34, 197, 94, 0.05);
}

.provider-card.active {
  box-shadow: 0 0 0 2px var(--primary-color);
}

.provider-header {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.provider-icon {
  flex-shrink: 0;
  color: var(--primary-color);
}

.provider-info h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.status-badge {
  font-size: 0.85rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.status-badge.connected {
  background: var(--success-color);
  color: white;
}

.status-badge.disconnected {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.provider-auth {
  margin-top: 1rem;
}

.provider-auth label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.api-key-input-group {
  display: flex;
  gap: 0.5rem;
}

.api-key-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: monospace;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.api-key-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color-bright);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: 0.4rem 0.8rem;
  font-size: 0.9rem;
}

.help-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

.help-text a {
  color: var(--primary-color);
  text-decoration: none;
}

.help-text a:hover {
  text-decoration: underline;
}

.provider-models label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.model-select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
}

.model-select:focus {
  outline: none;
  border-color: var(--primary-color);
}

.config-display {
  background: var(--bg-secondary);
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color);
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.config-value {
  font-family: monospace;
  color: var(--text-primary);
}

/* Agent Grid */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.agent-card {
  border: 2px solid var(--border-color);
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  background: var(--bg-secondary);
}

.agent-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.agent-card.active {
  border-color: var(--primary-color);
  background: rgba(59, 130, 246, 0.1);
}

.agent-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.agent-card h3 {
  margin: 0.5rem 0;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.agent-card p {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin: 0.5rem 0;
}

.agent-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  justify-content: center;
  margin-top: 0.75rem;
}

.tool-badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.4rem;
  background: var(--bg-tertiary);
  border-radius: 4px;
  color: var(--text-secondary);
}

/* Audio Settings */
.setting-item {
  margin-bottom: 1.5rem;
}

.setting-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.setting-info {
  flex: 1;
}

.setting-label {
  font-weight: 600;
  color: var(--text-primary);
  display: block;
  margin-bottom: 0.25rem;
}

.setting-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.switch-container {
  position: relative;
  width: 48px;
  height: 24px;
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
  background-color: var(--bg-tertiary);
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
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.switch-input:checked + .switch-slider {
  background-color: var(--primary-color);
}

.switch-input:checked + .switch-slider:before {
  transform: translateX(24px);
}

.whisper-dropdown-wrapper-full {
  width: 100%;
  margin-top: 0.5rem;
}

.loading,
.error-message {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary);
}

.error-message {
  color: var(--error-color);
}
</style>
