import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';

const SETTINGS_KEY = 'mercury-coder-settings';

// Default settings
const defaultSettings = {
  voiceRecorder: {
    autoRecordMode: false,
    whisperModelId: null,
  },
  opencode: {
    serverUrl: 'http://127.0.0.1:4096',
    defaultAgent: 'build',  // build, explore, plan, architect, fix
    autoStartServer: true
  }
};

// Load settings from localStorage
function loadSettings() {
  if (typeof window === 'undefined') {
    return defaultSettings;
  }
  
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to ensure all settings exist
      return {
        ...defaultSettings,
        ...parsed,
        voiceRecorder: {
          ...defaultSettings.voiceRecorder,
          ...(parsed.voiceRecorder || {}),
        },
        opencode: {
          ...defaultSettings.opencode,
          ...(parsed.opencode || {}),
        },
      };
    }
  } catch (error) {
    console.error('Error loading settings:', error);
  }
  
  return defaultSettings;
}

// Save settings to localStorage
function saveSettings(settings) {
  if (typeof window === 'undefined') {
    return;
  }
  
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(loadSettings());

  // Watch for changes and auto-save
  watch(
    settings,
    (newSettings) => {
      saveSettings(newSettings);
    },
    { deep: true }
  );

  // Voice recorder settings
  const autoRecordMode = computed(() => settings.value.voiceRecorder.autoRecordMode);
  const whisperModelId = computed(() => settings.value.voiceRecorder.whisperModelId);

  function setAutoRecordMode(enabled) {
    settings.value.voiceRecorder.autoRecordMode = enabled;
  }

  function setWhisperModelId(modelId) {
    settings.value.voiceRecorder.whisperModelId = modelId;
  }

  // OpenCode settings
  const opcodeSettings = computed(() => settings.value.opencode);
  const defaultAgent = computed(() => settings.value.opencode.defaultAgent);

  function setDefaultAgent(agentName) {
    const validAgents = ['build', 'explore', 'plan', 'architect', 'fix'];
    if (!validAgents.includes(agentName)) {
      console.warn(`Invalid agent: ${agentName}`);
      return;
    }
    settings.value.opencode.defaultAgent = agentName;
  }

  function setOpenCodeServerUrl(url) {
    settings.value.opencode.serverUrl = url;
  }

  function setAutoStartServer(enabled) {
    settings.value.opencode.autoStartServer = enabled;
  }

  return {
    settings,
    autoRecordMode,
    whisperModelId,
    setAutoRecordMode,
    setWhisperModelId,
    opcodeSettings,
    defaultAgent,
    setDefaultAgent,
    setOpenCodeServerUrl,
    setAutoStartServer,
  };
});
