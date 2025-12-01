<template>
  <div class="code-diff">
    <div class="diff-header">
      <span class="file-name">{{ filePath || 'file' }}</span>
      <button 
        v-if="hasChanges" 
        class="view-toggle" 
        @click="toggleView"
        :title="unifiedView ? 'Switch to side-by-side' : 'Switch to unified'"
      >
        {{ unifiedView ? 'Unified' : 'Side-by-side' }}
      </button>
    </div>
    
    <div v-if="!hasChanges" class="no-changes">
      No changes
    </div>
    
    <div v-else-if="unifiedView" class="unified-diff">
      <div 
        v-for="(line, index) in diffLines" 
        :key="index"
        class="diff-line"
        :class="line.type"
      >
        <span class="line-number">{{ line.oldLine || line.newLine || '' }}</span>
        <span class="line-marker">{{ line.marker }}</span>
        <code class="line-content">{{ line.content }}</code>
      </div>
    </div>
    
    <div v-else class="side-by-side-diff">
      <div class="diff-column old">
        <div class="column-header">Old</div>
        <div 
          v-for="(line, index) in oldLines" 
          :key="`old-${index}`"
          class="diff-line"
          :class="line.type"
        >
          <span class="line-number">{{ line.number }}</span>
          <code class="line-content">{{ line.content }}</code>
        </div>
      </div>
      <div class="diff-column new">
        <div class="column-header">New</div>
        <div 
          v-for="(line, index) in newLines" 
          :key="`new-${index}`"
          class="diff-line"
          :class="line.type"
        >
          <span class="line-number">{{ line.number }}</span>
          <code class="line-content">{{ line.content }}</code>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  old: {
    type: String,
    default: ''
  },
  new: {
    type: String,
    default: ''
  },
  filePath: {
    type: String,
    default: ''
  }
});

const unifiedView = ref(true);

const toggleView = () => {
  unifiedView.value = !unifiedView.value;
};

const hasChanges = computed(() => {
  return props.old !== props.new;
});

// Compute unified diff lines
const diffLines = computed(() => {
  if (!hasChanges.value) return [];
  
  const oldLines = props.old.split('\n');
  const newLines = props.new.split('\n');
  const diff = [];
  
  // Simple line-by-line diff
  const maxLen = Math.max(oldLines.length, newLines.length);
  
  for (let i = 0; i < maxLen; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];
    
    if (oldLine === undefined) {
      // Added line
      diff.push({
        type: 'added',
        marker: '+',
        oldLine: null,
        newLine: i + 1,
        content: newLine
      });
    } else if (newLine === undefined) {
      // Removed line
      diff.push({
        type: 'removed',
        marker: '-',
        oldLine: i + 1,
        newLine: null,
        content: oldLine
      });
    } else if (oldLine === newLine) {
      // Unchanged line
      diff.push({
        type: 'unchanged',
        marker: ' ',
        oldLine: i + 1,
        newLine: i + 1,
        content: oldLine
      });
    } else {
      // Modified line - show both
      diff.push({
        type: 'removed',
        marker: '-',
        oldLine: i + 1,
        newLine: null,
        content: oldLine
      });
      diff.push({
        type: 'added',
        marker: '+',
        oldLine: null,
        newLine: i + 1,
        content: newLine
      });
    }
  }
  
  return diff;
});

// Compute side-by-side diff
const oldLines = computed(() => {
  if (!hasChanges.value) return [];
  
  const lines = props.old.split('\n');
  const newLines = props.new.split('\n');
  const result = [];
  
  for (let i = 0; i < lines.length; i++) {
    const oldLine = lines[i];
    const newLine = newLines[i];
    
    if (oldLine === newLine) {
      result.push({
        type: 'unchanged',
        number: i + 1,
        content: oldLine
      });
    } else {
      result.push({
        type: 'removed',
        number: i + 1,
        content: oldLine
      });
    }
  }
  
  return result;
});

const newLines = computed(() => {
  if (!hasChanges.value) return [];
  
  const lines = props.new.split('\n');
  const oldLines = props.old.split('\n');
  const result = [];
  
  for (let i = 0; i < lines.length; i++) {
    const newLine = lines[i];
    const oldLine = oldLines[i];
    
    if (oldLine === newLine) {
      result.push({
        type: 'unchanged',
        number: i + 1,
        content: newLine
      });
    } else {
      result.push({
        type: 'added',
        number: i + 1,
        content: newLine
      });
    }
  }
  
  return result;
});
</script>

<style scoped>
.code-diff {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--background);
  margin: var(--space-2) 0;
}

.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}

.file-name {
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--foreground);
}

.view-toggle {
  padding: var(--space-1) var(--space-2);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--muted-foreground);
  cursor: pointer;
  transition: all 0.2s;
}

.view-toggle:hover {
  background: var(--accent);
  color: var(--foreground);
}

.no-changes {
  padding: var(--space-4);
  text-align: center;
  color: var(--muted-foreground);
  font-size: 13px;
}

.unified-diff {
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  max-height: 400px;
  overflow-y: auto;
}

.diff-line {
  display: flex;
  padding: 0 var(--space-2);
  min-height: 20px;
  align-items: center;
}

.diff-line.unchanged {
  background: var(--background);
}

.diff-line.added {
  background: color-mix(in srgb, var(--success) 15%, transparent);
}

.diff-line.removed {
  background: color-mix(in srgb, var(--destructive) 15%, transparent);
}

.line-number {
  display: inline-block;
  width: 40px;
  text-align: right;
  padding-right: var(--space-2);
  color: var(--muted-foreground);
  font-size: 11px;
  user-select: none;
}

.line-marker {
  display: inline-block;
  width: 20px;
  text-align: center;
  font-weight: 600;
  user-select: none;
}

.diff-line.added .line-marker {
  color: var(--success);
}

.diff-line.removed .line-marker {
  color: var(--destructive);
}

.diff-line.unchanged .line-marker {
  color: var(--muted-foreground);
}

.line-content {
  flex: 1;
  padding-left: var(--space-2);
  white-space: pre;
  font-family: inherit;
  background: transparent;
}

.side-by-side-diff {
  display: grid;
  grid-template-columns: 1fr 1fr;
  max-height: 400px;
  overflow-y: auto;
}

.diff-column {
  border-right: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
}

.diff-column:last-child {
  border-right: none;
}

.column-header {
  padding: var(--space-2) var(--space-3);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  color: var(--muted-foreground);
}

.diff-column .diff-line {
  display: flex;
  padding: 0 var(--space-2);
  min-height: 20px;
  align-items: center;
}

.diff-column .line-number {
  width: 50px;
}
</style>












