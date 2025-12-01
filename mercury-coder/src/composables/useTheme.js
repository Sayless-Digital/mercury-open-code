import { ref, watch } from 'vue';

const isDark = ref(false);
const THEME_KEY = 'mercury-coder-theme';

// Apply theme to document
const applyTheme = () => {
  if (typeof document !== 'undefined') {
    const root = document.documentElement;
    if (isDark.value) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }
};

// Initialize theme from localStorage or default to dark
const initTheme = () => {
  if (typeof window !== 'undefined') {
    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme) {
      isDark.value = savedTheme === 'dark';
    } else {
      // Default to dark mode
      isDark.value = true;
    }
    applyTheme();
  }
};

// Toggle theme
const toggleTheme = () => {
  isDark.value = !isDark.value;
  if (typeof window !== 'undefined') {
    localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light');
  }
  applyTheme();
};

// Set theme explicitly
const setTheme = (dark) => {
  isDark.value = dark;
  if (typeof window !== 'undefined') {
    localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light');
  }
  applyTheme();
};

// Watch for changes and apply
watch(isDark, () => {
  applyTheme();
}, { immediate: false });

// Initialize immediately when module loads
if (typeof window !== 'undefined') {
  initTheme();
}

export function useTheme() {
  // Ensure theme is applied when composable is used
  if (typeof document !== 'undefined') {
    applyTheme();
  }
  
  return {
    isDark,
    toggleTheme,
    setTheme,
  };
}

