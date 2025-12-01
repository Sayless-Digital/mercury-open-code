mercury
<template>
  <div class="chat-panel">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <Brain class="chat-icon" :size="14" />
        <span class="chat-title">Agent</span>
      </div>
      <button class="clear-btn" @click="clearChat" title="Clear">
        <Eraser :size="14" />
        Clear
      </button>
    </div>
    
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
                    <div v-else-if="part.type === 'tool'" class="message-part tool-part">
                      <div class="tool-call">
                        <div class="tool-header">
                          <span class="tool-name">{{ part.tool }}</span>
                          <span class="tool-status" :class="getToolStatusClass(part.state?.status)">
                            {{ getToolStatusText(part.state?.status) }}
                          </span>
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
                        
                        <!-- Show file path for edit/write tools without diff -->
                        <div v-else-if="(part.tool === 'edit' || part.tool === 'write') && part.state?.input?.filePath" class="tool-file-path">
                          <span class="file-path-label">File:</span>
                          <span class="file-path-value">{{ part.state.input.filePath }}</span>
                        </div>
                        
                        <div v-if="part.state?.input && !((part.tool === 'edit' || part.tool === 'write') && part.metadata?.filediff)" class="tool-input">
                          <pre>{{ JSON.stringify(part.state.input, null, 2) }}</pre>
                        </div>
                        <div v-if="part.state?.output && part.tool !== 'edit' && part.tool !== 'write'" class="tool-output">
                          <pre>{{ part.state.output }}</pre>
                        </div>
                        <div v-if="part.state?.error" class="tool-error">
                          Error: {{ part.state.error }}
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
        <button
          v-if="!autoRecordMode && !isRecording"
          class="voice-button"
          @click="toggleRecording"
          :disabled="loading"
          title="Start voice recording"
        >
          <Mic :size="18" />
        </button>
        <textarea
          v-model="inputText"
          @keydown="handleKeyDown"
          @input="handleInput"
          @focus="handleInputFocus"
          :disabled="loading"
          :placeholder="showTranscribingPlaceholder ? '' : 'Type or speak your message...'"
          class="chat-input"
          :class="{ 'transcribing-placeholder': showTranscribingPlaceholder }"
          rows="1"
          ref="inputRef"
        ></textarea>
        <div v-if="showTranscribingPlaceholder" class="transcribing-overlay">
          <span class="transcribing-text">Listening</span>
        </div>
        <button
          v-if="isRecording"
          class="stop-button"
          @click="stopRecording"
          :disabled="loading"
          title="Stop recording"
        >
          <Square :size="14" />
        </button>
        <button
          v-if="isRecording && inputText.trim()"
          class="send-button"
          @click="sendMessage"
          :disabled="loading || !inputText.trim()"
          title="Send message"
        >
          <Send :size="14" />
        </button>
        <button
          v-else-if="isTranscribingFinal || isTranscribing.value"
          class="loading-button"
          disabled
          title="Transcribing..."
        >
          <Loader2 :size="14" class="spinner" />
        </button>
        <template v-else-if="inputText.trim()">
          <button
            class="clear-input-button"
            @click="clearInput"
            :disabled="loading"
            title="Clear input"
          >
            <Eraser :size="14" />
          </button>
          <button
            class="send-button"
            @click="sendMessage"
            :disabled="loading || !inputText.trim()"
            title="Send message"
          >
            <Send :size="14" />
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
      <div v-if="error" class="error-message">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue';
import {
  Mic, Square, Send, Loader2, Eraser, Brain, RefreshCw
} from 'lucide-vue-next';
import { useChatStore } from '@/stores/chat';
import { useProjectStore } from '@/stores/project';
import { useSettingsStore } from '@/stores/settings';
import TaskControlPanel from './TaskControlPanel.vue';
import WorkflowSummaryCard from './WorkflowSummaryCard.vue';
import SideBySideDiff from './SideBySideDiff.vue';

const chatStore = useChatStore();
const projectStore = useProjectStore();
const settingsStore = useSettingsStore();

const messages = computed(() => chatStore.messages); // Legacy support
const turns = computed(() => chatStore.turns); // New turn-based structure
const loading = computed(() => chatStore.loading);
const error = computed(() => chatStore.error);
const autoRecordMode = computed(() => settingsStore.autoRecordMode);
const whisperModelId = computed(() => settingsStore.whisperModelId);
const workflowState = computed(() => chatStore.workflowState);

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
  hasManuallyStopped.value = false;
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto';
      inputRef.value.style.height = inputRef.value.scrollHeight + 'px';
    }
  });
  
  if (autoRecordMode.value && !isRecording.value && !loading.value && whisperModelId.value) {
    await nextTick();
    if (!inputText.value.trim()) {
      await startRecording();
    }
  }
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
      const chunkSize = isFinal ? 3 : 2;
      const nextChunk = textToStream.substring(streamedLength, streamedLength + chunkSize);
      streamedLength += nextChunk.length;
      
      const baseText = inputText.value.substring(0, startPosition);
      inputText.value = baseText + textToStream.substring(0, streamedLength);
      resizeTextarea();
      
      streamingTimeout = setTimeout(streamNext, isFinal ? 20 : 30);
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
      const newHeight = Math.min(inputRef.value.scrollHeight, 200);
      inputRef.value.style.height = newHeight + 'px';
    }
  });
};

const handleInputFocus = async () => {
  if (autoRecordMode.value && !isRecording.value && !loading.value && !hasManuallyStopped.value && !inputText.value.trim()) {
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
  
  const text = inputText.value.trim();
  inputText.value = '';
  accumulatedText = '';
  isTranscribingFinal.value = false;
  hasReceivedTranscription.value = false;
  hasManuallyStopped.value = false;
  
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto';
      inputRef.value.style.height = inputRef.value.scrollHeight + 'px';
    }
  });
  
  const context = {
    projectPath: projectStore.currentProject?.path,
    activeFile: projectStore.activeFile,
  };
  
  await chatStore.sendMessageStream(text, context);
  scrollToBottom();
};

const clearChat = () => {
  chatStore.clearMessages();
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

const formatMessage = (content) => {
  if (!content) return '';
  return content
    .replace(/\n/g, '<br>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

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
    
    const CHUNK_DURATION_MS = 3000;
    
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
    }, 3500);
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
  gap: var(--space-4);
}

.chat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ring);
  flex-shrink: 0;
}

.chat-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--foreground);
  margin: 0;
}

.clear-btn {
  background: var(--muted);
  border: none;
  color: var(--foreground);
  cursor: pointer;
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-size: 12px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-family: inherit;
}

.clear-btn:hover {
  background: var(--accent);
  opacity: 0.9;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
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
  font-size: 20px;
  font-weight: 600;
  color: var(--foreground);
  margin: 0;
}

.empty-state-text {
  font-size: 14px;
  color: var(--muted-foreground);
  line-height: 1.6;
  margin: 0;
}

/* Turn-based structure (OpenCode style) */
.chat-turn {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-4) var(--space-4) 0;
  border-bottom: 1px solid var(--border);
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
}

.turn-assistant-response {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-left: var(--space-4);
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

.text-part .text-content {
  color: var(--foreground);
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  padding: 0;
  margin: 0;
}

.tool-part {
  background: var(--muted);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}

.tool-call {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.tool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
}

.tool-name {
  color: var(--foreground);
}

.tool-status {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.tool-status.status-running {
  background: var(--accent);
  color: var(--accent-foreground);
}

.tool-status.status-completed {
  background: var(--success);
  color: var(--success-foreground);
}

.tool-status.status-error {
  background: var(--destructive);
  color: var(--destructive-foreground);
}

.tool-input,
.tool-output {
  background: var(--background);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  overflow-x: auto;
}

.tool-error {
  color: var(--destructive);
  font-size: var(--text-sm);
}

.tool-diff {
  margin-top: var(--space-3);
  width: 100%;
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
  font-size: 15px;
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
  font-size: 13px;
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
  margin-top: var(--space-2);
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
  padding: var(--space-2);
  background: var(--muted);
  border-top: 1px solid var(--border);
}

.input-wrapper {
  display: flex;
  gap: var(--space-2);
  align-items: flex-end;
  position: relative;
}

.voice-button {
  padding: var(--space-5);
  margin-bottom: var(--space-2);
  background: var(--accent);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  color: var(--foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.voice-button:hover:not(:disabled) {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.voice-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.voice-button-inline {
  width: var(--button-md);
  height: var(--button-md);
  min-width: var(--button-md);
  min-height: var(--button-md);
  padding: 0;
  margin-bottom: var(--space-2);
  border-radius: var(--radius-lg);
}

.stop-button {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  margin-bottom: var(--space-2);
  background: var(--destructive);
  border: none;
  border-radius: var(--radius-lg);
  color: var(--destructive-foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.stop-button:hover:not(:disabled) {
  background: var(--destructive);
  opacity: 0.9;
  transform: scale(1.05);
}

.stop-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-button {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  margin-bottom: var(--space-2);
  background: var(--primary);
  border: none;
  border-radius: var(--radius-lg);
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
  transform: scale(1.05);
}

.send-button:disabled {
  background: var(--muted);
  color: var(--muted-foreground);
  opacity: 0.6;
  cursor: not-allowed;
}

.clear-input-button {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  margin-bottom: var(--space-2);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  color: var(--foreground);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.clear-input-button:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--border);
  color: var(--foreground);
  transform: scale(1.05);
}

.clear-input-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-button {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  margin-bottom: var(--space-2);
  background: var(--warning);
  border: none;
  border-radius: var(--radius-lg);
  color: var(--warning-foreground);
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
  padding: var(--space-5) var(--space-6);
  background: var(--background);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  color: var(--foreground);
  font-size: 14px;
  font-family: inherit;
  resize: none;
  min-height: var(--input-md);
  max-height: 200px;
  overflow-y: auto;
  box-sizing: border-box;
  line-height: 1.5;
}

.chat-input.transcribing-placeholder {
  color: transparent;
}

.transcribing-overlay {
  position: absolute;
  left: var(--space-6);
  top: var(--space-5);
  pointer-events: none;
  z-index: 1;
}

.transcribing-text {
  font-size: 14px;
  font-family: inherit;
  color: var(--foreground);
  opacity: 0.7;
  background: linear-gradient(
    90deg,
    var(--foreground) 0%,
    var(--foreground) 30%,
    color-mix(in srgb, var(--foreground) 80%, white 20%) 45%,
    color-mix(in srgb, var(--foreground) 40%, white 60%) 50%,
    color-mix(in srgb, var(--foreground) 80%, white 20%) 55%,
    var(--foreground) 70%,
    var(--foreground) 100%
  );
  background-size: 300% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer-sweep 2.5s infinite;
}

@keyframes shimmer-sweep {
  0% {
    background-position: -100% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.chat-input:focus {
  outline: none;
  border-color: var(--border);
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
  font-size: 12px;
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
  font-size: 14px;
  color: var(--foreground);
  font-weight: 500;
}

.status-text.shimmer-text {
  background: linear-gradient(
    90deg,
    var(--foreground) 0%,
    var(--foreground) 30%,
    color-mix(in srgb, var(--foreground) 80%, white 20%) 45%,
    color-mix(in srgb, var(--foreground) 40%, white 60%) 50%,
    color-mix(in srgb, var(--foreground) 80%, white 20%) 55%,
    var(--foreground) 70%,
    var(--foreground) 100%
  );
  background-size: 300% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer-sweep 2.5s infinite;
}
</style>
