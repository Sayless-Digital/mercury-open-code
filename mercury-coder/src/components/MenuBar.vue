<template>
  <div class="menu-bar" ref="menuBarRef">
    <div class="menu-item" v-for="menu in menus" :key="menu.label">
      <button class="menu-button" @click="(e) => toggleMenu(menu.label, e)">
        <component v-if="menu.icon" :is="menu.icon" class="menu-button-icon" :size="14" />
        <span>{{ menu.label }}</span>
      </button>
      <div v-if="activeMenu === menu.label" class="menu-dropdown" :data-menu="menu.label" @click.stop>
        <div
          v-for="item in menu.items"
          :key="item.label"
          class="menu-dropdown-item"
          :class="{ disabled: item.disabled, separator: item.separator, hasSubmenu: item.submenu }"
          @mouseenter="(e) => handleItemHover(item, e)"
          @mouseleave="(e) => handleItemLeave(item, e)"
          @click="(e) => handleMenuClick(item, e)"
        >
          <div v-if="!item.separator" class="menu-item-content">
            <component v-if="item.icon" :is="item.icon" class="menu-item-icon" :size="14" />
            <span class="menu-item-label">{{ item.label }}</span>
            <component v-if="item.submenu" :is="ChevronRight" class="submenu-arrow" :size="12" />
          </div>
          <span v-if="item.shortcut && !item.submenu" class="menu-shortcut">{{ item.shortcut }}</span>
          <!-- Submenu -->
          <div 
            v-if="item.submenu && hoveredSubmenu === item.label"
            class="submenu" 
            @click.stop
            @mouseenter="handleSubmenuEnter(item)"
            @mouseleave="handleSubmenuLeave"
          >
            <div
              v-for="subItem in item.submenu"
              :key="subItem.label"
              class="menu-dropdown-item"
              :class="{ disabled: subItem.disabled, separator: subItem.separator }"
              @click="(e) => handleMenuClick(subItem, e)"
            >
              <div v-if="!subItem.separator" class="menu-item-content">
                <component v-if="subItem.icon" :is="subItem.icon" class="menu-item-icon" :size="14" />
                <span class="menu-item-label">{{ subItem.label }}</span>
              </div>
              <span v-if="subItem.shortcut" class="menu-shortcut">{{ subItem.shortcut }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { ChevronRight } from 'lucide-vue-next';

const props = defineProps({
  menus: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(['menu-click']);

const activeMenu = ref(null);
const menuBarRef = ref(null);
const hoveredSubmenu = ref(null);

const toggleMenu = (menuLabel, event) => {
  if (event) {
    event.stopPropagation();
  }
  activeMenu.value = activeMenu.value === menuLabel ? null : menuLabel;
};

const handleItemHover = (item, event) => {
  if (item.submenu) {
    hoveredSubmenu.value = item.label;
  } else {
    // Only clear if we're not hovering over another submenu item
    if (hoveredSubmenu.value !== item.label) {
      hoveredSubmenu.value = null;
    }
  }
};

const handleItemLeave = (item, event) => {
  // Check if we're moving to the submenu
  const relatedTarget = event.relatedTarget;
  if (relatedTarget && relatedTarget.closest('.submenu')) {
    return; // Moving to submenu, keep it open
  }
  // Close submenu after a small delay to allow moving to submenu
  setTimeout(() => {
    // Check if mouse is still over the item or submenu
    const hoveredSubmenuElement = document.querySelector('.submenu:hover');
    const hoveredItemElement = document.querySelector('.menu-dropdown-item.hasSubmenu:hover');
    if (!hoveredSubmenuElement && !hoveredItemElement && hoveredSubmenu.value === item.label) {
      hoveredSubmenu.value = null;
    }
  }, 150);
};

const handleSubmenuEnter = (item) => {
  hoveredSubmenu.value = item.label;
};

const handleSubmenuLeave = () => {
  setTimeout(() => {
    const hoveredSubmenuElement = document.querySelector('.submenu:hover');
    const hoveredItemElement = document.querySelector('.menu-dropdown-item.hasSubmenu:hover');
    if (!hoveredSubmenuElement && !hoveredItemElement) {
      hoveredSubmenu.value = null;
    }
  }, 150);
};

const handleMenuClick = (item, event) => {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  // If item has submenu, toggle it open/closed
  if (item.submenu) {
    const wasOpen = hoveredSubmenu.value === item.label;
    hoveredSubmenu.value = wasOpen ? null : item.label;
    return;
  }
  if (item.disabled || item.separator) return;
  
  activeMenu.value = null;
  hoveredSubmenu.value = null;
  emit('menu-click', item);
};

const closeMenus = (event) => {
  // Don't close if clicking inside the menu bar or on a menu button
  if (!event) {
    activeMenu.value = null;
    hoveredSubmenu.value = null;
    return;
  }
  
  const target = event.target;
  if (!target) {
    activeMenu.value = null;
    hoveredSubmenu.value = null;
    return;
  }
  
  // Check if click is on menu button or inside dropdown or submenu
  const isMenuButton = target.closest('.menu-button');
  const isInDropdown = target.closest('.menu-dropdown');
  const isInSubmenu = target.closest('.submenu');
  const isInMenuBar = menuBarRef.value && menuBarRef.value.contains(target);
  const isSubmenuItem = target.closest('.menu-dropdown-item.hasSubmenu');
  
  if (isMenuButton || isInDropdown || isInSubmenu || isInMenuBar || isSubmenuItem) {
    return;
  }
  
  activeMenu.value = null;
  hoveredSubmenu.value = null;
};

onMounted(() => {
  // Use a small delay to prevent immediate closure when clicking menu button
  requestAnimationFrame(() => {
    document.addEventListener('click', closeMenus);
  });
});

onUnmounted(() => {
  document.removeEventListener('click', closeMenus);
});
</script>

<style scoped>
.menu-bar {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
  margin-left: var(--space-6);
  -webkit-app-region: no-drag;
}

.menu-item {
  position: relative;
}

.menu-button {
  background: none;
  border: none;
  color: var(--foreground);
  padding: var(--space-2) var(--space-6);
  font-size: 12px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.menu-button-icon {
  flex-shrink: 0;
  opacity: 0.8;
}

.menu-button:hover {
  background: var(--accent);
}

.menu-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  background: var(--card);
  border: none;
  border-radius: var(--radius-xl);
  min-width: 200px;
  box-shadow: var(--shadow-2xl);
  z-index: 10000;
  padding: var(--space-3) 0;
  margin-top: var(--space-2);
  overflow: visible;
}

.menu-dropdown[data-menu="File"] {
  min-width: 240px;
}

.menu-dropdown[data-menu="View"] {
  min-width: 280px;
}

.menu-dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-6);
  font-size: 12px;
  color: var(--foreground);
  cursor: pointer;
  transition: background-color 0.15s;
  gap: var(--space-4);
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
}

.menu-item-icon {
  flex-shrink: 0;
  opacity: 0.7;
}

.menu-item-label {
  flex: 1;
}

.menu-dropdown-item:hover:not(.disabled):not(.separator) {
  background: var(--accent);
}

.menu-dropdown-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.menu-dropdown-item.separator {
  height: 1px;
  background: transparent;
  margin: var(--space-2) 0;
  padding: 0;
  cursor: default;
}

.menu-shortcut {
  margin-left: var(--space-12);
  color: var(--muted-foreground);
  font-size: 11px;
}

.menu-dropdown-item.hasSubmenu {
  position: relative;
}

.submenu-arrow {
  margin-left: auto;
  opacity: 0.6;
}

.submenu {
  position: absolute;
  left: calc(100% + var(--space-2));
  top: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  min-width: 200px;
  box-shadow: var(--shadow-2xl);
  z-index: 10001;
  padding: var(--space-3) 0;
  overflow: visible;
}

/* Bridge gap between menu item and submenu */
.menu-dropdown-item.hasSubmenu::after {
  content: '';
  position: absolute;
  right: calc(-1 * var(--space-2));
  top: 0;
  bottom: 0;
  width: var(--space-4);
  z-index: 10000;
}
</style>

