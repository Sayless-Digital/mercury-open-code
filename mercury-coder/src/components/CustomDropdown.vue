<template>
  <div class="custom-dropdown" :class="{ 'is-open': isOpen, 'is-disabled': disabled }">
    <div 
      ref="triggerRef"
      class="dropdown-trigger"
      @click="toggleDropdown"
      :class="{ 'has-value': selectedLabel }"
    >
      <span class="dropdown-value">{{ selectedLabel || placeholder }}</span>
      <svg 
        class="dropdown-arrow" 
        width="12" 
        height="12" 
        viewBox="0 0 12 12" 
        fill="none" 
        stroke="currentColor" 
        stroke-width="2"
        :class="{ 'is-open': isOpen }"
      >
        <path d="M3 4.5 L6 7.5 L9 4.5"/>
      </svg>
    </div>
    
    <Transition name="dropdown">
      <div v-if="isOpen" class="dropdown-menu" :style="menuStyle">
        <div class="dropdown-search" v-if="searchable">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search..."
            class="search-input"
            @click.stop
          />
        </div>
        
        <div class="dropdown-options" ref="optionsRef">
          <template v-if="grouped">
            <div 
              v-for="group in filteredGroups" 
              :key="group.key"
              class="dropdown-group"
            >
              <div class="dropdown-group-label">{{ group.label }}</div>
              <div
                v-for="option in group.options"
                :key="getOptionValue(option)"
                class="dropdown-option"
                :class="{ 
                  'is-selected': isSelected(option),
                  'is-disabled': isOptionDisabled(option)
                }"
                @click="selectOption(option)"
              >
                <span class="option-label">{{ getOptionLabel(option) }}</span>
                <span v-if="isSelected(option)" class="option-checkmark">✓</span>
              </div>
            </div>
          </template>
          <template v-else>
            <div
              v-for="option in filteredOptions"
              :key="getOptionValue(option)"
              class="dropdown-option"
              :class="{ 
                'is-selected': isSelected(option),
                'is-disabled': isOptionDisabled(option)
              }"
              @click="selectOption(option)"
            >
              <span class="option-label">{{ getOptionLabel(option) }}</span>
              <span v-if="isSelected(option)" class="option-checkmark">✓</span>
            </div>
          </template>
          
          <div v-if="filteredOptions.length === 0 && filteredGroups.length === 0" class="dropdown-empty">
            No options found
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: null
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'Select an option...'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  searchable: {
    type: Boolean,
    default: false
  },
  optionLabel: {
    type: String,
    default: 'label'
  },
  optionValue: {
    type: String,
    default: 'value'
  },
  grouped: {
    type: Boolean,
    default: false
  },
  groupLabel: {
    type: String,
    default: 'label'
  },
  groupOptions: {
    type: String,
    default: 'options'
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)
const searchQuery = ref('')
const optionsRef = ref(null)
const triggerRef = ref(null)
const menuStyle = ref({})

const selectedOption = computed(() => {
  if (props.grouped) {
    for (const group of props.options) {
      const option = group[props.groupOptions]?.find(opt => getOptionValue(opt) === props.modelValue)
      if (option) return option
    }
    return null
  }
  return props.options.find(opt => getOptionValue(opt) === props.modelValue) || null
})

const selectedLabel = computed(() => {
  if (selectedOption.value) {
    return getOptionLabel(selectedOption.value)
  }
  return null
})

const filteredOptions = computed(() => {
  if (!props.searchable || !searchQuery.value) {
    return props.options
  }
  const query = searchQuery.value.toLowerCase()
  return props.options.filter(opt => {
    const label = getOptionLabel(opt).toLowerCase()
    return label.includes(query)
  })
})

const filteredGroups = computed(() => {
  if (!props.grouped) return []
  
  if (!props.searchable || !searchQuery.value) {
    return props.options.map((group, index) => ({
      key: index,
      label: group[props.groupLabel],
      options: group[props.groupOptions] || []
    }))
  }
  
  const query = searchQuery.value.toLowerCase()
  return props.options
    .map((group, index) => {
      const filtered = (group[props.groupOptions] || []).filter(opt => {
        const label = getOptionLabel(opt).toLowerCase()
        return label.includes(query)
      })
      return filtered.length > 0 ? {
        key: index,
        label: group[props.groupLabel],
        options: filtered
      } : null
    })
    .filter(Boolean)
})

function getOptionLabel(option) {
  if (typeof option === 'string' || typeof option === 'number') {
    return String(option)
  }
  return option[props.optionLabel] || option.label || String(option)
}

function getOptionValue(option) {
  if (typeof option === 'string' || typeof option === 'number') {
    return option
  }
  return option[props.optionValue] || option.value || option.id || option
}

function isSelected(option) {
  return getOptionValue(option) === props.modelValue
}

function isOptionDisabled(option) {
  if (typeof option === 'object' && option !== null) {
    return option.disabled === true
  }
  return false
}

function selectOption(option) {
  if (isOptionDisabled(option)) return
  
  const value = getOptionValue(option)
  emit('update:modelValue', value)
  emit('change', value)
  isOpen.value = false
  searchQuery.value = ''
}

function toggleDropdown() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => {
      positionMenu()
      scrollToSelected()
    })
  }
}

function positionMenu() {
  if (!triggerRef.value) return
  
  // Reset menu style first
    menuStyle.value = {
      top: '100%',
      bottom: 'auto',
      marginTop: '4px'
    }
  
  // Wait for menu to render, then check if we need to flip
  nextTick(() => {
    if (!triggerRef.value || !optionsRef.value) return
    
    const triggerRect = triggerRef.value.getBoundingClientRect()
    const menuRect = optionsRef.value.getBoundingClientRect()
    const viewportHeight = window.innerHeight
    
    const spaceBelow = viewportHeight - triggerRect.bottom
    const spaceAbove = triggerRect.top
    const menuHeight = menuRect.height || 250
    
    // Only position above if there's not enough space below AND more space above
    if (spaceBelow < menuHeight && spaceAbove > spaceBelow) {
      menuStyle.value = {
        bottom: '100%',
        top: 'auto',
        marginBottom: '4px',
        marginTop: '0'
      }
    }
  })
}

function scrollToSelected() {
  if (!optionsRef.value) return
  
  const selected = optionsRef.value.querySelector('.is-selected')
  if (selected) {
    selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }
}

function handleClickOutside(event) {
  const dropdown = event.target.closest('.custom-dropdown')
  if (!dropdown && isOpen.value) {
    isOpen.value = false
    searchQuery.value = ''
  }
}

function handleEscape(event) {
  if (event.key === 'Escape' && isOpen.value) {
    isOpen.value = false
    searchQuery.value = ''
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})

watch(() => props.modelValue, () => {
  if (isOpen.value) {
    nextTick(() => {
      scrollToSelected()
    })
  }
})
</script>

<style scoped>
.custom-dropdown {
  position: relative;
  width: 100%;
}

.dropdown-trigger {
  width: 100%;
  padding: var(--space-2) var(--space-4);
  background: var(--accent);
  border: none;
  border-radius: var(--radius-md);
  color: var(--foreground);
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  transition: all 0.2s;
  user-select: none;
  height: var(--button-sm);
}

.dropdown-trigger:hover:not(.is-disabled) {
  background: var(--accent);
}

.dropdown-trigger.has-value {
  color: var(--foreground);
}

.custom-dropdown.is-open .dropdown-trigger {
  background: var(--accent);
}

.custom-dropdown.is-disabled .dropdown-trigger {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropdown-value {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-arrow {
  flex-shrink: 0;
  transition: transform 0.2s;
  color: var(--muted-foreground);
}

.dropdown-arrow.is-open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--popover, var(--card));
  border: none;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  max-height: 300px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dropdown-search {
  padding: var(--space-3);
}

.search-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--input-background, var(--muted));
  border: none;
  border-radius: var(--radius-sm);
  color: var(--foreground);
  font-size: 12px;
}

.search-input:focus {
  outline: none;
}

.dropdown-options {
  overflow-y: auto;
  padding: var(--space-1);
  max-height: 250px;
}

.dropdown-group {
  margin-bottom: var(--space-4);
}

.dropdown-group:last-child {
  margin-bottom: 0;
}

.dropdown-group-label {
  padding: var(--space-2) var(--space-4);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--muted-foreground);
  letter-spacing: 0.5px;
  margin-bottom: var(--space-2);
  background: var(--muted);
  width: 100%;
  display: block;
}

.dropdown-option {
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  border-radius: var(--radius-sm);
  transition: background-color 0.15s;
  font-size: 12px;
  color: var(--foreground);
}

.dropdown-option:hover:not(.is-disabled) {
  background: var(--accent);
}

.dropdown-option.is-selected {
  /* No background highlight - only show checkmark */
}

.dropdown-option.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.option-label {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.option-checkmark {
  flex-shrink: 0;
  font-weight: bold;
  font-size: 16px;
}

.dropdown-empty {
  padding: var(--space-4);
  text-align: center;
  color: var(--muted-foreground);
  font-size: 12px;
}

/* Transitions */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.dropdown-enter-from {
  opacity: 0;
    transform: translateY(calc(-1 * var(--space-2))) scale(0.98);
}

.dropdown-leave-to {
  opacity: 0;
    transform: translateY(calc(-1 * var(--space-2))) scale(0.98);
}
</style>

