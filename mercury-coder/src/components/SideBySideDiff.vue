<template>
  <div class="side-by-side-diff">
    <div class="diff-header">
      <div class="diff-side-header old-side">
        <span class="diff-label">Original</span>
      </div>
      <div class="diff-side-header new-side">
        <span class="diff-label">Modified</span>
      </div>
    </div>
    <div class="diff-content">
      <div class="diff-side old-side">
        <div class="diff-lines">
          <div
            v-for="(line, index) in diffResult.old"
            :key="`old-${index}`"
            class="diff-line"
            :class="getLineClass(index, 'old')"
          >
            <span class="line-number">{{ index + 1 }}</span>
            <span class="line-content">{{ getLineContent(index, 'old') }}</span>
          </div>
        </div>
      </div>
      <div class="diff-side new-side">
        <div class="diff-lines">
          <div
            v-for="(line, index) in diffResult.new"
            :key="`new-${index}`"
            class="diff-line"
            :class="getLineClass(index, 'new')"
          >
            <span class="line-number">{{ index + 1 }}</span>
            <span class="line-content">{{ getLineContent(index, 'new') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  before: {
    type: String,
    required: true
  },
  after: {
    type: String,
    required: true
  },
  filename: {
    type: String,
    default: ''
  }
})

const oldLines = computed(() => {
  return props.before.split('\n')
})

const newLines = computed(() => {
  return props.after.split('\n')
})

// Simple diff algorithm - compare lines and mark changes
const diffResult = computed(() => {
  const old = oldLines.value
  const new_ = newLines.value
  const maxLines = Math.max(old.length, new_.length)
  const result = {
    old: [],
    new: []
  }
  
  for (let i = 0; i < maxLines; i++) {
    const oldLine = old[i]
    const newLine = new_[i]
    
    if (oldLine === undefined) {
      // Line added
      result.old.push({ content: '', type: 'empty' })
      result.new.push({ content: newLine, type: 'added' })
    } else if (newLine === undefined) {
      // Line removed
      result.old.push({ content: oldLine, type: 'removed' })
      result.new.push({ content: '', type: 'empty' })
    } else if (oldLine === newLine) {
      // Line unchanged
      result.old.push({ content: oldLine, type: 'unchanged' })
      result.new.push({ content: newLine, type: 'unchanged' })
    } else {
      // Line modified
      result.old.push({ content: oldLine, type: 'removed' })
      result.new.push({ content: newLine, type: 'added' })
    }
  }
  
  return result
})

const getLineClass = (index, side) => {
  const line = side === 'old' ? diffResult.value.old[index] : diffResult.value.new[index]
  if (!line) return 'line-unchanged'
  return `line-${line.type}`
}

const getLineContent = (index, side) => {
  const line = side === 'old' ? diffResult.value.old[index] : diffResult.value.new[index]
  return line?.content || ''
}
</script>

<style scoped>
.side-by-side-diff {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.diff-header {
  display: flex;
  background: transparent;
  margin-top: 0;
}

.diff-side-header {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 12px;
  font-weight: 500;
}

.diff-side-header.old-side {
  background: color-mix(in srgb, var(--destructive) 15%, transparent 85%);
  color: var(--foreground);
}

.diff-side-header.new-side {
  background: color-mix(in srgb, var(--success) 15%, transparent 85%);
  color: var(--foreground);
}

.diff-label {
  font-weight: 600;
}

.diff-filename {
  color: var(--muted-foreground);
  font-family: var(--font-mono);
  font-size: 11px;
}

.diff-content {
  display: flex;
  max-height: 250px;
  overflow: auto;
  margin-top: 0;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.diff-content::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.diff-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.diff-side::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.diff-side.old-side {
  border-right: none;
}

.diff-lines {
  display: flex;
  flex-direction: column;
  min-width: 100%;
}

.diff-line {
  display: flex;
  min-height: 18px;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.4;
}

.line-number {
  display: inline-block;
  width: 40px;
  padding: 0 var(--space-2);
  text-align: right;
  color: var(--muted-foreground);
  background: var(--muted);
  border-right: none;
  user-select: none;
  flex-shrink: 0;
  font-size: 11px;
}

.line-content {
  flex: 1;
  padding: 0 var(--space-2);
  white-space: pre;
  word-break: break-all;
  font-size: 11px;
}

.diff-line.line-unchanged .line-content {
  background: var(--background);
  color: var(--foreground);
}

.diff-line.line-added {
  background: color-mix(in srgb, var(--success) 15%, transparent 85%);
}

.diff-line.line-added .line-content {
  color: var(--foreground);
}

.diff-line.line-removed {
  background: color-mix(in srgb, var(--destructive) 15%, transparent 85%);
}

.diff-line.line-removed .line-content {
  color: var(--foreground);
  opacity: 0.8;
}

.diff-line.line-empty {
  min-height: 18px;
}

.diff-line.line-empty .line-content {
  background: var(--background);
}

.diff-line.line-added .line-number {
  background: color-mix(in srgb, var(--success) 20%, var(--muted) 80%);
}

.diff-line.line-removed .line-number {
  background: color-mix(in srgb, var(--destructive) 20%, var(--muted) 80%);
}
</style>

