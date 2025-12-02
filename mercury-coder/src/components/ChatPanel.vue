mercury
<template>
  <div class="chat-panel">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <div class="header-tabs" ref="headerTabsRef">
          <div 
            class="header-tabs-background"
            :style="backgroundStyle"
          ></div>
          <button 
            ref="mercuryTabRef"
            class="header-tab"
            :class="{ active: !showHistory }"
            @click="showHistory = false"
          >
            <div class="app-logo">
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="7.5" stroke="currentColor" stroke-width="2.5"/>
                <circle cx="10" cy="10" r="3.5" stroke="currentColor" stroke-width="2.5"/>
              </svg>
            </div>
            <span class="header-tab-label">Mercury Coder</span>
          </button>
          <button 
            ref="historyTabRef"
            class="header-tab"
            :class="{ active: showHistory }"
            @click="showHistory = true"
          >
            <History :size="16" />
            <span class="header-tab-label">History</span>
          </button>
        </div>
        <!-- Session Tabs - moved to header -->
        <SessionTabs v-if="!showHistory" class="header-session-tabs" />
      </div>
    </div>
    
    <!-- Session History View -->
    <SessionHistory v-if="showHistory" />
    
    <!-- Chat View -->
    <template v-else>
    
    <!-- Task Control Panel -->
    <TaskControlPanel />
    
      <!-- Messages Area - OpenCode-style turns -->
    <div class="chat-messages" ref="messagesContainer">
      <!-- Debug info (remove in production) -->
      <div v-if="false" style="padding: 10px; background: #f0f0f0; font-size: 12px; margin: 10px;">
        <div>Total messages in map: {{ chatStore.messageMap.size }}</div>
        <div>Total turns: {{ turns.length }}</div>
        <div>Total legacy messages: {{ messages.length }}</div>
        <div v-if="turns.length > 0">
          <div v-for="(turn, idx) in turns" :key="turn.id" style="margin-top: 5px;">
            Turn {{ idx + 1 }}: User msg {{ turn.userMessage.info.id }}, {{ turn.assistantMessages.length }} assistant msgs
          </div>
        </div>
      </div>
      
      <div v-if="turns.length === 0 && messages.length === 0" class="empty-state">
        <div class="empty-state-content">
          <Brain class="empty-state-icon" :size="48" />
          <h3 class="empty-state-title">Ready to help!</h3>
          <p class="empty-state-text">Ask me anything about your codebase, and I'll explore, analyze, and help you build.</p>
        </div>
      </div>
      
      <!-- Fallback: Show legacy messages if turns are empty but messages exist -->
      <template v-if="turns.length === 0 && messages.length > 0">
      <template v-for="(message, index) in messages" :key="message.id">
        <div class="message" :class="message.role">
          <div class="message-content">
            <div v-if="message.content" class="message-text" v-html="formatMessage(message.content)"></div>
            <div v-if="message.streaming" class="streaming-indicator">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              </div>
            </div>
          </div>
        </template>
      </template>
      
      <!-- Display turns (user message + assistant response) -->
      <template v-else v-for="(turn, turnIndex) in turns" :key="turn.id">
        <div class="chat-turn" :data-turn-id="turn.id">
          <!-- User Message -->
          <div class="turn-user-message">
            <div class="message-content">
              <div class="message-text">
                {{ getUserMessageText(turn.userMessage) }}
              </div>
            </div>
          </div>
          
          <!-- Assistant Response(s) -->
          <div v-if="turn.assistantMessages.length > 0" class="turn-assistant-response">
            <template v-for="(assistantMsg, msgIndex) in turn.assistantMessages" :key="assistantMsg.info.id">
              <div class="assistant-message">
                <!-- Message Parts -->
                <div class="message-parts">
                  <template v-for="(part, partIndex) in assistantMsg.parts" :key="part.id">
                    <!-- Text Part -->
                    <div v-if="part.type === 'text'" class="message-part text-part">
                      <div class="text-content" v-html="formatMessage(part.text)"></div>
                    </div>
                    
                    <!-- Tool Part -->
                    <div v-else-if="part.type === 'tool' && isToolReady(part)" class="message-part tool-part" :class="{ 'has-content': hasVisibleContent(part) }">
                      <div class="tool-container">
                        <div 
                          class="tool-header" 
                          :class="{ 
                            'rounded-bottom': !hasVisibleContent(part),
                            'clickable': hasTechnicalDetails(part)
                          }"
                          @click="hasTechnicalDetails(part) && toggleToolDetails(part.callID || part.id)"
                          :style="{ cursor: hasTechnicalDetails(part) ? 'pointer' : 'default' }"
                        >
                          <div class="tool-title-section">
                            <span class="tool-name">
                              <component :is="getToolIcon(part)" class="tool-icon" :size="14" />
                              {{ getToolDisplayName(part) }}
                              <span v-if="getToolSubtitle(part)" class="tool-subtitle-inline">{{ getToolSubtitle(part) }}</span>
                            </span>
                            <span v-if="getToolCount(part)" class="tool-count">
                              <FileText v-if="getToolCountIcon(part) === 'file'" :size="12" />
                              <CheckSquare v-else-if="getToolCountIcon(part) === 'check'" :size="12" />
                              {{ getToolCount(part) }}
                            </span>
                          </div>
                          <div class="tool-header-right">
                            <span v-if="part.state?.status === 'error'" class="tool-status" :class="getToolStatusClass(part.state?.status)">
                              {{ getToolStatusText(part.state?.status) }}
                            </span>
                            <div
                              v-if="hasTechnicalDetails(part)"
                              class="tool-details-toggle-header"
                              @click.stop
                            >
                              <ChevronDown :size="12" :class="{ 'expanded': expandedToolDetails.has(part.callID || part.id) }" />
                            </div>
                          </div>
                        </div>
                        <div v-if="hasVisibleContent(part)" class="tool-content">
                        
                        <!-- Todo list display (todowrite) -->
                        <div v-if="part.tool === 'todowrite' && part.state?.input?.todos" class="tool-todos">
                          <div class="todos-list">
                            <div
                              v-for="(todo, index) in part.state.input.todos"
                              :key="index"
                              class="todo-item"
                              :class="{ 'todo-completed': todo.status === 'completed' }"
                            >
                              <div v-if="todo.status === 'in_progress' || todo.status === 'running'" class="todo-spinner">
                                <RefreshCw :size="14" class="spinner-icon" />
                              </div>
                              <div v-else class="custom-checkbox" :class="{ 'checked': todo.status === 'completed' }">
                                <svg v-if="todo.status === 'completed'" class="checkmark" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                                  <path
                                    d="M3 7.17905L5.02703 8.85135L9 3.5"
                                    stroke="currentColor"
                                    stroke-width="1.5"
                                    stroke-linecap="square"
                                  />
                                </svg>
                              </div>
                              <span class="todo-content" :class="{ 'shimmer-text': todo.status === 'in_progress' || todo.status === 'running' }">{{ todo.content }}</span>
                            </div>
                          </div>
                        </div>
                        
                        <!-- Task list display (task) -->
                        <div v-if="part.tool === 'task' && part.metadata?.summary" class="tool-task-list">
                          <div class="task-description">{{ part.state?.input?.description || 'Task in progress' }}</div>
                          <div v-if="Array.isArray(part.metadata.summary)" class="task-todos">
                            <div
                              v-for="(taskPart, index) in part.metadata.summary"
                              :key="index"
                              class="task-item"
                            >
                              <div v-if="taskPart.state?.input?.todos" class="task-todos-list">
                                <div
                                  v-for="(todo, todoIndex) in taskPart.state.input.todos"
                                  :key="todoIndex"
                                  class="todo-item"
                                  :class="{ 'todo-completed': todo.status === 'completed' }"
                                >
                                  <div v-if="todo.status === 'in_progress' || todo.status === 'running'" class="todo-spinner">
                                    <RefreshCw :size="14" class="spinner-icon" />
                                  </div>
                                  <div v-else class="custom-checkbox" :class="{ 'checked': todo.status === 'completed' }">
                                    <svg v-if="todo.status === 'completed'" class="checkmark" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                                      <path
                                        d="M3 7.17905L5.02703 8.85135L9 3.5"
                                        stroke="currentColor"
                                        stroke-width="1.5"
                                        stroke-linecap="square"
                                      />
                                    </svg>
                                  </div>
                                  <span class="todo-content" :class="{ 'shimmer-text': todo.status === 'in_progress' || todo.status === 'running' }">{{ todo.content }}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <!-- Show side-by-side diff for edit tools -->
                        <div v-if="part.tool === 'edit' && hasDiffData(part)" class="tool-diff">
                          <SideBySideDiff
                            :before="getBeforeContent(part)"
                            :after="getAfterContent(part)"
                            :filename="getDiffFilename(part)"
                          />
                        </div>
                        
                        <!-- Show side-by-side diff for write tools (if they have before/after) -->
                        <div v-else-if="part.tool === 'write' && hasDiffData(part)" class="tool-diff">
                          <SideBySideDiff
                            :before="getBeforeContent(part)"
                            :after="getAfterContent(part)"
                            :filename="getDiffFilename(part)"
                          />
                        </div>
                        
                        <!-- Collapsible technical details -->
                        <div
                          v-if="hasTechnicalDetails(part) && expandedToolDetails.has(part.callID || part.id)"
                          class="tool-details-content"
                        >
                          <div v-if="part.state?.input && shouldShowInput(part)" class="tool-input">
                            <pre>{{ JSON.stringify(part.state.input, null, 2) }}</pre>
                          </div>
                          <div v-if="part.state?.output && shouldShowOutput(part)" class="tool-output">
                            <pre>{{ part.state.output }}</pre>
                          </div>
                        </div>
                        
                        <!-- Non-collapsible output for certain tools -->
                        <div v-if="part.state?.output && !shouldCollapseOutput(part)" class="tool-output">
                          <pre>{{ part.state.output }}</pre>
                        </div>
                        
                        <div v-if="part.state?.error" class="tool-error">
                          Error: {{ part.state.error }}
                        </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- File/Diff Part -->
                    <div v-else-if="part.type === 'file'" class="message-part file-part">
                      <div class="file-info">
                        <span class="file-name">{{ part.filename || part.name }}</span>
                      </div>
                    </div>
                  </template>
                </div>
                
                    <!-- Status indicator for incomplete messages -->
                    <div v-if="!assistantMsg.info.finish" class="status-indicator">
                      <RefreshCw :size="16" class="status-spinner" />
                      <span class="status-text shimmer-text">{{ getStatusText(turn, assistantMsg) }}</span>
                    </div>
                
                <!-- Error display -->
                <div v-if="assistantMsg.info.error" class="message-error">
                  <div class="error-content">
                    {{ assistantMsg.info.error?.message || 'An error occurred' }}
                  </div>
                </div>
              </div>
            </template>
          </div>
          
          <!-- Loading indicator for turn in progress -->
          <div v-else-if="turnIndex === turns.length - 1 && loading" class="turn-loading">
            <div class="status-indicator">
              <RefreshCw :size="16" class="status-spinner" />
              <span class="status-text shimmer-text">{{ getDefaultStatusText() }}</span>
            </div>
          </div>
        </div>
      </template>
      
      <!-- Agent Status Indicator -->
      <div v-if="showAgentStatus" class="agent-status-indicator">
        <RefreshCw :size="16" class="status-spinner" />
        <span class="status-text shimmer-text">{{ agentStatusMessage }}</span>
      </div>
    </div>

    <!-- Input Section -->
    <div class="chat-input-container">
      <div class="input-wrapper">
        <textarea
          v-model="inputText"
          @keydown="handleKeyDown"
          @input="handleInput"
          @focus="handleInputFocus"
          :disabled="loading"
          :placeholder="showTranscribingPlaceholder ? 'Listening intently' : 'Type or speak your message...'"
          class="chat-input"
          :class="{ 'transcribing-placeholder': showTranscribingPlaceholder }"
          rows="1"
          ref="inputRef"
        ></textarea>
        <div v-if="showTranscribingPlaceholder" class="transcribing-overlay">
          <Loader2 :size="12" class="transcribing-spinner" />
          <span class="transcribing-text shimmer-text">Listening intently</span>
        </div>
      </div>
      <div class="input-actions">
        <div class="agent-selector-wrapper">
          <CustomDropdown
            v-model="selectedAgent"
            :options="agentOptions"
            placeholder="Agent"
            option-label="name"
            option-value="id"
            class="agent-dropdown"
          />
        </div>
        <div class="action-buttons">
          <button
            v-if="!autoRecordMode && !isRecording"
            class="voice-button"
            @click="toggleRecording"
            :disabled="loading"
            title="Start voice recording"
          >
            <Mic :size="18" fill="currentColor" />
          </button>
        <button
          v-if="isRecording"
          class="stop-button"
          @click="stopRecording"
          :disabled="loading"
          title="Stop recording"
        >
            <Square :size="10" fill="currentColor" />
        </button>
        <button
          v-if="isRecording && inputText.trim()"
          class="send-button"
          @click="sendMessage"
          :disabled="loading || !inputText.trim()"
          title="Send message"
        >
            <ArrowUp :size="14" fill="currentColor" />
        </button>
        <button
          v-else-if="isTranscribingFinal || isTranscribing.value"
          class="loading-button"
          disabled
          title="Transcribing..."
        >
            <Loader2 :size="14" class="spinner" fill="currentColor" />
        </button>
        <template v-else-if="inputText.trim()">
          <button
            class="clear-input-button"
            @click="clearInput"
            :disabled="loading"
            title="Clear input"
          >
              <Eraser :size="16" />
          </button>
          <button
            class="send-button"
            @click="sendMessage"
            :disabled="loading || !inputText.trim()"
            title="Send message"
          >
              <ArrowUp :size="14" fill="currentColor" />
          </button>
        </template>
        <button
          v-else-if="!autoRecordMode"
          class="voice-button voice-button-inline"
          @click="startRecordingAtCursor"
          :disabled="loading"
          title="Start recording"
        >
          <Mic :size="16" />
        </button>
        </div>
      </div>
      <div v-if="error" class="error-message">{{ error }}</div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { marked } from 'marked';
import {
  Mic, Square, Send, Loader2, Eraser, Brain, RefreshCw, ChevronDown, FileText, CheckSquare,
  Search, FileEdit, FilePlus, FolderOpen, Globe, Terminal, ListTodo, ArrowUp, ChevronUp,
  Hammer, ClipboardList, Building, Wrench, History
} from 'lucide-vue-next';
import { useChatStore } from '@/stores/chat';
import { useProjectStore } from '@/stores/project';
import { useSettingsStore } from '@/stores/settings';
import { useSessionStore } from '@/stores/session';
import TaskControlPanel from './TaskControlPanel.vue';
import WorkflowSummaryCard from './WorkflowSummaryCard.vue';
import SideBySideDiff from './SideBySideDiff.vue';
import CustomDropdown from './CustomDropdown.vue';
import SessionTabs from './SessionTabs.vue';
import SessionHistory from './SessionHistory.vue';

const chatStore = useChatStore();
const projectStore = useProjectStore();
const settingsStore = useSettingsStore();
const sessionStore = useSessionStore();

const messages = computed(() => chatStore.messages); // Legacy support
const turns = computed(() => chatStore.turns); // New turn-based structure
const loading = computed(() => chatStore.loading);
const error = computed(() => chatStore.error);
const autoRecordMode = computed(() => settingsStore.autoRecordMode);
const whisperModelId = computed(() => settingsStore.whisperModelId);
const workflowState = computed(() => chatStore.workflowState);

// View toggle: chat or history
const showHistory = ref(false);
const headerTabsRef = ref(null);
const mercuryTabRef = ref(null);
const historyTabRef = ref(null);

// Computed style for sliding background
const backgroundStyle = computed(() => {
  if (!mercuryTabRef.value || !historyTabRef.value || !headerTabsRef.value) {
    return {
      width: '0px',
      transform: 'translateX(0)'
    };
  }

  const activeTab = showHistory.value ? historyTabRef.value : mercuryTabRef.value;
  const tabsContainer = headerTabsRef.value;
  
  const activeTabRect = activeTab.getBoundingClientRect();
  const containerRect = tabsContainer.getBoundingClientRect();
  
  const width = activeTabRect.width;
  const leftOffset = activeTabRect.left - containerRect.left;
  
  return {
    width: `${width}px`,
    transform: `translateX(${leftOffset}px)`
  };
});

// Watch for tab changes to update background position
watch(showHistory, () => {
  // Force a re-render by triggering a style recalculation
  nextTick(() => {
    // The computed property will automatically update
  });
});

// Agent selection - initialize with default agent from settings
const selectedAgent = ref(settingsStore.defaultAgent);

const getAgentIcon = (agentId) => {
  const icons = {
    build: Hammer,
    explore: Search,
    plan: ClipboardList,
    architect: Building,
    fix: Wrench
  };
  return icons[agentId] || Hammer;
};

const agentOptions = [
  { id: 'build', name: 'Build', icon: Hammer },
  { id: 'explore', name: 'Explore', icon: Search },
  { id: 'plan', name: 'Plan', icon: ClipboardList },
  { id: 'architect', name: 'Architect', icon: Building },
  { id: 'fix', name: 'Fix', icon: Wrench }
];

// Watch for changes to default agent in settings
watch(() => settingsStore.defaultAgent, (newAgent) => {
  selectedAgent.value = newAgent;
});

const showAgentStatus = computed(() => {
  if (!loading.value) return false;
  
  // Check last assistant message for statusUpdate
  const lastAssistantMessage = messages.value.filter(m => m.role === 'assistant').pop();
  if (lastAssistantMessage?.statusUpdate) {
    const stage = lastAssistantMessage.statusUpdate.stage;
    return stage && stage !== 'completed' && stage !== 'error';
  }
  
  // Fallback to workflowState
  if (!workflowState.value) return false;
  const stage = workflowState.value.stage;
  return stage && stage !== 'completed' && stage !== 'error';
});

const agentStatusMessage = computed(() => {
  // Check last assistant message for statusUpdate first
  const lastAssistantMessage = messages.value.filter(m => m.role === 'assistant').pop();
  if (lastAssistantMessage?.statusUpdate) {
    return lastAssistantMessage.statusUpdate.message || getDefaultStatusMessage(lastAssistantMessage.statusUpdate.stage);
  }
  
  // Fallback to workflowState
  if (!workflowState.value) return 'Thinking...';
  return workflowState.value.message || getDefaultStatusMessage(workflowState.value.stage);
});

const getDefaultStatusMessage = (stage) => {
  const messages = {
    'exploring': 'Exploring codebase...',
    'planning': 'Planning next steps...',
    'executing': 'Executing plan...',
    'validating': 'Validating changes...'
  };
  return messages[stage] || 'Thinking...';
};

const inputText = ref('');
const inputRef = ref(null);
const messagesContainer = ref(null);
const expandedToolDetails = ref(new Set());
const isRecording = ref(false);
const hasManuallyStopped = ref(false);
const isTranscribingFinal = ref(false);
const isTranscribing = ref(false);
const hasReceivedTranscription = ref(false);
let mediaRecorder = null;
let audioChunks = [];
let stream = null;
let transcriptionInterval = null;
let accumulatedText = '';
let isTranscribingInternal = false;
let streamingTimeout = null;
let audioContext = null;

const handleKeyDown = async (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
    return;
  }
  
  if (e.key === 'Backspace' && !inputText.value.trim() && autoRecordMode.value && 
      !isRecording.value && !loading.value && !hasManuallyStopped.value && whisperModelId.value) {
    e.preventDefault();
    await startRecording();
    return;
  }
  
  if (isRecording.value && !hasReceivedTranscription.value && 
      !e.ctrlKey && !e.metaKey && !e.altKey && 
      e.key.length === 1) {
    console.log('User started typing while recording, stopping recording and canceling transcription');
    stopRecording(true);
    return;
  }
  
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

const showTranscribingPlaceholder = computed(() => {
  return isRecording.value && !inputText.value.trim() && !hasReceivedTranscription.value;
});

const handleInput = (e) => {
  if (isRecording.value && !hasReceivedTranscription.value && inputText.value.trim()) {
    console.log('User started typing while recording, stopping recording and canceling transcription');
    stopRecording(true);
  }
  
  if (!inputText.value.trim() && autoRecordMode.value && !isRecording.value && !loading.value) {
    hasManuallyStopped.value = false;
    nextTick(async () => {
      if (!inputText.value.trim() && whisperModelId.value) {
        console.log('Input cleared, restarting recording in auto record mode');
        await startRecording();
      }
    });
  }
  
  resizeTextarea();
};

const clearInput = async () => {
  inputText.value = '';
  accumulatedText = '';
  hasReceivedTranscription.value = false;
  hasManuallyStopped.value = true; // Prevent auto-recording after clearing
  
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = '24px';
      // Unfocus the input to prevent auto-recording
      inputRef.value.blur();
    }
  });
};

const startRecordingAtCursor = async () => {
  await startRecording();
};

const streamTextToInput = (newText, isFinal = false) => {
  return new Promise((resolve) => {
    if (streamingTimeout) {
      clearTimeout(streamingTimeout);
      streamingTimeout = null;
    }
    
    const currentText = inputText.value;
    
    if (newText === currentText) {
      resolve();
      return;
    }
    
    if (newText.length < currentText.length && currentText.startsWith(newText)) {
      inputText.value = newText;
      resizeTextarea();
      resolve();
      return;
    }
    
    let commonPrefixEnd = 0;
    const minLength = Math.min(currentText.length, newText.length);
    for (let i = 0; i < minLength; i++) {
      if (currentText[i] === newText[i]) {
        commonPrefixEnd = i + 1;
      } else {
        break;
      }
    }
    
    if (newText.startsWith(currentText)) {
      const textToStream = newText.substring(currentText.length);
      if (textToStream.length > 0) {
        streamRemainder(textToStream, currentText.length, isFinal, resolve);
      } else {
        resolve();
      }
      return;
    }
    
    const commonPrefix = newText.substring(0, commonPrefixEnd);
    const remainder = newText.substring(commonPrefixEnd);
    
    inputText.value = commonPrefix;
    resizeTextarea();
    
    if (remainder.length > 0) {
      streamRemainder(remainder, commonPrefixEnd, isFinal, resolve);
    } else {
      inputText.value = newText;
      resizeTextarea();
      resolve();
    }
  });
};

const streamRemainder = (textToStream, startPosition, isFinal = false, onComplete = null) => {
  let streamedLength = 0;
  
  const streamNext = () => {
    if (streamedLength < textToStream.length) {
      // Smaller chunk size
      const chunkSize = 5;
      const nextChunk = textToStream.substring(streamedLength, streamedLength + chunkSize);
      streamedLength += nextChunk.length;
      
      const baseText = inputText.value.substring(0, startPosition);
      inputText.value = baseText + textToStream.substring(0, streamedLength);
      resizeTextarea();
      
      // Slightly increased delay
      streamingTimeout = setTimeout(streamNext, isFinal ? 15 : 20);
    } else {
      streamingTimeout = null;
      if (onComplete) {
        onComplete();
      }
    }
  };
  
  streamNext();
};

const resizeTextarea = () => {
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto';
      // Only expand if content requires more than one line
      const newHeight = Math.max(24, Math.min(inputRef.value.scrollHeight, 200));
      inputRef.value.style.height = newHeight + 'px';
    }
  });
};

const handleInputFocus = async () => {
  // Reset manual stop flag when user focuses the input - they're indicating they want to use it again
  hasManuallyStopped.value = false;
  
  if (autoRecordMode.value && !isRecording.value && !loading.value && !inputText.value.trim()) {
    await nextTick();
    if (whisperModelId.value) {
      await startRecording();
    }
  }
};

const sendMessage = async () => {
  if (!inputText.value.trim() || loading.value) return;
  
  if (isRecording.value) {
    await stopRecording(true);
  }
  
  // Cancel any in-flight transcription
  isTranscribingInternal = false;
  isTranscribing.value = false;
  isTranscribingFinal.value = false;
  
  const text = inputText.value.trim();
  inputText.value = '';
  accumulatedText = '';
  hasReceivedTranscription.value = false;
  hasManuallyStopped.value = false;
  
  resizeTextarea();
  
  const context = {
    projectPath: projectStore.currentProject?.path,
    activeFile: projectStore.activeFile,
    agent: selectedAgent.value
  };
  
  await chatStore.sendMessageStream(text, context);
  scrollToBottom();
  
  // Unfocus the input and prevent auto-recording
  hasManuallyStopped.value = true;
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.blur();
    }
  });
};


// Helper functions for turn-based display
const getUserMessageText = (userMessage) => {
  if (!userMessage?.parts) return ''
  // Extract text from user message parts
  return userMessage.parts
    .filter(p => p.type === 'text' && !p.synthetic)
    .map(p => p.text)
    .join('')
}

const getToolStatusClass = (status) => {
  const statusMap = {
    'running': 'status-running',
    'completed': 'status-completed',
    'error': 'status-error'
  }
  return statusMap[status] || 'status-unknown'
}

const getToolStatusText = (status) => {
  const statusMap = {
    'running': 'Running...',
    'completed': 'Completed',
    'error': 'Error'
  }
  return statusMap[status] || status || 'Unknown'
}

/**
 * Get status text based on the last part of the assistant message
 * Similar to OpenCode's MessageProgress component
 */
const getStatusText = (turn, assistantMsg) => {
  if (!assistantMsg?.parts || assistantMsg.parts.length === 0) {
    return 'Thinking...'
  }
  
  // Get the last part
  const lastPart = assistantMsg.parts[assistantMsg.parts.length - 1]
  
  if (lastPart.type === 'tool') {
    switch (lastPart.tool) {
      case 'task':
        return 'Delegating work...'
      case 'todowrite':
      case 'todoread':
        return 'Planning next steps...'
      case 'read':
        return 'Gathering context...'
      case 'list':
      case 'grep':
      case 'glob':
        return 'Searching the codebase...'
      case 'webfetch':
        return 'Searching the web...'
      case 'edit':
      case 'write':
        return 'Making edits...'
      case 'bash':
        return 'Running commands...'
      default:
        return 'Working...'
    }
  } else if (lastPart.type === 'reasoning') {
    return 'Thinking...'
  } else if (lastPart.type === 'text') {
    return 'Gathering thoughts...'
  }
  
  return 'Thinking...'
}

/**
 * Get default status text when no parts are available yet
 */
const getDefaultStatusText = () => {
  return 'Thinking...'
}

/**
 * Extract filename from file path
 */
const getFilename = (filePath) => {
  if (!filePath) return ''
  const parts = filePath.split('/')
  return parts[parts.length - 1] || filePath
}

/**
 * Check if tool part has diff data (either in metadata.filediff or in input)
 */
const hasDiffData = (part) => {
  // Check for filediff in metadata
  if (part.metadata?.filediff?.before && part.metadata?.filediff?.after) {
    return true
  }
  // Check for oldString/newString in input
  if (part.state?.input?.oldString && part.state?.input?.newString) {
    return true
  }
  return false
}

/**
 * Get before content from tool part
 */
const getBeforeContent = (part) => {
  // Try metadata.filediff first
  if (part.metadata?.filediff?.before) {
    return part.metadata.filediff.before
  }
  // Fall back to input.oldString
  if (part.state?.input?.oldString) {
    return part.state.input.oldString
  }
  return ''
}

/**
 * Get after content from tool part
 */
const getAfterContent = (part) => {
  // Try metadata.filediff first
  if (part.metadata?.filediff?.after) {
    return part.metadata.filediff.after
  }
  // Fall back to input.newString
  if (part.state?.input?.newString) {
    return part.state.input.newString
  }
  return ''
}

/**
 * Get filename for diff display
 */
const getDiffFilename = (part) => {
  // Try metadata.filediff
  if (part.metadata?.filediff?.file) {
    return getFilename(part.metadata.filediff.file)
  }
  if (part.metadata?.filediff?.path) {
    return getFilename(part.metadata.filediff.path)
  }
  // Fall back to input.filePath
  if (part.state?.input?.filePath) {
    return getFilename(part.state.input.filePath)
  }
  return ''
}

/**
 * Get icon component for tool type
 */
const getToolIcon = (part) => {
  const tool = part.tool
  const iconMap = {
    'list': FolderOpen,
    'read': FileText,
    'edit': FileEdit,
    'write': FilePlus,
    'webfetch': Globe,
    'task': ListTodo,
    'todowrite': CheckSquare,
    'bash': Terminal,
    'grep': Search,
    'glob': Search
  }
  return iconMap[tool] || FileText
}

/**
 * Get user-friendly tool display name (past tense)
 */
const getToolDisplayName = (part) => {
  const tool = part.tool
  const input = part.state?.input || {}
  
  const nameMap = {
    'list': 'Explored',
    'read': 'Read',
    'edit': 'Edit',
    'write': 'Write',
    'webfetch': 'Searched the web',
    'task': 'Task',
    'todowrite': 'To-dos',
    'bash': 'Shell',
    'grep': 'Searched',
    'glob': 'Searched'
  }
  
  let name = nameMap[tool] || tool
  
  // For edit tool, append filename
  if (tool === 'edit' && input.filePath) {
    name += ' ' + getFilename(input.filePath)
  }
  
  return name
}

/**
 * Get tool subtitle (contextual information) - inline with title
 */
const getToolSubtitle = (part) => {
  const tool = part.tool
  const input = part.state?.input || {}
  
  if (tool === 'list') {
    const path = input.path || '/'
    if (path === '/' || path === '') {
      return 'the codebase'
    }
    // Extract directory name from path
    const parts = path.split('/').filter(p => p)
    return parts.length > 0 ? parts[parts.length - 1] : 'the codebase'
  }
  
  if (tool === 'read' && input.filePath) {
    return getFilename(input.filePath)
  }
  
  if (tool === 'webfetch' && input.url) {
    try {
      const url = new URL(input.url)
      return url.hostname
    } catch {
      return input.url
    }
  }
  
  if (tool === 'task' && input.description) {
    return input.description
  }
  
  // Don't show subtitle for edit (filename is in title) or todowrite (count is shown separately)
  if (tool === 'edit' || tool === 'todowrite') {
    return null
  }
  
  return null
}

/**
 * Get tool count (for right side display)
 */
const getToolCount = (part) => {
  const tool = part.tool
  const input = part.state?.input || {}
  
  if (tool === 'todowrite' && input.todos) {
    // Count files to edit
    const editTodos = input.todos.filter(t => 
      t.content && (
        t.content.toLowerCase().includes('edit') ||
        t.content.toLowerCase().includes('file') ||
        t.content.toLowerCase().includes('update')
      )
    )
    if (editTodos.length > 0) {
      return editTodos.length
    }
    // Otherwise show completion count
    const completed = input.todos.filter(t => t.status === 'completed').length
    const total = input.todos.length
    return `${completed}/${total}`
  }
  
  return null
}

/**
 * Get icon type for tool count
 */
const getToolCountIcon = (part) => {
  const tool = part.tool
  if (tool === 'todowrite') {
    const input = part.state?.input || {}
    const editTodos = input.todos?.filter(t => 
      t.content && (
        t.content.toLowerCase().includes('edit') ||
        t.content.toLowerCase().includes('file') ||
        t.content.toLowerCase().includes('update')
      )
    )
    if (editTodos && editTodos.length > 0) {
      return 'file'
    }
    return 'check'
  }
  return null
}


/**
 * Check if tool has technical details to show
 */
const hasTechnicalDetails = (part) => {
  // Don't show technical details for tools that have special displays
  if (part.tool === 'todowrite' || part.tool === 'task') {
    return false
  }
  
  // Show if there's input or output that should be collapsible
  return (part.state?.input && shouldShowInput(part)) || 
         (part.state?.output && shouldShowOutput(part) && shouldCollapseOutput(part))
}

/**
 * Check if input should be shown
 */
const shouldShowInput = (part) => {
  // Don't show input for edit/write if they have diff
  if ((part.tool === 'edit' || part.tool === 'write') && hasDiffData(part)) {
    return false
  }
  return true
}

/**
 * Check if output should be shown
 */
const shouldShowOutput = (part) => {
  // Don't show output for edit/write (they use diff instead)
  if (part.tool === 'edit' || part.tool === 'write') {
    return false
  }
  return true
}

/**
 * Check if output should be collapsible
 */
const shouldCollapseOutput = (part) => {
  // Most tools should have collapsible output
  // Except for tools that have special displays
  return true
}

/**
 * Toggle tool details accordion
 */
const toggleToolDetails = (partId) => {
  if (expandedToolDetails.value.has(partId)) {
    expandedToolDetails.value.delete(partId)
  } else {
    expandedToolDetails.value.add(partId)
  }
}

/**
 * Check if tool is ready to be displayed (has content or error)
 */
const isToolReady = (part) => {
  // Always show if there's an error
  if (part.state?.status === 'error' || part.state?.error) {
    return true
  }
  
  // For edit/write tools, wait for diff data
  if (part.tool === 'edit' || part.tool === 'write') {
    return hasDiffData(part)
  }
  
  // For todowrite, wait for todos
  if (part.tool === 'todowrite') {
    return !!part.state?.input?.todos
  }
  
  // For task, wait for summary
  if (part.tool === 'task') {
    return !!part.metadata?.summary
  }
  
  // For other tools, show if they have output or are completed
  if (part.state?.output || part.state?.status === 'completed') {
    return true
  }
  
  // Don't show if still running without content
  return false
}

/**
 * Check if tool part has visible content (excluding technical details)
 */
const hasVisibleContent = (part) => {
  // Check for todos
  if (part.tool === 'todowrite' && part.state?.input?.todos) {
    return true
  }
  
  // Check for task list
  if (part.tool === 'task' && part.metadata?.summary) {
    return true
  }
  
  // Check for diff
  if ((part.tool === 'edit' || part.tool === 'write') && hasDiffData(part)) {
    return true
  }
  
  // Check for non-collapsible output
  if (part.state?.output && !shouldCollapseOutput(part)) {
    return true
  }
  
  // Check for expanded technical details
  if (hasTechnicalDetails(part) && expandedToolDetails.value.has(part.callID || part.id)) {
    return true
  }
  
  return false
}

const formatMessage = (content) => {
  if (!content) return '';
  
  try {
    // Configure marked options
    marked.setOptions({
      breaks: true, // Convert \n to <br>
      gfm: true, // GitHub Flavored Markdown
    });
    
    // Parse markdown to HTML
    let html = marked.parse(content);
    
    // Add color previews for color codes
    html = addColorPreviews(html);
    
    return html;
  } catch (error) {
    console.error('Markdown parsing error:', error);
    // Fallback to basic formatting if parsing fails
  return content
    .replace(/\n/g, '<br>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
  }
};

const isValidColor = (color) => {
  // Check if it's a valid CSS color
  const s = new Option().style;
  s.color = color;
  return s.color !== '';
};

const addColorPreviews = (html) => {
  // Match hex colors (#rgb, #rrggbb, #rrggbbaa) - but not inside code blocks
  const hexPattern = /#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b/g;
  
  // Match rgb/rgba colors
  const rgbPattern = /rgba?\([^)]+\)/g;
  
  // Match hsl/hsla colors
  const hslPattern = /hsla?\([^)]+\)/g;
  
  // Match common color names (basic set)
  const colorNames = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta', 'lime', 'navy', 'teal', 'olive', 'maroon', 'silver', 'gold'];
  const colorNamePattern = new RegExp(`\\b(${colorNames.join('|')})\\b`, 'gi');
  
  // Helper to determine text color (light or dark) based on background
  const getContrastColor = (color) => {
    // Simple contrast calculation - if color is dark, use white text, else black
    const hex = color.replace('#', '');
    if (hex.length === 3) {
      const r = parseInt(hex[0] + hex[0], 16);
      const g = parseInt(hex[1] + hex[1], 16);
      const b = parseInt(hex[2] + hex[2], 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness < 128 ? '#ffffff' : '#000000';
    } else if (hex.length === 6 || hex.length === 8) {
      const r = parseInt(hex.substring(0, 2), 16);
      const g = parseInt(hex.substring(2, 4), 16);
      const b = parseInt(hex.substring(4, 6), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness < 128 ? '#ffffff' : '#000000';
    }
    // For named colors, use a simple heuristic
    const darkColors = ['black', 'navy', 'maroon', 'purple', 'olive'];
    return darkColors.includes(color.toLowerCase()) ? '#ffffff' : '#000000';
  };
  
  // Process code blocks separately - replace colors inside code blocks
  html = html.replace(/<code>([^<]*)<\/code>/g, (match, codeContent) => {
    let processed = codeContent;
    
    // Replace hex colors in code
    processed = processed.replace(hexPattern, (colorMatch) => {
      if (isValidColor(colorMatch)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${colorMatch}"></span>${colorMatch}</span>`;
      }
      return colorMatch;
    });
    
    // Replace rgb/rgba in code
    processed = processed.replace(rgbPattern, (colorMatch) => {
      if (isValidColor(colorMatch)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${colorMatch}"></span>${colorMatch}</span>`;
      }
      return colorMatch;
    });
    
    // Replace hsl/hsla in code
    processed = processed.replace(hslPattern, (colorMatch) => {
      if (isValidColor(colorMatch)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${colorMatch}"></span>${colorMatch}</span>`;
      }
      return colorMatch;
    });
    
    // Replace color names in code
    processed = processed.replace(colorNamePattern, (colorName) => {
      if (isValidColor(colorName)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${colorName}"></span>${colorName}</span>`;
      }
      return colorName;
    });
    
    return `<code>${processed}</code>`;
  });
  
  // Replace colors outside of code blocks (in regular text)
  const parts = html.split(/(<code>[\s\S]*?<\/code>)/g);
  for (let i = 0; i < parts.length; i += 2) {
    // Only process parts that are NOT code blocks
    let text = parts[i];
    
    // Replace hex colors
    text = text.replace(hexPattern, (match) => {
      if (isValidColor(match)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${match}"></span>${match}</span>`;
      }
      return match;
    });
    
    // Replace rgb/rgba
    text = text.replace(rgbPattern, (match) => {
      if (isValidColor(match)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${match}"></span>${match}</span>`;
      }
      return match;
    });
    
    // Replace hsl/hsla
    text = text.replace(hslPattern, (match) => {
      if (isValidColor(match)) {
        return `<span class="color-code"><span class="color-swatch" style="background-color: ${match}"></span>${match}</span>`;
      }
      return match;
    });
    
    parts[i] = text;
  }
  
  return parts.join('');
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

// Watch for session changes and reload messages (mimics OpenCode's createEffect pattern)
// OpenCode uses: createEffect(() => { if (!params.id) return; sync.session.sync(params.id) })
watch(
  () => sessionStore.activeSessionId,
  async (newSessionId, oldSessionId) => {
    if (!newSessionId) return // Similar to OpenCode's early return
    
    if (newSessionId !== oldSessionId) {
      console.log('[ChatPanel] Session changed from', oldSessionId, 'to', newSessionId)
      
      // Check if chatStore and required methods are available
      if (!chatStore || !chatStore.opencode || typeof chatStore.loadMessages !== 'function') {
        console.warn('[ChatPanel] ChatStore not ready, skipping message load')
        return
      }
      
      // Note: We don't need to wait for opencode.sessionId to be updated
      // because loadMessages accepts a sessionId parameter and will use that directly
      // The sessionId in opencode is mainly for sending new messages, not for loading old ones
      
      // Mimic OpenCode's sync.session.sync(sessionID) pattern
      // Load messages for the specific session ID (like OpenCode does)
      console.log('[ChatPanel] Syncing messages for session:', newSessionId)
      try {
        // Pass the sessionId directly to loadMessages (like OpenCode's sync function)
        await chatStore.loadMessages(newSessionId)
        
        // Verify messages were loaded
        const messageMap = chatStore.messageMap
        if (messageMap) {
          const loadedMessages = Array.from(messageMap.values())
            .filter(msg => msg.info?.sessionID === newSessionId)
          console.log('[ChatPanel] Synced', loadedMessages.length, 'messages for session', newSessionId)
          console.log('[ChatPanel] Total messages in map:', messageMap.size)
          if (chatStore.turns && chatStore.turns.value) {
            console.log('[ChatPanel] Turns computed:', chatStore.turns.value.length)
          }
        } else {
          console.warn('[ChatPanel] messageMap not available')
        }
      } catch (err) {
        console.error('[ChatPanel] Error syncing messages:', err)
      }
      
      // Scroll to bottom after messages load
      await nextTick()
      scrollToBottom()
    }
  },
  { immediate: true } // Run immediately like OpenCode's createEffect
)

// Load messages on initial mount if there's an active session
onMounted(async () => {
  if (sessionStore.activeSessionId && chatStore?.loadMessages) {
    await nextTick()
    try {
      await chatStore.loadMessages()
      await nextTick()
      scrollToBottom()
    } catch (err) {
      console.error('[ChatPanel] Error loading initial messages:', err)
    }
  }
})

// Watch for new turns or updates to scroll to bottom
watch(() => turns.value.length, () => {
  scrollToBottom();
});

watch(() => {
  // Watch for updates to the last turn's assistant messages
  if (turns.value.length > 0) {
    const lastTurn = turns.value[turns.value.length - 1]
    return lastTurn.assistantMessages.length
  }
  return 0
}, () => {
  scrollToBottom();
});

// Also watch messages for backward compatibility
watch(() => messages.value.length, () => {
  scrollToBottom();
});

const toggleRecording = async () => {
  hasManuallyStopped.value = false;
  if (!whisperModelId.value) {
    return;
  }
  await startRecording();
};

const startRecording = async () => {
  try {
    if (!whisperModelId.value) {
      console.error('Whisper model not configured');
      alert('Please select a Whisper model in Settings > Audio');
      return;
    }
    
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    const options = { mimeType: 'audio/webm;codecs=opus' };
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
      delete options.mimeType;
    }
    
    mediaRecorder = new MediaRecorder(stream, options);
    audioChunks = [];
    accumulatedText = '';
    inputText.value = '';
    isTranscribingFinal.value = false;
    hasReceivedTranscription.value = false;
    
    nextTick(() => {
      if (inputRef.value) {
        inputRef.value.style.height = 'auto';
        inputRef.value.style.height = inputRef.value.scrollHeight + 'px';
      }
    });
    
    console.log('Starting recording with Whisper model:', whisperModelId.value);
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
        console.log('Audio chunk received:', event.data.size, 'bytes');
      }
    };
    
    mediaRecorder.onstop = async () => {
      console.log('Recording stopped, processing final chunk. Total chunks:', audioChunks.length);
      isRecording.value = false;
      isTranscribingFinal.value = true;
      isTranscribing.value = true;
      await new Promise(resolve => setTimeout(resolve, 300));
      if (audioChunks.length > 0) {
        console.log('Processing final audio chunk(s), total size:', audioChunks.reduce((sum, chunk) => sum + chunk.size, 0), 'bytes');
        await processChunk(true);
      } else {
        console.log('No audio chunks available to process');
        isTranscribingFinal.value = false;
        isTranscribing.value = false;
      }
      hasManuallyStopped.value = false;
    };
    
    const CHUNK_DURATION_MS = 200;
    
    mediaRecorder.start(CHUNK_DURATION_MS);
    isRecording.value = true;
    
    transcriptionInterval = setInterval(async () => {
      if (isRecording.value && audioChunks.length > 0 && !isTranscribingInternal) {
        console.log('Processing chunk during recording. Chunks:', audioChunks.length);
        await processChunk(false);
      }
    }, CHUNK_DURATION_MS);
    
    setTimeout(async () => {
      if (isRecording.value && audioChunks.length > 0 && !isTranscribingInternal) {
        console.log('Processing first chunk. Chunks:', audioChunks.length);
        await processChunk(false);
      }
    }, 300);
  } catch (error) {
    console.error('Error accessing microphone:', error);
    isRecording.value = false;
  }
};

const stopRecording = async (cancelTranscription = false) => {
  if (transcriptionInterval) {
    clearInterval(transcriptionInterval);
    transcriptionInterval = null;
  }
  
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    if (cancelTranscription) {
      const originalOnStop = mediaRecorder.onstop;
      mediaRecorder.onstop = null;
      mediaRecorder.stop();
      setTimeout(() => {
        mediaRecorder.onstop = originalOnStop;
      }, 100);
    } else {
      console.log('Stopping recording, requesting final data. Current chunks:', audioChunks.length);
      mediaRecorder.requestData();
      await new Promise(resolve => setTimeout(resolve, 100));
      mediaRecorder.stop();
    }
    isRecording.value = false;
    if (autoRecordMode.value && hasReceivedTranscription.value) {
      hasManuallyStopped.value = true;
    } else if (autoRecordMode.value && !hasReceivedTranscription.value) {
      hasManuallyStopped.value = false;
    }
  }
  
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }
  
  if (cancelTranscription) {
    audioChunks = [];
    isTranscribing.value = false;
    isTranscribingFinal.value = false;
    isTranscribingInternal = false;
  }
};

const hasSpeech = async (audioBlob) => {
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    
    const channelData = audioBuffer.getChannelData(0);
    const length = channelData.length;
    
    if (length === 0) {
      return false;
    }
    
    let sumSquares = 0;
    for (let i = 0; i < length; i++) {
      sumSquares += channelData[i] * channelData[i];
    }
    const rms = Math.sqrt(sumSquares / length);
    
    const speechThreshold = 0.005;
    
    let zeroCrossings = 0;
    for (let i = 1; i < length; i++) {
      if ((channelData[i] >= 0) !== (channelData[i - 1] >= 0)) {
        zeroCrossings++;
      }
    }
    const zcr = zeroCrossings / length;
    
    const hasEnergy = rms > speechThreshold;
    const hasVariation = zcr > 0.01;
    
    console.log(`Speech detection: RMS=${rms.toFixed(6)}, ZCR=${zcr.toFixed(4)}, hasEnergy=${hasEnergy}, hasVariation=${hasVariation}`);
    
    return hasEnergy || hasVariation;
  } catch (error) {
    console.error('Error detecting speech:', error);
    return true;
  }
};

const processChunk = async (isFinal = false) => {
  // Only process transcription if we're currently recording
  if (!isRecording.value && !isFinal) {
    console.log('Ignoring transcription chunk - not currently recording');
    return;
  }
  
  if (audioChunks.length === 0) {
    console.log('No audio chunks to process');
    return;
  }
  
  if (isTranscribingInternal && !isFinal) {
    console.log('Transcription already in progress, skipping...');
    return;
  }
  
  const mimeType = mediaRecorder?.mimeType || 'audio/webm';
  const audioBlob = new Blob([...audioChunks], { type: mimeType });
  
  const minSize = isFinal ? 1000 : 10000;
  if (audioBlob.size < minSize) {
    if (isFinal) {
      console.log(`Processing final audio chunk (${audioBlob.size} bytes) - user stopped early, processing available audio`);
    } else {
      console.warn(`Audio blob smaller than expected (${audioBlob.size} bytes), but processing anyway. Expected minimum: ${minSize} bytes`);
    }
  }
  
  if (!isFinal) {
    const containsSpeech = await hasSpeech(audioBlob);
    if (!containsSpeech) {
      console.log('No speech detected in chunk, skipping transcription');
      return;
    }
  } else {
    const containsSpeech = await hasSpeech(audioBlob);
    if (!containsSpeech) {
      console.log('No speech detected in final chunk, but processing anyway since user stopped recording');
    }
  }
  
  isTranscribingInternal = true;
  isTranscribing.value = true;
  
  try {
    const extension = mimeType.includes('webm') ? 'webm' : 
                     mimeType.includes('ogg') ? 'ogg' : 'wav';
    const filename = `recording.${extension}`;
    
    console.log('Sending audio blob for transcription. Size:', audioBlob.size, 'bytes', isFinal ? '(final)' : '(streaming)');
    
    const formData = new FormData();
    formData.append('file', audioBlob, filename);
    if (whisperModelId.value) {
      formData.append('model_id', whisperModelId.value);
    }
    
    const response = await fetch('http://127.0.0.1:8001/api/whisper/transcribe', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Transcription HTTP error:', response.status, errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Transcription response:', data);
    
    // Check again after fetch completes - recording might have stopped while fetch was in progress
    if (!isRecording.value && !isFinal) {
      console.log('Ignoring transcription result - not currently recording');
      return;
    }
    
    if (data.success && data.text) {
      const newText = data.text.trim();
      console.log('Transcribed text:', newText);
      
      if (!hasReceivedTranscription.value) {
        hasReceivedTranscription.value = true;
      }
      
      await streamTextToInput(newText, isFinal);
      
      if (isFinal) {
        accumulatedText = '';
        isTranscribingFinal.value = false;
        isTranscribing.value = false;
        console.log('Final transcription set:', inputText.value);
      } else {
        accumulatedText = newText;
        console.log('Streaming transcription updated:', inputText.value);
      }
    } else {
      console.error('Transcription failed:', data.error || 'Unknown error', data);
      if (isFinal) {
        isTranscribingFinal.value = false;
        isTranscribing.value = false;
      }
    }
  } catch (error) {
    console.error('Transcription error:', error);
    console.error('Error details:', error.message);
    
    const isConnectionError = error.message.includes('Failed to fetch') || 
                              error.message.includes('ERR_CONNECTION_REFUSED') ||
                              error.message.includes('ERR_EMPTY_RESPONSE');
    
    if (isFinal) {
      console.error('Final transcription failed');
      isTranscribingFinal.value = false;
      isTranscribing.value = false;
      
      if (isConnectionError) {
        console.warn('Backend server appears to be unavailable. Please ensure the backend is running.');
      }
    } else if (isConnectionError) {
      console.warn('Backend connection error during streaming, will retry on next chunk');
    }
  } finally {
    isTranscribingInternal = false;
    if (!isFinal) {
      isTranscribing.value = false;
    }
    if (isFinal) {
      audioChunks = [];
    }
  }
};

onBeforeUnmount(() => {
  if (isRecording.value) {
    stopRecording();
  }
  if (transcriptionInterval) {
    clearInterval(transcriptionInterval);
    transcriptionInterval = null;
  }
  if (streamingTimeout) {
    clearTimeout(streamingTimeout);
    streamingTimeout = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
});
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--sidebar);
  border-radius: var(--radius-xl);
  overflow: hidden;
  padding: 0;
  margin: 0;
}

.chat-header {
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
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.header-session-tabs {
  flex: 1;
  min-width: 0;
  margin-left: var(--space-2);
}

.header-tabs {
  display: flex;
  align-items: center;
  gap: 0;
  position: relative;
  background: var(--accent);
  border-radius: var(--radius-full);
  padding: var(--space-1);
}

.header-tabs-background {
  position: absolute;
  top: var(--space-1);
  left: 0;
  height: calc(100% - var(--space-1) * 2);
  background: var(--background);
  border-radius: var(--radius-full);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.header-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  color: var(--muted-foreground);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s ease;
  white-space: nowrap;
  position: relative;
  z-index: 1;
}

.header-tab:hover {
  color: var(--foreground);
}

.header-tab.active {
  color: var(--foreground);
}

.header-tab .app-logo {
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-tab-label {
  font-weight: 500;
}

.app-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ring);
  flex-shrink: 0;
}

.chat-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--foreground);
  margin: 0;
}


.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) var(--space-4) var(--space-4) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  user-select: text;
  -webkit-user-select: text;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  text-align: center;
}

.empty-state-content {
  max-width: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-6);
}

.empty-state-icon {
  color: var(--primary);
  opacity: 0.6;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.empty-state-title {
  font-size: 21px;
  font-weight: 600;
  color: var(--foreground);
  margin: 0;
}

.empty-state-text {
  font-size: 15px;
  color: var(--muted-foreground);
  line-height: 1.6;
  margin: 0;
}

/* Turn-based structure (OpenCode style) */
.chat-turn {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-4) 0 0;
}

.turn-user-message {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.turn-user-message .message-content {
  flex: 1;
  background: var(--primary);
  color: var(--primary-foreground);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}

.turn-user-message .message-text {
  color: var(--primary-foreground);
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  font-weight: 500;
}

.turn-assistant-response {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: 0;
}

.assistant-message {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: 0;
}

.message-parts {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.message-part {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.text-part {
  margin-top: var(--space-2);
  margin-bottom: var(--space-2);
  margin-left: 2px;
}

.text-part .text-content {
  color: var(--foreground);
  line-height: 1.6;
  word-wrap: break-word;
  padding: 0;
  margin: 0;
  font-size: 13px;
}

/* Markdown styling */
.text-content :deep(h1) {
  margin: var(--space-8) 0 var(--space-5) 0;
  font-weight: 600;
  line-height: 1.3;
  font-size: 1.5em;
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--border);
  color: var(--foreground);
  background: transparent !important;
}

.text-content :deep(h1:first-child) {
  margin-top: 0;
}

/* Ensure H1 content is never grouped */
.text-content :deep(h1 ~ *) {
  background: transparent !important;
}

/* H2 styling (no grouping, just visual styling) */
.text-content :deep(h2) {
  margin: var(--space-6) 0 var(--space-3) 0;
  font-weight: 600;
  line-height: 1.4;
  font-size: 1.3em;
  padding: var(--space-2) var(--space-3);
  padding-left: var(--space-2);
  border-left: 4px solid var(--primary);
  border-radius: var(--radius-md);
  color: var(--foreground) !important;
  background: color-mix(in srgb, var(--muted) 30%, transparent 70%);
}

.text-content :deep(h2 strong) {
  color: var(--foreground) !important;
}

/* Ensure H2 content is never grouped (only H3 groups) */
.text-content :deep(h2 ~ *:not(h3):not(h1)) {
  background: transparent !important;
}


/* H3 styling (no grouping) */
.text-content :deep(h3) {
  margin: var(--space-5) 0 var(--space-3) 0;
  font-weight: 600;
  line-height: 1.4;
  font-size: 1.1em;
  padding: var(--space-2) var(--space-3);
  padding-left: var(--space-2);
  border-left: 2px solid var(--muted-foreground);
  border-radius: var(--radius-md);
  color: var(--foreground) !important;
  background: color-mix(in srgb, var(--muted) 30%, transparent 70%);
}

.text-content :deep(h3 strong) {
  color: var(--foreground) !important;
}

.text-content :deep(h4) {
  margin: var(--space-4) 0 var(--space-2) 0;
  font-weight: 600;
  line-height: 1.4;
  color: var(--foreground) !important;
  padding-left: var(--space-2);
  border-left: 1px solid var(--border);
  opacity: 0.7;
  background: transparent !important;
}

/* Ensure H4 content is never grouped (only H3 groups) */
.text-content :deep(h4 ~ *:not(h3):not(h2):not(h1)) {
  background: transparent !important;
}

/* Override H4 margins when under H3 */
.text-content :deep(h3 ~ h4) {
  margin: 0 !important;
  padding-top: var(--space-2);
  padding-bottom: 0;
}

.text-content :deep(h4 strong) {
  color: var(--foreground) !important;
}

.text-content :deep(h5),
.text-content :deep(h6) {
  margin: var(--space-4) 0 var(--space-2) 0;
  font-weight: 600;
  line-height: 1.4;
  color: var(--foreground) !important;
  padding-left: var(--space-2);
  border-left: 1px solid var(--border);
  opacity: 0.7;
  background: transparent !important;
}

/* Ensure H5 and H6 content is never grouped (only H3 groups) */
.text-content :deep(h5 ~ *:not(h3):not(h2):not(h1):not(h4)),
.text-content :deep(h6 ~ *:not(h3):not(h2):not(h1):not(h4):not(h5)) {
  background: transparent !important;
}

.text-content :deep(h5 strong),
.text-content :deep(h6 strong) {
  color: var(--foreground) !important;
}

.text-content :deep(p) {
  margin: var(--space-3) 0;
  line-height: 1.6;
}

/* Consistent spacing after headings */
.text-content :deep(h1 + *),
.text-content :deep(h2 + *),
.text-content :deep(h3 + *),
.text-content :deep(h4 + *),
.text-content :deep(h5 + *),
.text-content :deep(h6 + *) {
  margin-top: var(--space-3);
}

.text-content :deep(ul),
.text-content :deep(ol) {
  margin: var(--space-4) var(--space-6) var(--space-4) var(--space-8);
  padding-left: var(--space-5);
}

.text-content :deep(li) {
  margin: var(--space-2) 0;
  padding-left: var(--space-2);
  position: relative;
  line-height: 1.6;
}

.text-content :deep(ul) {
  list-style-type: none;
}

.text-content :deep(ul li::before) {
  content: '•';
  color: var(--foreground);
  font-weight: bold;
  font-size: 1.1em;
  position: absolute;
  left: calc(-1 * var(--space-5));
  line-height: 1.6;
  opacity: 0.6;
}

.text-content :deep(ol) {
  list-style-type: none;
  counter-reset: list-counter;
}

.text-content :deep(ol li) {
  counter-increment: list-counter;
  padding-left: var(--space-5);
}

.text-content :deep(ol li::before) {
  content: counter(list-counter) '.';
  color: var(--foreground);
  font-weight: 600;
  position: absolute;
  left: calc(-1 * var(--space-5));
  line-height: 1.6;
  min-width: var(--space-4);
  text-align: right;
  opacity: 0.6;
}

.text-content :deep(ul ul),
.text-content :deep(ol ol),
.text-content :deep(ul ol),
.text-content :deep(ol ul) {
  margin-top: var(--space-2);
  margin-bottom: var(--space-2);
  margin-left: var(--space-4);
  padding-left: var(--space-4);
}

.text-content :deep(code) {
  background: var(--muted);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.9em;
}

.text-content :deep(.color-code) {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  vertical-align: middle;
}

.text-content :deep(.color-swatch) {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  flex-shrink: 0;
  vertical-align: middle;
  margin-bottom: 1px;
}

.text-content :deep(pre) {
  background: var(--muted);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin: var(--space-4) 0;
}

.text-content :deep(pre code) {
  background: transparent;
  padding: 0;
}

.text-content :deep(blockquote) {
  border-left: 3px solid var(--border);
  padding-left: var(--space-3);
  margin: var(--space-4) 0;
  color: var(--muted-foreground);
  font-style: italic;
}

.text-content :deep(a) {
  color: var(--primary);
  text-decoration: underline;
}

.text-content :deep(a:hover) {
  opacity: 0.8;
}

.text-content :deep(strong) {
  font-weight: 600;
  color: var(--primary);
}

.text-content :deep(em) {
  font-style: italic;
}

.text-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: var(--space-6) 0;
}

.text-content :deep(table) {
  border-collapse: collapse;
  margin: var(--space-8) var(--space-6);
  width: calc(100% - var(--space-12));
  max-width: calc(100% - var(--space-12));
}

.text-content :deep(th),
.text-content :deep(td) {
  border: 1px solid var(--border);
  padding: var(--space-3) var(--space-4);
  text-align: left;
}

.text-content :deep(th) {
  background: var(--muted);
  font-weight: 600;
}

.tool-part {
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tool-part.has-content .tool-header {
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.tool-part:not(.has-content) .tool-header {
  border-radius: var(--radius-md);
}

.tool-container {
  display: flex;
  flex-direction: column;
}

.tool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
  gap: var(--space-3);
  background: var(--muted);
  padding: var(--space-2) var(--space-3);
  font-size: 13px;
  transition: background 0.2s ease;
}

.tool-header.clickable:hover {
  background: var(--accent);
}

.tool-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.tool-details-toggle-header {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  pointer-events: none;
}

.tool-details-toggle-header svg {
  transition: transform 0.2s ease;
}

.tool-details-toggle-header .expanded {
  transform: rotate(180deg);
}

.toggle-text {
  font-weight: 500;
  font-size: 13px;
}

.tool-content {
  background: var(--background);
  padding: var(--space-2) var(--space-3);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  max-height: 250px;
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.tool-content::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.tool-title-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  gap: var(--space-2);
}

.tool-name {
  color: var(--foreground);
  font-weight: 500;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.tool-icon {
  flex-shrink: 0;
  color: var(--muted-foreground);
  opacity: 0.8;
}

.tool-subtitle-inline {
  color: var(--muted-foreground);
  font-weight: 400;
  font-size: 13px;
}

.tool-count {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--muted-foreground);
  font-size: 12px;
  font-weight: 400;
}

.tool-status {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.tool-status.status-running {
  background: var(--muted);
  color: var(--muted-foreground);
}

.tool-status.status-completed {
  display: none;
}

.tool-status.status-error {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.tool-input,
.tool-output {
  background: transparent;
  padding: var(--space-2) 0;
  font-family: var(--font-mono);
  font-size: 12px;
  overflow-x: auto;
}

.tool-error {
  color: var(--destructive);
  font-size: 12px;
}

/* Todo list styles */
.tool-todos {
  margin-top: var(--space-2);
}

.todos-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.todo-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  font-size: 13px;
  min-height: 20px;
}

.todo-item:hover {
  background: var(--muted);
}

.todo-item.todo-completed {
  opacity: 1;
}

.custom-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--border);
  background: var(--background);
  transition: all 0.2s ease;
  position: relative;
  margin-top: 2px;
}

.custom-checkbox.checked {
  background: var(--primary);
  border-color: var(--primary);
}

.custom-checkbox .checkmark {
  width: 10px;
  height: 10px;
  color: var(--primary-foreground);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.custom-checkbox.checked .checkmark {
  opacity: 1;
}

.todo-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.todo-spinner .spinner-icon {
  color: var(--primary);
  animation: spin 1s linear infinite;
}

.todo-content {
  flex: 1;
  line-height: 1.5;
  color: var(--foreground);
  transition: all 0.2s ease;
  padding-top: 1px; /* Slight alignment adjustment */
}

.todo-content.shimmer-text {
  background: linear-gradient(
    270deg,
    var(--muted-foreground) 0%,
    var(--muted-foreground) 35%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 42%,
    white 50%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 58%,
    var(--muted-foreground) 65%,
    var(--muted-foreground) 100%
  );
  background-size: 400% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0.7;
  animation: shimmer-sweep-reverse 3.5s linear infinite;
}

.todo-item.todo-completed .todo-content {
  text-decoration: line-through;
  color: var(--muted-foreground);
  opacity: 0.7;
}

/* Task list styles */
.tool-task-list {
  margin-top: var(--space-2);
}

.task-description {
  font-size: 13px;
  font-weight: 500;
  color: var(--foreground);
  margin-bottom: var(--space-2);
}

.task-todos {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.task-item {
  padding: var(--space-1) var(--space-2);
  background: var(--muted);
  border-radius: var(--radius-sm);
}

.task-todos-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* Accordion for technical details */
.tool-details-content {
  width: 100%;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tool-diff {
  margin: calc(-1 * var(--space-2)) calc(-1 * var(--space-3));
  width: calc(100% + 2 * var(--space-3));
}

.tool-file-path {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--muted);
  border-radius: var(--radius-sm);
  margin-top: var(--space-2);
  font-size: var(--text-sm);
}

.file-path-label {
  font-weight: 500;
  color: var(--muted-foreground);
}

.file-path-value {
  font-family: var(--font-mono);
  color: var(--foreground);
}

.file-part {
  background: var(--muted);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.file-name {
  color: var(--foreground);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.message-error {
  background: var(--destructive);
  color: var(--destructive-foreground);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  margin-top: var(--space-2);
}

.error-content {
  font-size: var(--text-sm);
}

.turn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  margin-left: 0;
  margin-bottom: var(--space-4);
}

/* Legacy message styles (for backward compatibility) */
.message {
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.2s ease;
  width: 100%;
}

.message.user {
  align-items: flex-end;
}

.message.assistant {
  align-items: flex-start;
}

.message-content {
  width: 100%;
  word-wrap: break-word;
}

.message.user .message-content {
  background: linear-gradient(135deg, var(--muted) 0%, color-mix(in srgb, var(--muted) 95%, var(--primary) 5%) 100%);
  color: var(--foreground);
  border-radius: var(--radius-xl);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  padding: var(--space-4) var(--space-5);
}

.message.assistant .message-content {
  background: transparent;
  color: var(--foreground);
  padding: var(--space-5) var(--space-6);
}

.message-text {
  line-height: 1.8;
  font-size: 16px;
  user-select: text;
  -webkit-user-select: text;
  color: var(--foreground);
  margin: 0;
}

.message-text :deep(code) {
  background: var(--muted);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 14px;
}

.message-text :deep(strong) {
  font-weight: 600;
}

.message-text :deep(em) {
  font-style: italic;
}

.streaming-indicator {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding-top: var(--space-2);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  margin-bottom: var(--space-4);
  padding-top: var(--space-2);
}

.typing-dot {
  width: var(--space-3);
  height: var(--space-3);
  border-radius: 50%;
  background: var(--muted-foreground);
  animation: typing 1.4s infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(calc(-1 * var(--space-2)));
  }
}

.chat-input-container {
  padding: var(--space-4);
  background: var(--background);
  margin: var(--space-4);
  border-radius: var(--radius-xl);
}

.input-wrapper {
  display: flex;
  gap: var(--space-2);
  align-items: flex-end;
  position: relative;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-2);
  gap: var(--space-2);
}

.agent-selector-wrapper {
  display: flex;
  justify-content: flex-start;
}

.action-buttons {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin-left: auto;
}

.agent-selector-wrapper :deep(.custom-dropdown) {
  width: auto;
  min-width: auto;
}

.agent-selector-wrapper :deep(.dropdown-menu) {
  width: max-content;
  min-width: max-content;
  left: 0;
  right: auto;
}

.agent-selector-wrapper :deep(.custom-dropdown) {
  font-size: 11px;
}

.agent-selector-wrapper :deep(.dropdown-trigger) {
  padding: 0 var(--space-2);
  font-size: 11px;
  height: 24px;
  min-height: 24px;
  width: auto;
  min-width: auto;
  background: var(--muted);
  border: none;
  border-radius: var(--radius-full);
  color: var(--muted-foreground);
  white-space: nowrap;
}

.agent-selector-wrapper :deep(.dropdown-trigger:hover) {
  background: var(--accent);
  color: var(--foreground);
}

.agent-selector-wrapper :deep(.custom-dropdown.is-open .dropdown-trigger) {
  border: none;
  outline: none;
}

.agent-selector-wrapper :deep(.dropdown-value) {
  font-size: 11px;
  color: var(--foreground);
  line-height: 1.2;
}

.agent-selector-wrapper :deep(.dropdown-arrow) {
  width: 10px;
  height: 10px;
}

.voice-button {
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--muted-foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.voice-button:hover:not(:disabled) {
  color: var(--foreground);
}

.voice-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.voice-button-inline {
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  padding: 0;
}

.stop-button {
  width: 20px;
  height: 20px;
  min-width: 20px;
  min-height: 20px;
  padding: 0;
  background: var(--primary);
  border: none;
  border-radius: var(--radius-full);
  color: var(--primary-foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.stop-button:hover:not(:disabled) {
  background: var(--primary-hover);
  color: var(--primary-foreground);
}

.stop-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-button {
  width: 20px;
  height: 20px;
  min-width: 20px;
  min-height: 20px;
  padding: 0;
  background: var(--primary);
  border: none;
  border-radius: var(--radius-full);
  color: var(--primary-foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-button:hover:not(:disabled) {
  background: var(--primary-hover);
  color: var(--primary-foreground);
}

.send-button:disabled {
  color: var(--muted-foreground);
  opacity: 0.5;
  cursor: not-allowed;
}

.clear-input-button {
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--muted-foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.clear-input-button:hover:not(:disabled) {
  color: var(--foreground);
}

.clear-input-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-button {
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--muted-foreground);
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.loading-button .spinner {
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

.chat-input {
  flex: 1;
  padding: 0;
  margin-bottom: 2px;
  background: var(--background);
  border: none;
  border-radius: var(--radius-lg);
  color: var(--foreground);
  font-size: 13px;
  font-family: inherit;
  resize: none;
  height: 24px;
  min-height: 24px;
  max-height: 200px;
  overflow-y: auto;
  box-sizing: border-box;
  line-height: 1.5;
}

.chat-input.transcribing-placeholder {
  color: transparent;
}

.chat-input.transcribing-placeholder::placeholder {
  color: transparent;
}

.transcribing-overlay {
  position: absolute;
  left: 0;
  top: -2px;
  pointer-events: none;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 24px;
}

.transcribing-spinner {
  color: var(--muted-foreground);
  opacity: 0.7;
  animation: spin 1s linear infinite;
}

.transcribing-text {
  font-size: 13px;
  font-family: inherit;
  line-height: 1.5;
}

.transcribing-text.shimmer-text {
  background: linear-gradient(
    270deg,
    var(--muted-foreground) 0%,
    var(--muted-foreground) 35%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 42%,
    white 50%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 58%,
    var(--muted-foreground) 65%,
    var(--muted-foreground) 100%
  );
  background-size: 400% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0.7;
  animation: shimmer-sweep-reverse 3.5s linear infinite;
}

@keyframes shimmer-sweep {
  0% {
    background-position: -100% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes shimmer-sweep-reverse {
  0% {
    background-position: 400% 0;
  }
  100% {
    background-position: -100% 0;
  }
}

.chat-input:focus {
  outline: none;
  border: none;
}

.chat-input::-webkit-scrollbar {
  display: none;
}

.chat-input {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.chat-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: var(--space-4);
  padding: var(--space-4);
  background: var(--destructive-background);
  color: var(--destructive);
  border-radius: var(--radius-sm);
  font-size: 13px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(var(--space-2));
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-messages::-webkit-scrollbar {
  width: var(--space-3);
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--accent);
  border-radius: var(--radius-xs);
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--border);
}

.agent-status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  margin-top: calc(-1 * var(--space-4));
  animation: fadeIn 0.2s ease;
}

.status-spinner {
  color: var(--primary);
  flex-shrink: 0;
  animation: spin 1s linear infinite;
}

.status-text {
  font-size: 13px;
  color: var(--muted-foreground);
  font-weight: 500;
  opacity: 0.7;
}

.status-text.shimmer-text {
  background: linear-gradient(
    270deg,
    var(--muted-foreground) 0%,
    var(--muted-foreground) 35%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 42%,
    white 50%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 58%,
    var(--muted-foreground) 65%,
    var(--muted-foreground) 100%
  );
  background-size: 400% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0.7;
  animation: shimmer-sweep-reverse 3.5s linear infinite;
}

.status-indicator .status-text.shimmer-text,
.turn-loading .status-text.shimmer-text {
  background: linear-gradient(
    270deg,
    var(--muted-foreground) 0%,
    var(--muted-foreground) 35%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 42%,
    white 50%,
    color-mix(in srgb, var(--muted-foreground) 20%, white 80%) 58%,
    var(--muted-foreground) 65%,
    var(--muted-foreground) 100%
  );
  background-size: 400% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0.7;
  animation: shimmer-sweep-reverse 3.5s linear infinite;
}
</style>
