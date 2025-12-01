<template>
  <div class="memory-page">
    <div class="memory-panel">
      <!-- Header -->
    <div class="memory-header">
        <div class="header-left">
      <button class="back-button" @click="goBack" title="Back">
            <ArrowLeft :size="16" />
      </button>
          <Brain class="memory-icon" :size="14" />
          <span class="memory-title">Memory Management</span>
        </div>
        <button class="refresh-btn" @click="refresh" :disabled="loading" title="Refresh">
          <RefreshCw :size="14" :class="{ spinning: loading }" />
        </button>
    </div>
    
      <!-- Stats Bar -->
      <div class="stats-bar" v-if="stats">
      <div class="stat-item">
        <span class="stat-label">Memories:</span>
        <span class="stat-value">{{ stats.total_memories || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Conversations:</span>
        <span class="stat-value">{{ stats.total_conversations || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Tasks:</span>
        <span class="stat-value">{{ stats.total_task_summaries || 0 }}</span>
      </div>
      <div class="stat-item" v-if="stats.vector_store_enabled">
        <span class="stat-badge">Vector Search Enabled</span>
      </div>
      </div>

      <!-- Tabs -->
      <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
      </div>

      <!-- Search and Filters -->
      <div class="filters">
      <div class="search-box">
          <Search :size="14" />
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          placeholder="Search memories..."
          class="search-input"
        />
        <button
          v-if="searchQuery"
          @click="clearSearch"
          class="clear-search"
          title="Clear search"
        >
          <X :size="14" />
        </button>
      </div>
        <div class="type-filter-wrapper">
          <CustomDropdown
        v-model="selectedMemoryType"
            :options="memoryTypeOptions"
            placeholder="All Types"
        @change="handleFilterChange"
          />
        </div>
      </div>

      <!-- Content Area -->
      <div class="memory-content">
      <!-- Memories Tab -->
      <div v-if="activeTab === 'memories'" class="tab-content">
        <div v-if="loading" class="loading-state">
          <Loader2 :size="20" class="spinner" />
          <span>Loading memories...</span>
        </div>
        <div v-else-if="error" class="error-state">
          <AlertCircle :size="20" />
          <span>{{ error }}</span>
        </div>
        <div v-else-if="filteredMemories.length === 0" class="empty-state">
          <Brain :size="32" />
          <p>No memories found</p>
          <p class="empty-hint">Memories are created automatically as you chat</p>
        </div>
        <div v-else class="memory-list">
          <div
            v-for="memory in filteredMemories"
            :key="memory.id"
            class="memory-item"
          >
            <div class="memory-item-header">
              <div class="memory-meta">
                <span class="memory-type-badge" :class="memory.memory_type">
                  {{ formatType(memory.memory_type) }}
                </span>
                <span class="memory-title-text" v-if="memory.title">
                  {{ memory.title }}
                </span>
                <span class="memory-date">{{ formatDate(memory.created_at) }}</span>
              </div>
              <div class="memory-actions">
                <span class="memory-stats">
                  <Star :size="12" />
                  {{ memory.importance.toFixed(1) }}
                  <span class="separator">•</span>
                  <TrendingUp :size="12" />
                  {{ memory.usage_count }}
                </span>
                <button
                  @click="handleDeleteMemory(memory.id)"
                  class="delete-btn"
                  title="Delete memory"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
            <div class="memory-content-text">
              {{ truncate(memory.content, 300) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Conversations Tab -->
      <div v-if="activeTab === 'conversations'" class="tab-content">
        <div v-if="loading" class="loading-state">
          <Loader2 :size="20" class="spinner" />
          <span>Loading conversations...</span>
        </div>
        <div v-else-if="error" class="error-state">
          <AlertCircle :size="20" />
          <span>{{ error }}</span>
        </div>
        <div v-else-if="conversations.length === 0" class="empty-state">
          <MessageSquare :size="32" />
          <p>No conversations found</p>
        </div>
        <div v-else class="conversation-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="conversation-item"
            :class="conv.role"
          >
            <div class="conversation-role">{{ conv.role }}</div>
            <div class="conversation-content">{{ truncate(conv.content, 200) }}</div>
            <div class="conversation-date">{{ formatDate(conv.created_at) }}</div>
          </div>
        </div>
      </div>

      <!-- Task Summaries Tab -->
      <div v-if="activeTab === 'summaries'" class="tab-content">
        <div v-if="loading" class="loading-state">
          <Loader2 :size="20" class="spinner" />
          <span>Loading task summaries...</span>
        </div>
        <div v-else-if="error" class="error-state">
          <AlertCircle :size="20" />
          <span>{{ error }}</span>
        </div>
        <div v-else-if="taskSummaries.length === 0" class="empty-state">
          <CheckCircle :size="32" />
          <p>No task summaries found</p>
        </div>
        <div v-else class="summary-list">
          <div
            v-for="summary in taskSummaries"
            :key="summary.id"
            class="summary-item"
            :class="{ success: summary.success, failed: !summary.success }"
          >
            <div class="summary-header">
              <div class="summary-status">
                <CheckCircle v-if="summary.success" :size="16" class="success-icon" />
                <XCircle v-else :size="16" class="failed-icon" />
                <span class="summary-goal">{{ summary.task_goal }}</span>
              </div>
              <span class="summary-date">{{ formatDate(summary.created_at) }}</span>
            </div>
            <div class="summary-content">{{ truncate(summary.summary, 250) }}</div>
          </div>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import {
  RefreshCw, X, Search, Loader2, AlertCircle, Brain, Star, TrendingUp,
  Trash2, MessageSquare, CheckCircle, XCircle, ArrowLeft
} from 'lucide-vue-next';
import { useMemoryStore } from '@/stores/memory';
import { useProjectStore } from '@/stores/project';
import CustomDropdown from './CustomDropdown.vue';

const emit = defineEmits(['close']);

const goBack = () => {
  projectStore.showMemoryBrowser = false;
};

const memoryStore = useMemoryStore();
const projectStore = useProjectStore();

const activeTab = ref('memories');
const tabs = [
  { id: 'memories', label: 'Memories' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'summaries', label: 'Task Summaries' }
];

const searchQuery = computed({
  get: () => memoryStore.searchQuery,
  set: (value) => { memoryStore.searchQuery = value; }
});

const selectedMemoryType = computed({
  get: () => memoryStore.selectedMemoryType,
  set: (value) => { memoryStore.selectedMemoryType = value; }
});

const loading = computed(() => memoryStore.loading);
const error = computed(() => memoryStore.error);
const filteredMemories = computed(() => memoryStore.filteredMemories);
const memoryTypes = computed(() => memoryStore.memoryTypes);
const conversations = computed(() => memoryStore.conversations);
const taskSummaries = computed(() => memoryStore.taskSummaries);
const stats = computed(() => memoryStore.stats);

const memoryTypeOptions = computed(() => {
  return [
    { label: 'All Types', value: '' },
    ...memoryTypes.value.map(type => ({
      label: formatType(type),
      value: type
    }))
  ];
});

const handleSearch = () => {
  if (searchQuery.value.length >= 2) {
    memoryStore.searchMemories(searchQuery.value, projectStore.currentProject?.path);
  } else if (searchQuery.value.length === 0) {
    loadCurrentTab();
  }
};

const clearSearch = () => {
  memoryStore.searchQuery = '';
  loadCurrentTab();
};

const handleFilterChange = () => {
  loadCurrentTab();
};

const loadCurrentTab = () => {
  const projectPath = projectStore.currentProject?.path;
  
  if (activeTab.value === 'memories') {
    memoryStore.loadMemories(projectPath, selectedMemoryType.value);
  } else if (activeTab.value === 'conversations') {
    memoryStore.loadConversations(projectPath);
  } else if (activeTab.value === 'summaries') {
    memoryStore.loadTaskSummaries(projectPath);
  }
};

const refresh = () => {
  loadCurrentTab();
  memoryStore.loadStats(projectStore.currentProject?.path);
};

const handleDeleteMemory = async (memoryId) => {
  if (confirm('Are you sure you want to delete this memory?')) {
    const success = await memoryStore.deleteMemory(memoryId);
    if (success) {
      // Reload to update list
      loadCurrentTab();
    }
  }
};

const formatType = (type) => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const truncate = (text, length) => {
  if (!text) return '';
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
};

// Watch tab changes
watch(activeTab, () => {
  loadCurrentTab();
});

// Load on mount
onMounted(() => {
  refresh();
});
</script>

<style scoped>
.memory-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--background);
  padding: var(--space-4);
}

.memory-panel {
  width: 100%;
  max-width: 1000px;
  height: calc(100vh - var(--space-8));
  display: flex;
  flex-direction: column;
  background: var(--card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.memory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
  height: var(--header-md);
  min-height: var(--header-md);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.back-button {
  background: none;
  border: none;
  color: var(--foreground);
  cursor: pointer;
  padding: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
}

.back-button:hover {
  background: var(--accent);
}

.memory-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ring);
  flex-shrink: 0;
}

.memory-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--foreground);
}

.refresh-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: var(--accent);
  color: var(--foreground);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.stats-bar {
  display: flex;
  gap: var(--space-8);
  padding: var(--space-4) var(--space-6);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.stat-label {
  color: var(--muted-foreground);
}

.stat-value {
  font-weight: 600;
  color: var(--foreground);
}

.stat-badge {
  padding: var(--space-1) var(--space-4);
  background: var(--primary);
  color: var(--primary-foreground);
  border-radius: var(--radius-sm);
  font-size: 11px;
}

.tabs {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
}

.tab {
  padding: var(--space-2) var(--space-6);
  background: var(--accent);
  border: none;
  color: var(--foreground);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 13px;
  transition: all 0.2s;
  height: var(--button-sm);
}

.tab:hover {
  background: var(--muted);
}

.tab.active {
  background: var(--card);
  font-weight: 500;
  color: var(--foreground);
}

.filters {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--card);
  border-bottom: 1px solid var(--border);
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-6);
  background: var(--muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.search-box svg {
  color: var(--muted-foreground);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: none;
  border: none;
  color: var(--foreground);
  font-size: 13px;
  outline: none;
}

.clear-search {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: var(--space-1);
  display: flex;
  align-items: center;
  border-radius: var(--radius-xs);
}

.clear-search:hover {
  background: var(--accent);
  color: var(--foreground);
}


.memory-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-8);
  background: var(--card);
}

.tab-content {
  height: 100%;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-6);
  padding: var(--space-24) var(--space-12);
  color: var(--muted-foreground);
  text-align: center;
}

.loading-state svg,
.error-state svg,
.empty-state svg {
  opacity: 0.5;
}

.error-state {
  color: var(--destructive);
}

.empty-hint {
  font-size: 12px;
  opacity: 0.7;
}

.memory-list,
.conversation-list,
.summary-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.memory-item {
  padding: var(--space-6);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  transition: all 0.2s;
}

.memory-item:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.memory-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.memory-meta {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
}

.memory-type-badge {
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
}

.memory-type-badge.user_preference {
  background: var(--info);
  color: var(--info-foreground);
}

.memory-type-badge.code_pattern {
  background: var(--success);
  color: var(--success-foreground);
}

.memory-type-badge.solution {
  background: var(--warning);
  color: var(--warning-foreground);
}

.memory-type-badge.context {
  background: var(--primary);
  color: var(--primary-foreground);
}

.memory-title-text {
  font-weight: 600;
  color: var(--foreground);
  font-size: 13px;
}

.memory-date {
  font-size: 11px;
  color: var(--muted-foreground);
  margin-left: auto;
}

.memory-actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.memory-stats {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 11px;
  color: var(--muted-foreground);
}

.memory-stats svg {
  width: var(--icon-xs);
  height: var(--icon-xs);
}

.separator {
  margin: 0 var(--space-2);
}

.delete-btn {
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

.delete-btn:hover {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.memory-content-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--foreground);
  white-space: pre-wrap;
}

.conversation-item {
  padding: var(--space-6);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  border-left: 3px solid var(--border);
}

.conversation-item.user {
  border-left-color: var(--info);
}

.conversation-item.assistant {
  border-left-color: var(--success);
}

.conversation-role {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--muted-foreground);
  margin-bottom: var(--space-2);
}

.conversation-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--foreground);
  margin-bottom: var(--space-2);
}

.conversation-date {
  font-size: 11px;
  color: var(--muted-foreground);
}

.summary-item {
  padding: var(--space-6);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  border-left: 3px solid var(--border);
}

.summary-item.success {
  border-left-color: var(--success);
}

.summary-item.failed {
  border-left-color: var(--destructive);
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.summary-status {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
}

.summary-status svg {
  flex-shrink: 0;
}

.success-icon {
  color: var(--success);
}

.failed-icon {
  color: var(--destructive);
}

.summary-goal {
  font-weight: 600;
  color: var(--foreground);
  font-size: 13px;
}

.summary-date {
  font-size: 11px;
  color: var(--muted-foreground);
}

.summary-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--foreground);
}

.memory-content::-webkit-scrollbar {
  width: var(--space-3);
}

.memory-content::-webkit-scrollbar-track {
  background: transparent;
}

.memory-content::-webkit-scrollbar-thumb {
  background: var(--accent);
  border-radius: var(--radius-xs);
}

.memory-content::-webkit-scrollbar-thumb:hover {
  background: var(--border);
}

.type-filter-wrapper {
  width: 200px;
  flex-shrink: 0;
}
</style>
