import { ref, onMounted } from 'vue';

export function useWindowControls() {
  const isMaximized = ref(false);

  const checkMaximized = async () => {
    if (window.electronAPI) {
      isMaximized.value = await window.electronAPI.windowIsMaximized();
    }
  };

  onMounted(() => {
    checkMaximized();
  });

  const minimize = () => {
    window.electronAPI?.windowMinimize();
  };

  const toggleMaximize = async () => {
    if (window.electronAPI) {
      isMaximized.value = await window.electronAPI.windowMaximize();
    }
  };

  const close = () => {
    window.electronAPI?.windowClose();
  };

  return {
    minimize,
    toggleMaximize,
    close,
    isMaximized,
  };
}









































