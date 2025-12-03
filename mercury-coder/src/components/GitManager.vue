<template>
  <div class="git-manager">
    <!-- Header -->
    <div class="git-header">
      <div class="header-left">
        <GitBranch :size="16" class="header-icon" />
        <!-- Branch dropdown replaces "Source Control" title -->
        <div class="branch-dropdown branch-dropdown-in-title" v-if="currentBranch">
          <button 
            class="branch-dropdown-btn branch-dropdown-title" 
            @click.stop="toggleBranchDropdown"
            :disabled="loading"
          >
            <span class="branch-dropdown-text">{{ currentBranch }}</span>
            <span class="branch-status-small" v-if="branchStatus" :class="getBranchStatusClass()">
              {{ branchStatus }}
            </span>
            <ChevronDown :size="12" :class="{ rotated: branchDropdownOpen }" />
          </button>
          <div class="branch-dropdown-menu" v-if="branchDropdownOpen" @click.stop>
            <div class="branch-dropdown-header">Branches</div>
            <div 
              v-for="branch in allBranches" 
              :key="branch.name"
              class="branch-item"
              :class="{ active: branch.name === currentBranch, current: branch.isCurrent }"
              @click="switchBranch(branch.name)"
            >
              <GitBranch :size="12" />
              <span class="branch-item-name">{{ branch.name }}</span>
              <Check :size="12" v-if="branch.name === currentBranch" class="branch-check" />
            </div>
            <div v-if="allBranches.length === 0" class="branch-empty">
              No branches found
            </div>
          </div>
        </div>
        <span class="header-title" v-else>Source Control</span>
      </div>
      <div class="header-actions">
        <button 
          class="header-action-btn" 
          @click="handlePull"
          :disabled="loading || pushing || !currentBranch"
          title="Pull from remote"
        >
          <ArrowDown :size="14" />
        </button>
        <button 
          class="header-action-btn" 
          @click="handlePush"
          :disabled="loading || pushing || !hasCommitsToPush || !currentBranch"
          title="Push to remote"
        >
          <ArrowUp :size="14" />
        </button>
        <button 
          class="header-action-btn" 
          @click="refreshGitStatus" 
          :disabled="loading" 
          title="Refresh"
        >
          <RefreshCw :size="14" :class="{ spinning: loading }" />
        </button>
      </div>
    </div>

    <div class="git-body" v-if="projectPath">
      <!-- Commit Message Input (First - at the top) -->
      <div class="commit-input-container">
        <textarea
          ref="commitMessageTextarea"
          v-model="commitMessage"
          class="commit-input-single"
          placeholder="Enter commit message..."
          :disabled="!hasChanges"
          @keydown="handleCommitKeydown"
          @input="autoResizeTextarea"
          rows="1"
        />
        <button
          class="ai-generate-btn"
          @click="generateCommitMessage"
          :disabled="!hasChanges || generatingMessage"
          title="Generate commit message with AI"
        >
          <Loader2 v-if="generatingMessage" :size="14" class="spinning" />
          <Sparkles v-else :size="14" />
        </button>
      </div>

      <!-- Commit Button (Below input) -->
      <div class="commit-button-container">
        <button 
          class="commit-btn-primary" 
          @click="handleCommit"
          :disabled="!commitMessage.trim() || committing || !hasChanges"
          :class="{ loading: committing }"
        >
          <Check :size="14" v-if="!committing" />
          <span v-if="committing">Committing...</span>
          <span v-else>Commit</span>
        </button>
      </div>

      <!-- Changes Dropdown -->
      <div class="changes-group">
        <div class="group-header" @click="toggleChangesGroup">
          <div class="group-header-left">
            <div class="group-icon changes-icon">
              <FileDiff :size="12" />
            </div>
            <span class="group-title">CHANGES</span>
            <span class="group-badge">{{ allFiles.length }}</span>
          </div>
          <ChevronDown :size="14" :class="{ rotated: changesExpanded }" />
        </div>
        <div class="group-content" v-show="changesExpanded">
          <div 
            v-for="file in allFiles" 
            :key="file.path" 
            class="file-entry"
            :class="{ staged: file.isStaged }"
            @click="toggleFileStaged(file)"
          >
            <div class="file-icon-wrapper">
              <File :size="13" />
            </div>
            <div class="file-info">
              <span class="file-name">{{ getFileName(file.path) }}</span>
              <span class="file-dir">{{ getFileDir(file.path) }}</span>
            </div>
            <div class="file-actions">
              <span class="status-badge" :class="getStatusClass(file.status)">
                {{ getShortStatus(file.status) }}
              </span>
              <span class="stage-indicator" v-if="file.isStaged">Staged</span>
              <button class="file-action-btn" @click.stop="toggleFileStaged(file)" :title="file.isStaged ? 'Unstage' : 'Stage'">
                <Minus :size="12" v-if="file.isStaged" />
                <Plus :size="12" v-else />
              </button>
            </div>
          </div>
          <div v-if="allFiles.length === 0" class="empty-files">
            <p>No changes</p>
          </div>
        </div>
      </div>

      <!-- History Dropdown -->
      <div class="changes-group">
        <div class="group-header" @click="toggleHistoryGroup">
          <div class="group-header-left">
            <div class="group-icon history-icon">
              <GitCommit :size="12" />
            </div>
            <span class="group-title">HISTORY</span>
            <span class="group-badge">{{ commitHistory.length }}</span>
          </div>
          <ChevronDown :size="14" :class="{ rotated: historyExpanded }" />
        </div>
        <div class="group-content history-content" v-show="historyExpanded">
          <div 
            v-for="commit in commitHistory" 
            :key="commit.hash" 
            class="commit-entry"
          >
            <div class="commit-hash">{{ commit.hash.substring(0, 7) }}</div>
            <div class="commit-info">
              <div class="commit-message">{{ commit.message }}</div>
              <div class="commit-meta">
                <span class="commit-author">{{ commit.author }}</span>
                <span class="commit-date">{{ commit.date }}</span>
              </div>
            </div>
          </div>
          <div v-if="commitHistory.length === 0" class="empty-files">
            <p>No commits</p>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div class="empty-state" v-if="!loading && !hasChanges && !error">
        <div class="empty-icon">
          <GitBranch :size="32" />
        </div>
        <p class="empty-title" v-if="currentBranch">No changes</p>
        <p class="empty-subtitle" v-if="currentBranch">Working tree clean</p>
        <p class="empty-title" v-else>Not a git repository</p>
      </div>

      <!-- Loading State -->
      <div class="loading-state" v-if="loading && !hasChanges">
        <RefreshCw :size="16" class="spinning" />
        <span>Loading changes...</span>
      </div>

      <!-- Error State -->
      <div class="error-banner" v-if="error">
        <AlertCircle :size="14" />
        <span class="error-text">{{ error }}</span>
        <button class="error-dismiss" @click="error = null">
          <X :size="14" />
        </button>
      </div>
    </div>

    <div v-else class="empty-state full">
      <p>No project open</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue';
import { 
  GitBranch, RefreshCw, File, Check, ArrowUp, ArrowDown, AlertCircle,
  FileDiff, Plus, Minus, ChevronDown, X, GitCommit, Sparkles, Loader2
} from 'lucide-vue-next';
import { useOpencode } from '@/composables/useOpencode';

const props = defineProps({
  projectPath: {
    type: String,
    default: null,
  },
});

const loading = ref(false);
const committing = ref(false);
const pushing = ref(false);
const error = ref(null);
const currentBranch = ref(null);
const branchStatus = ref('');
const stagedFiles = ref([]);
const unstagedFiles = ref([]);
const commitMessage = ref('');
const hasCommitsToPush = ref(false);
const changesExpanded = ref(true);
const historyExpanded = ref(true);
const commitHistory = ref([]);
const generatingMessage = ref(false);
const { client } = useOpencode();
const branchDropdownOpen = ref(false);
const allBranches = ref([]);
const commitMessageTextarea = ref(null);

const hasChanges = computed(() => {
  return stagedFiles.value.length > 0 || unstagedFiles.value.length > 0;
});

const toggleChangesGroup = () => {
  changesExpanded.value = !changesExpanded.value;
};

const toggleHistoryGroup = () => {
  historyExpanded.value = !historyExpanded.value;
  if (historyExpanded.value && commitHistory.value.length === 0) {
    loadCommitHistory();
  }
};

const allFiles = computed(() => {
  const files = [];
  stagedFiles.value.forEach(file => {
    files.push({ ...file, isStaged: true });
  });
  unstagedFiles.value.forEach(file => {
    files.push({ ...file, isStaged: false });
  });
  return files;
});

const getFileName = (filePath) => {
  return filePath.split(/[/\\]/).pop();
};

const getFileDir = (filePath) => {
  const parts = filePath.split(/[/\\]/);
  if (parts.length > 1) {
    return parts.slice(0, -1).join('/');
  }
  return '';
};

const getShortStatus = (status) => {
  const short = {
    'Modified': 'M',
    'Added': 'A',
    'Deleted': 'D',
    'Renamed': 'R',
    'Copied': 'C',
    'Unmerged': 'U',
    'Untracked': '?'
  };
  return short[status] || status[0];
};

const getStatusClass = (status) => {
  const classes = {
    'Modified': 'status-modified',
    'Added': 'status-added',
    'Deleted': 'status-deleted',
    'Renamed': 'status-renamed',
    'Untracked': 'status-untracked'
  };
  return classes[status] || '';
};

const getBranchStatusClass = () => {
  if (branchStatus.value.includes('↑')) return 'status-ahead';
  if (branchStatus.value.includes('↓')) return 'status-behind';
  return '';
};

const toggleBranchDropdown = () => {
  branchDropdownOpen.value = !branchDropdownOpen.value;
  if (branchDropdownOpen.value && allBranches.value.length === 0) {
    loadAllBranches();
  }
};

const loadAllBranches = async () => {
  if (!window.electronAPI || !props.projectPath) return;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['branch'],
      cwd: props.projectPath
    });
    
    if (result.success && result.stdout) {
      const lines = result.stdout.trim().split('\n').filter(line => line.trim());
      const branches = lines.map(line => {
        const isCurrent = line.startsWith('*');
        const name = line.replace(/^\*\s+/, '').trim();
        return {
          name: name,
          isCurrent: isCurrent
        };
      }).filter(branch => branch.name && !branch.name.includes('HEAD'));
      
      // Sort: current branch first, then alphabetically
      allBranches.value = branches.sort((a, b) => {
        if (a.name === currentBranch.value) return -1;
        if (b.name === currentBranch.value) return 1;
        return a.name.localeCompare(b.name);
      });
    } else {
      allBranches.value = [];
    }
  } catch (err) {
    console.error('Error loading branches:', err);
    allBranches.value = [];
  }
};

const switchBranch = async (branchName) => {
  if (!window.electronAPI || !props.projectPath || branchName === currentBranch.value) {
    branchDropdownOpen.value = false;
    return;
  }
  
  loading.value = true;
  error.value = null;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['checkout', branchName],
      cwd: props.projectPath
    });
    
    if (result.success) {
      branchDropdownOpen.value = false;
      await refreshGitStatus();
    } else {
      error.value = result.stderr || 'Failed to switch branch';
    }
  } catch (err) {
    error.value = err.message || 'Failed to switch branch';
    console.error('Switch branch error:', err);
  } finally {
    loading.value = false;
  }
};

const refreshGitStatus = async () => {
  if (!props.projectPath) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    await Promise.all([
      getCurrentBranch(),
      getGitStatus(),
      checkCommitsToPush()
    ]);
    if (historyExpanded.value) {
      await loadCommitHistory();
    }
    // Refresh branches list if dropdown is open
    if (branchDropdownOpen.value) {
      await loadAllBranches();
    }
  } catch (err) {
    error.value = err.message || 'Failed to refresh git status';
    console.error('Git status error:', err);
  } finally {
    loading.value = false;
  }
};

const getCurrentBranch = async () => {
  if (!window.electronAPI) return;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['rev-parse', '--abbrev-ref', 'HEAD'],
      cwd: props.projectPath
    });
    
    if (result.success && result.stdout) {
      currentBranch.value = result.stdout.trim();
      
      try {
        const statusResult = await window.electronAPI.executeCommand({
          command: 'git',
          args: ['status', '-sb'],
          cwd: props.projectPath
        });
        
        if (statusResult.success && statusResult.stdout) {
          const statusLine = statusResult.stdout.split('\n')[0];
          if (statusLine.includes('ahead')) {
            const match = statusLine.match(/ahead (\d+)/);
            branchStatus.value = match ? `↑${match[1]}` : '';
          } else if (statusLine.includes('behind')) {
            const match = statusLine.match(/behind (\d+)/);
            branchStatus.value = match ? `↓${match[1]}` : '';
          } else {
            branchStatus.value = '';
          }
        }
      } catch (statusErr) {
        branchStatus.value = '';
      }
    } else {
      currentBranch.value = null;
      branchStatus.value = '';
    }
  } catch (err) {
    currentBranch.value = null;
    branchStatus.value = '';
  }
};

const getGitStatus = async () => {
  if (!window.electronAPI) return;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['status', '--porcelain'],
      cwd: props.projectPath
    });
    
    if (result.success && result.stdout) {
      const lines = result.stdout.trim().split('\n').filter(line => line.trim());
      stagedFiles.value = [];
      unstagedFiles.value = [];
      
      lines.forEach(line => {
        const status = line.substring(0, 2);
        const path = line.substring(3);
        const stagedStatus = status[0];
        const unstagedStatus = status[1];
        
        if (stagedStatus !== ' ' && stagedStatus !== '?') {
          stagedFiles.value.push({
            path,
            status: getStatusLabel(stagedStatus)
          });
        }
        
        if (unstagedStatus !== ' ' && unstagedStatus !== '?') {
          unstagedFiles.value.push({
            path,
            status: getStatusLabel(unstagedStatus)
          });
        }
      });
    }
  } catch (err) {
    console.error('Error getting git status:', err);
  }
};

const getStatusLabel = (status) => {
  const labels = {
    'M': 'Modified',
    'A': 'Added',
    'D': 'Deleted',
    'R': 'Renamed',
    'C': 'Copied',
    'U': 'Unmerged',
    '?': 'Untracked'
  };
  return labels[status] || status;
};

const checkCommitsToPush = async () => {
  if (!window.electronAPI || !currentBranch.value) {
    hasCommitsToPush.value = false;
    return;
  }
  
  try {
    const remoteCheck = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['remote', 'get-url', 'origin'],
      cwd: props.projectPath
    });
    
    if (!remoteCheck.success) {
      hasCommitsToPush.value = false;
      return;
    }
    
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['rev-list', '--count', `origin/${currentBranch.value}..HEAD`],
      cwd: props.projectPath
    });
    
    if (result.success && result.stdout) {
      const count = parseInt(result.stdout.trim());
      hasCommitsToPush.value = count > 0;
    } else {
      hasCommitsToPush.value = false;
    }
  } catch (err) {
    hasCommitsToPush.value = false;
  }
};

const toggleFileStaged = async (file) => {
  if (!window.electronAPI) return;
  
  const isStaged = stagedFiles.value.some(f => f.path === file.path);
  
  try {
    if (isStaged) {
      await window.electronAPI.executeCommand({
        command: 'git',
        args: ['reset', 'HEAD', '--', file.path],
        cwd: props.projectPath
      });
    } else {
      await window.electronAPI.executeCommand({
        command: 'git',
        args: ['add', file.path],
        cwd: props.projectPath
      });
    }
    
    await refreshGitStatus();
  } catch (err) {
    error.value = err.message || 'Failed to stage/unstage file';
    console.error('Error toggling file:', err);
  }
};

const handleCommit = async () => {
  if (!commitMessage.value.trim()) {
    error.value = 'Please enter a commit message';
    return;
  }
  
  if (!hasChanges.value) {
    error.value = 'No changes to commit';
    return;
  }
  
  committing.value = true;
  error.value = null;
  
  try {
    // Auto-stage all files if there are unstaged changes and no staged files
    if (stagedFiles.value.length === 0 && unstagedFiles.value.length > 0) {
      // Stage all modified and new files
      const stageResult = await window.electronAPI.executeCommand({
        command: 'git',
        args: ['add', '-A'],
        cwd: props.projectPath
      });
      
      if (!stageResult.success) {
        error.value = `Failed to stage files: ${stageResult.stderr || stageResult.stdout || 'Unknown error'}`;
        return;
      }
      
      // Refresh status to get the newly staged files
      await getGitStatus();
    }
    
    // Handle multi-line commit messages properly
    // Split by newlines and use multiple -m flags (one per line)
    const messageLines = commitMessage.value.trim().split('\n').filter(line => line.trim());
    const commitArgs = ['commit'];
    
    // Add each line as a separate -m flag
    messageLines.forEach(line => {
      commitArgs.push('-m', line.trim());
    });
    
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: commitArgs,
      cwd: props.projectPath
    });
    
    if (result.success) {
      commitMessage.value = '';
      autoResizeTextarea(); // Reset height after clearing
      await refreshGitStatus();
    } else {
      // Check if the error is about no staged files
      const errorOutput = (result.stderr || result.stdout || '').toLowerCase();
      if (errorOutput.includes('no changes added to commit') || 
          errorOutput.includes('nothing to commit') ||
          errorOutput.includes('changes not staged for commit')) {
        error.value = 'No staged files to commit. Please stage files first using the + button next to each file.';
      } else {
        error.value = result.stderr || result.stdout || 'Commit failed';
      }
      console.error('Commit failed:', result.stderr || result.stdout);
    }
  } catch (err) {
    error.value = err.message || 'Failed to commit';
    console.error('Commit error:', err);
  } finally {
    committing.value = false;
  }
};

const autoResizeTextarea = () => {
  if (!commitMessageTextarea.value) return;
  
  // Reset height to auto to get the correct scrollHeight
  commitMessageTextarea.value.style.height = 'auto';
  
  // Set height to scrollHeight, with a max height of ~200px (about 8-9 lines)
  const maxHeight = 200;
  const newHeight = Math.min(commitMessageTextarea.value.scrollHeight, maxHeight);
  commitMessageTextarea.value.style.height = `${newHeight}px`;
  
  // Enable scrolling if content exceeds max height
  commitMessageTextarea.value.style.overflowY = commitMessageTextarea.value.scrollHeight > maxHeight ? 'auto' : 'hidden';
};

const handleCommitKeydown = (event) => {
  // Enter alone commits, Shift+Enter creates new line
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    handleCommit();
  }
};

const handleCommitAndPush = async () => {
  await handleCommit();
  if (!error.value) {
    await handlePush();
  }
};

const handlePush = async () => {
  if (!currentBranch.value) return;
  
  pushing.value = true;
  error.value = null;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['push', 'origin', currentBranch.value],
      cwd: props.projectPath
    });
    
    if (result.success) {
      await refreshGitStatus();
    } else {
      error.value = result.stderr || 'Push failed';
    }
  } catch (err) {
    error.value = err.message || 'Failed to push';
    console.error('Push error:', err);
  } finally {
    pushing.value = false;
  }
};

const loadCommitHistory = async () => {
  if (!window.electronAPI || !props.projectPath) return;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['log', '--pretty=format:%H|%an|%ad|%s', '--date=relative', '-30'],
      cwd: props.projectPath
    });
    
    if (result.success && result.stdout) {
      const lines = result.stdout.trim().split('\n').filter(line => line.trim());
      commitHistory.value = lines.map(line => {
        const [hash, author, date, ...messageParts] = line.split('|');
        return {
          hash: hash || '',
          author: author || 'Unknown',
          date: date || '',
          message: messageParts.join('|') || ''
        };
      });
    } else {
      commitHistory.value = [];
    }
  } catch (err) {
    console.error('Error loading commit history:', err);
    commitHistory.value = [];
  }
};

const generateCommitMessage = async () => {
  if (!window.electronAPI || !props.projectPath || !hasChanges.value) {
    error.value = 'No modified files to generate commit message for';
    return;
  }
  
  generatingMessage.value = true;
  error.value = null;
  
  // Create a temporary session for this isolated request (won't appear in main chat)
  let tempSessionId = null;
  
  try {
    // Get git diff of all changes (staged + unstaged)
    const diffResult = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['diff', '--stat'],
      cwd: props.projectPath
    });
    
    // Also get staged changes separately for better context
    const stagedDiffResult = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['diff', '--cached', '--stat'],
      cwd: props.projectPath
    });
    
    const diff = diffResult.stdout || '';
    const stagedDiff = stagedDiffResult.success ? stagedDiffResult.stdout || '' : '';
    
    // Include all modified files (staged + unstaged)
    const allModifiedFiles = [...stagedFiles.value, ...unstagedFiles.value];
    const filesChanged = allModifiedFiles.map(f => f.path).join(', ');
    
    // Get more detailed diff for better context (limit size to avoid token limits)
    // Get both staged and unstaged changes
    const detailedDiffResult = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['diff'],
      cwd: props.projectPath
    });
    
    const stagedDetailedDiffResult = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['diff', '--cached'],
      cwd: props.projectPath
    });
    
    let detailedDiff = '';
    if (detailedDiffResult.success && detailedDiffResult.stdout) {
      detailedDiff += 'Unstaged changes:\n' + detailedDiffResult.stdout.substring(0, 1500);
    }
    if (stagedDetailedDiffResult.success && stagedDetailedDiffResult.stdout) {
      if (detailedDiff) detailedDiff += '\n\n';
      detailedDiff += 'Staged changes:\n' + stagedDetailedDiffResult.stdout.substring(0, 1500);
    }
    
    // Create prompt for AI
    const prompt = `Generate a professional git commit message based on these modified files.

Files changed: ${filesChanged}
${diff ? `\nDiff summary (all changes):\n${diff}` : ''}
${stagedDiff ? `\nStaged changes summary:\n${stagedDiff}` : ''}
${detailedDiff ? `\nDetailed changes:\n${detailedDiff}` : ''}

Requirements:
- Use conventional commit format (e.g., "feat:", "fix:", "docs:", "refactor:", "style:", "test:", "chore:", etc.)
- First line should be a concise summary (under 72 characters)
- Follow with a blank line, then bullet points describing the changes
- Each bullet point should start with "- " and describe what was done
- Focus on the "what" and "why" from the user's perspective
- Be specific about the changes made

Format example:
feat: implement feature name

- Added new functionality for X
- Updated Y to support Z
- Improved performance of W

Return ONLY the commit message, nothing else. No explanations, no code blocks, just the commit message text.`;

    if (!client.value) {
      error.value = 'Failed to connect to AI service';
      return;
    }
    
    // Create temporary session
    const createResult = await client.value.session.create({
      body: { title: 'Commit Message Generator' },
      query: { directory: props.projectPath }
    });
    
    if (createResult.error || !createResult.data) {
      error.value = 'Failed to create temporary session: ' + (createResult.error?.message || 'Unknown error');
      return;
    }
    
    tempSessionId = createResult.data.id;
    
    // Get model from config
    const configResult = await client.value.config.get({
      query: { directory: props.projectPath }
    });
    
    const model = configResult.data?.model || 'amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0';
    const [providerID, modelID] = model.includes('/') ? model.split('/') : ['amazon-bedrock', model];
    
    // Use session.prompt - it returns the response directly (synchronous, fast)
    const promptResult = await client.value.session.prompt({
      path: { id: tempSessionId },
      body: {
        providerID,
        modelID,
        agent: 'build',
        parts: [{
          type: 'text',
          text: prompt
        }]
      }
    });
    
    if (promptResult.error) {
      error.value = 'Failed to generate commit message: ' + (promptResult.error.message || 'Unknown error');
      return;
    }
    
    // Extract text from response (direct response, no events needed)
    const textParts = promptResult.data?.parts?.filter(p => p.type === 'text') || [];
    if (textParts.length === 0) {
      error.value = 'No text response from AI';
      return;
    }
    
    // Get the last text part (most complete response)
    const message = textParts[textParts.length - 1].text.trim();
    
    if (!message) {
      error.value = 'Empty response from AI';
      return;
    }
  
    // Clean up the message - remove any markdown formatting or extra text
    let cleanedMessage = message
      .replace(/^```[\w]*\n?/g, '')
      .replace(/```$/g, '')
      .replace(/^["'](.*)["']$/s, '$1')
      .replace(/^commit message:?\s*/i, '')
      .replace(/^message:?\s*/i, '')
      .replace(/^summary:?\s*/i, '')
      .trim();
    
    // Remove any conversational prefixes from the beginning
    const lines = cleanedMessage.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    
    // Filter out conversational lines at the start
    let startIndex = 0;
    for (let i = 0; i < lines.length; i++) {
      const lower = lines[i].toLowerCase();
      const isConversational = lower.match(/^(perfect!?|great!?|okay,?|sure,?|here'?s?|here is|let'?s?|now let'?s?|i'?ll|i will|based on)/) ||
                              lower.startsWith('commit message:') ||
                              lower.startsWith('message:') ||
                              lower.startsWith('summary:') ||
                              (lower.startsWith('here') && i === 0);
      
      if (!isConversational) {
        startIndex = i;
        break;
      }
    }
    
    const commitMessageLines = lines.slice(startIndex);
    
    if (commitMessageLines.length > 0) {
      commitMessage.value = commitMessageLines.join('\n');
    } else {
      commitMessage.value = cleanedMessage;
    }
    
    // Auto-resize textarea after setting the message
    await nextTick();
    autoResizeTextarea();
    
  } catch (err) {
    error.value = err.message || 'Failed to generate commit message';
    console.error('Generate commit message error:', err);
  } finally {
    // Clean up: delete the temporary session so it doesn't appear in chat
    if (tempSessionId && client.value) {
      try {
        await client.value.session.delete({ path: { id: tempSessionId } });
      } catch (deleteErr) {
        // Ignore delete errors - session will be cleaned up eventually
        console.warn('Failed to delete temporary session:', deleteErr);
      }
    }
    generatingMessage.value = false;
  }
};

const handlePull = async () => {
  if (!currentBranch.value) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    const result = await window.electronAPI.executeCommand({
      command: 'git',
      args: ['pull', 'origin', currentBranch.value],
      cwd: props.projectPath
    });
    
    if (result.success) {
      await refreshGitStatus();
    } else {
      error.value = result.stderr || 'Pull failed';
    }
  } catch (err) {
    error.value = err.message || 'Failed to pull';
    console.error('Pull error:', err);
  } finally {
    loading.value = false;
  }
};

watch(() => props.projectPath, (newPath) => {
  if (newPath) {
    refreshGitStatus();
  } else {
    currentBranch.value = null;
    stagedFiles.value = [];
    unstagedFiles.value = [];
    commitMessage.value = '';
  }
}, { immediate: true });

// Auto-resize textarea when commit message changes
watch(commitMessage, () => {
  // Use nextTick to ensure DOM is updated
  setTimeout(() => {
    autoResizeTextarea();
  }, 0);
});

const handleClickOutside = (event) => {
  const dropdown = event.target.closest('.branch-dropdown');
  if (!dropdown && branchDropdownOpen.value) {
    branchDropdownOpen.value = false;
  }
};

onMounted(() => {
  if (props.projectPath) {
    refreshGitStatus();
  }
  
  // Close dropdown when clicking outside
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.git-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--sidebar);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

/* Header */
.git-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--muted);
  min-height: 40px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  color: var(--primary);
  flex-shrink: 0;
}

.header-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--foreground);
  letter-spacing: 0.2px;
}

/* Branch Dropdown */
.branch-dropdown {
  position: relative;
}

.branch-dropdown-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
}

.branch-dropdown-btn:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--primary);
}

.branch-dropdown-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.branch-dropdown-btn.branch-dropdown-title {
  background: transparent;
  border: none;
  padding: 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.2px;
  color: var(--foreground);
}

.branch-dropdown-btn.branch-dropdown-title:hover:not(:disabled) {
  background: transparent;
  opacity: 0.8;
}

.branch-dropdown-text {
  font-weight: 500;
}

.branch-status-small {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 4px;
  border-radius: 3px;
  background: var(--muted);
  color: var(--muted-foreground);
}

.branch-status-small.status-ahead {
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.branch-status-small.status-behind {
  background: rgba(59, 130, 246, 0.15);
  color: rgb(59, 130, 246);
}

.branch-dropdown-btn svg:last-child {
  color: var(--muted-foreground);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.branch-dropdown-btn svg:last-child.rotated {
  transform: rotate(-180deg);
}

.branch-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 200px;
  max-width: 300px;
  max-height: 300px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.branch-dropdown-header {
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--muted-foreground);
  border-bottom: 1px solid var(--border);
  background: var(--card);
  border-radius: 6px 6px 0 0;
}

.branch-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 12px;
  color: var(--foreground);
  background: var(--card);
}

.branch-item:hover {
  background: var(--accent);
}

.branch-item.active {
  background: rgba(var(--primary-rgb, 59, 130, 246), 0.1);
  font-weight: 500;
}

.branch-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-check {
  color: var(--primary);
  flex-shrink: 0;
}

.branch-empty {
  padding: 16px 12px;
  text-align: center;
  font-size: 11px;
  color: var(--muted-foreground);
  background: var(--card);
  border-radius: 0 0 6px 6px;
}

.header-action-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.15s;
  opacity: 0.7;
}

.header-action-btn:hover:not(:disabled) {
  background: var(--accent);
  color: var(--foreground);
  opacity: 1;
}

.header-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.header-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}

/* Body */
.git-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 8px;
}


/* Changes Container */
.changes-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.changes-group {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--card);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.group-header:hover {
  background: var(--accent);
}

.group-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.group-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  flex-shrink: 0;
}

.group-icon.staged-icon {
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.group-icon.unstaged-icon {
  background: rgba(59, 130, 246, 0.15);
  color: rgb(59, 130, 246);
}

.group-icon.changes-icon {
  background: rgba(59, 130, 246, 0.15);
  color: rgb(59, 130, 246);
}

.group-icon.history-icon {
  background: rgba(168, 85, 247, 0.15);
  color: rgb(168, 85, 247);
}

.group-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--muted-foreground);
}

.group-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  background: var(--muted);
  color: var(--foreground);
  min-width: 20px;
  text-align: center;
}

.group-header svg:last-child {
  color: var(--muted-foreground);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.group-header svg:last-child.rotated {
  transform: rotate(-180deg);
}

.group-content {
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

/* File Entry */
.file-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--border);
}

.file-entry:last-child {
  border-bottom: none;
}

.file-entry:hover {
  background: var(--accent);
}

.file-entry.staged {
  background: rgba(34, 197, 94, 0.05);
}

.file-entry.unstaged {
  background: transparent;
}

.stage-indicator {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.empty-files {
  padding: 16px;
  text-align: center;
  color: var(--muted-foreground);
  font-size: 11px;
}

/* History Content */
.history-content {
  display: flex;
  flex-direction: column;
}

.commit-entry {
  display: flex;
  gap: 10px;
  padding: 10px;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}

.commit-entry:last-child {
  border-bottom: none;
}

.commit-entry:hover {
  background: var(--accent);
}

.commit-hash {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
  color: var(--muted-foreground);
  font-weight: 600;
  flex-shrink: 0;
  min-width: 60px;
}

.commit-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.commit-message {
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.commit-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  color: var(--muted-foreground);
}

.commit-author {
  font-weight: 500;
}

.commit-date {
  opacity: 0.8;
}

.file-icon-wrapper {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted-foreground);
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-dir {
  font-size: 10px;
  color: var(--muted-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.status-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 5px;
  border-radius: 3px;
  background: var(--muted);
  color: var(--muted-foreground);
}

.status-badge.status-modified {
  background: rgba(251, 191, 36, 0.15);
  color: rgb(251, 191, 36);
}

.status-badge.status-added {
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.status-badge.status-deleted {
  background: rgba(239, 68, 68, 0.15);
  color: rgb(239, 68, 68);
}

.status-badge.status-untracked {
  background: rgba(168, 85, 247, 0.15);
  color: rgb(168, 85, 247);
}

.file-action-btn {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  opacity: 0;
  transition: all 0.15s;
}

.file-entry:hover .file-action-btn {
  opacity: 1;
}

.file-action-btn:hover {
  background: var(--accent);
  color: var(--foreground);
}

/* Commit Input Container */
.commit-input-container {
  margin-bottom: 4px;
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.commit-input-single {
  flex: 1;
  padding: 8px 10px;
  padding-right: 36px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--card);
  color: var(--foreground);
  font-size: 12px;
  font-family: inherit;
  transition: border-color 0.15s;
  resize: none;
  overflow-y: hidden;
  min-height: 36px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.ai-generate-btn {
  position: absolute;
  right: 6px;
  top: 6px;
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.15s;
  opacity: 0.7;
  z-index: 1;
}

.ai-generate-btn:hover:not(:disabled) {
  background: var(--accent);
  color: var(--primary);
  opacity: 1;
}

.ai-generate-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.commit-input-single:focus {
  outline: none;
  border-color: var(--primary);
}

.commit-input-single:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.commit-input-single::placeholder {
  color: var(--muted-foreground);
}

/* Commit Button Container */
.commit-button-container {
  margin-bottom: 8px;
}

.commit-btn-primary {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: var(--primary);
  color: var(--primary-foreground);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.commit-btn-primary:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.commit-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.commit-btn-primary.loading {
  opacity: 0.7;
  cursor: wait;
}

/* Commit Container (old - keeping for reference but not used) */
.commit-container {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--card);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.commit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.commit-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--muted-foreground);
}

.commit-hint {
  font-size: 10px;
  color: var(--muted-foreground);
  font-style: italic;
}

.commit-input {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--background);
  color: var(--foreground);
  font-size: 12px;
  font-family: inherit;
  resize: none;
  min-height: 50px;
  line-height: 1.5;
  transition: border-color 0.15s;
}

.commit-input:focus {
  outline: none;
  border-color: var(--primary);
}

.commit-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.commit-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.commit-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--muted-foreground);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.commit-buttons {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.commit-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.commit-btn.primary {
  background: var(--primary);
  color: var(--primary-foreground);
}

.commit-btn.primary:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.commit-btn.secondary {
  background: var(--muted);
  color: var(--foreground);
  border: 1px solid var(--border);
}

.commit-btn.secondary:hover:not(:disabled) {
  background: var(--accent);
}

.commit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.commit-btn.loading {
  opacity: 0.7;
  cursor: wait;
}


/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
  gap: 8px;
}

.empty-state.full {
  height: 100%;
}

.empty-icon {
  color: var(--muted-foreground);
  opacity: 0.4;
  margin-bottom: 8px;
}

.empty-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--foreground);
}

.empty-subtitle {
  font-size: 11px;
  color: var(--muted-foreground);
}

/* Loading State */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--muted-foreground);
  font-size: 12px;
}

/* Error Banner */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  color: rgb(239, 68, 68);
  font-size: 11px;
}

.error-text {
  flex: 1;
}

.error-dismiss {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.error-dismiss:hover {
  opacity: 1;
}

.spinning {
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

/* Scrollbar */
.git-body::-webkit-scrollbar {
  width: 8px;
}

.git-body::-webkit-scrollbar-track {
  background: transparent;
}

.git-body::-webkit-scrollbar-thumb {
  background: var(--muted);
  border-radius: 4px;
}

.git-body::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}
</style>
