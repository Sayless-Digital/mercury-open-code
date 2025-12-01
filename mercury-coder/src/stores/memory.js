import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

const API_BASE = 'http://127.0.0.1:8000';

const request = async (path, options = {}) => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed');
  }
  return data;
};

export const useMemoryStore = defineStore('memory', () => {
  const memories = ref([]);
  const conversations = ref([]);
  const taskSummaries = ref([]);
  const stats = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const searchQuery = ref('');
  const selectedMemoryType = ref(null);
  const selectedProject = ref(null);

  // Computed
  const filteredMemories = computed(() => {
    let filtered = memories.value;

    if (selectedMemoryType.value) {
      filtered = filtered.filter(m => m.memory_type === selectedMemoryType.value);
    }

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(m => 
        (m.title || '').toLowerCase().includes(query) ||
        m.content.toLowerCase().includes(query)
      );
    }

    return filtered;
  });

  const memoryTypes = computed(() => {
    const types = new Set(memories.value.map(m => m.memory_type));
    return Array.from(types);
  });

  // Actions
  const loadMemories = async (projectPath = null, memoryType = null) => {
    loading.value = true;
    error.value = null;
    try {
      const params = new URLSearchParams();
      if (projectPath) params.append('project_path', projectPath);
      if (memoryType) params.append('memory_type', memoryType);
      params.append('limit', '100');

      const data = await request(`/api/memory/list?${params}`);
      memories.value = data.memories || [];
    } catch (err) {
      error.value = err.message;
      console.error('Failed to load memories:', err);
    } finally {
      loading.value = false;
    }
  };

  const searchMemories = async (query, projectPath = null) => {
    loading.value = true;
    error.value = null;
    try {
      const params = new URLSearchParams();
      params.append('query', query);
      if (projectPath) params.append('project_path', projectPath);
      params.append('limit', '50');

      const data = await request(`/api/memory/search?${params}`);
      memories.value = data.memories || [];
      searchQuery.value = query;
    } catch (err) {
      error.value = err.message;
      console.error('Failed to search memories:', err);
    } finally {
      loading.value = false;
    }
  };

  const deleteMemory = async (memoryId) => {
    try {
      await request(`/api/memory/${memoryId}`, { method: 'DELETE' });
      memories.value = memories.value.filter(m => m.id !== memoryId);
      return true;
    } catch (err) {
      error.value = err.message;
      console.error('Failed to delete memory:', err);
      return false;
    }
  };

  const loadConversations = async (projectPath = null, sessionId = null) => {
    loading.value = true;
    error.value = null;
    try {
      const params = new URLSearchParams();
      if (projectPath) params.append('project_path', projectPath);
      if (sessionId) params.append('session_id', sessionId);
      params.append('limit', '100');

      const data = await request(`/api/memory/conversations?${params}`);
      conversations.value = data.conversations || [];
    } catch (err) {
      error.value = err.message;
      console.error('Failed to load conversations:', err);
    } finally {
      loading.value = false;
    }
  };

  const loadTaskSummaries = async (projectPath = null) => {
    loading.value = true;
    error.value = null;
    try {
      const params = new URLSearchParams();
      if (projectPath) params.append('project_path', projectPath);
      params.append('limit', '50');

      const data = await request(`/api/memory/task-summaries?${params}`);
      taskSummaries.value = data.summaries || [];
    } catch (err) {
      error.value = err.message;
      console.error('Failed to load task summaries:', err);
    } finally {
      loading.value = false;
    }
  };

  const loadStats = async (projectPath = null) => {
    try {
      const params = new URLSearchParams();
      if (projectPath) params.append('project_path', projectPath);

      const data = await request(`/api/memory/stats?${params}`);
      stats.value = data.stats;
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const clearFilters = () => {
    searchQuery.value = '';
    selectedMemoryType.value = null;
  };

  return {
    // State
    memories,
    conversations,
    taskSummaries,
    stats,
    loading,
    error,
    searchQuery,
    selectedMemoryType,
    selectedProject,
    // Computed
    filteredMemories,
    memoryTypes,
    // Actions
    loadMemories,
    searchMemories,
    deleteMemory,
    loadConversations,
    loadTaskSummaries,
    loadStats,
    clearFilters,
  };
});






