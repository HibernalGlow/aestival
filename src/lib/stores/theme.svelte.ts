/**
 * AestivalFlow - 主题系统
 * 支持明暗模式切换和从 tweakcn.com 导入主题 JSON
 */
import { writable, get } from 'svelte/store';

export type ThemeMode = 'light' | 'dark' | 'system';

export interface ThemeColors {
  [key: string]: string;
}

export interface TweakcnTheme {
  name: string;
  cssVars: {
    light: ThemeColors;
    dark: ThemeColors;
    theme?: ThemeColors;
  };
}

export interface ThemeState {
  mode: ThemeMode;
  themeName: string;
  themes: {
    light: ThemeColors;
    dark: ThemeColors;
  };
  showImportDialog: boolean;
}

// 默认主题颜色（shadcn 默认）
const DEFAULT_LIGHT: ThemeColors = {
  'background': '0 0% 100%',
  'foreground': '240 10% 3.9%',
  'card': '0 0% 100%',
  'card-foreground': '240 10% 3.9%',
  'popover': '0 0% 100%',
  'popover-foreground': '240 10% 3.9%',
  'primary': '240 5.9% 10%',
  'primary-foreground': '0 0% 98%',
  'secondary': '240 4.8% 95.9%',
  'secondary-foreground': '240 5.9% 10%',
  'muted': '240 4.8% 95.9%',
  'muted-foreground': '240 3.8% 46.1%',
  'accent': '240 4.8% 95.9%',
  'accent-foreground': '240 5.9% 10%',
  'destructive': '0 84.2% 60.2%',
  'destructive-foreground': '0 0% 98%',
  'border': '240 5.9% 90%',
  'input': '240 5.9% 90%',
  'ring': '240 5.9% 10%',
};

const DEFAULT_DARK: ThemeColors = {
  'background': '240 10% 3.9%',
  'foreground': '0 0% 98%',
  'card': '240 10% 3.9%',
  'card-foreground': '0 0% 98%',
  'popover': '240 10% 3.9%',
  'popover-foreground': '0 0% 98%',
  'primary': '0 0% 98%',
  'primary-foreground': '240 5.9% 10%',
  'secondary': '240 3.7% 15.9%',
  'secondary-foreground': '0 0% 98%',
  'muted': '240 3.7% 15.9%',
  'muted-foreground': '240 5% 64.9%',
  'accent': '240 3.7% 15.9%',
  'accent-foreground': '0 0% 98%',
  'destructive': '0 62.8% 30.6%',
  'destructive-foreground': '0 0% 98%',
  'border': '240 3.7% 15.9%',
  'input': '240 3.7% 15.9%',
  'ring': '240 4.9% 83.9%',
};

// 从 localStorage 加载主题
function loadThemeFromStorage(): ThemeState {
  if (typeof window === 'undefined') {
    return {
      mode: 'system',
      themeName: 'default',
      themes: { light: DEFAULT_LIGHT, dark: DEFAULT_DARK },
      showImportDialog: false,
    };
  }

  try {
    const stored = localStorage.getItem('aestival-theme');
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        mode: parsed.mode || 'system',
        themeName: parsed.themeName || 'default',
        themes: {
          light: parsed.themes?.light || DEFAULT_LIGHT,
          dark: parsed.themes?.dark || DEFAULT_DARK,
        },
        showImportDialog: false,
      };
    }
  } catch {
    // 忽略解析错误
  }

  return {
    mode: 'system',
    themeName: 'default',
    themes: { light: DEFAULT_LIGHT, dark: DEFAULT_DARK },
    showImportDialog: false,
  };
}

// 保存主题到 localStorage
function saveThemeToStorage(state: ThemeState) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem('aestival-theme', JSON.stringify({
      mode: state.mode,
      themeName: state.themeName,
      themes: state.themes,
    }));
  } catch {
    // 忽略存储错误
  }
}

// 应用主题到 DOM
function applyThemeToDOM(state: ThemeState) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  
  // 确定是否使用暗色模式
  const systemPrefersDark = typeof window !== 'undefined' && 
    window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const isDark = state.mode === 'dark' || (state.mode === 'system' && systemPrefersDark);

  // 设置 dark class
  if (isDark) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }

  // 应用 CSS 变量
  const colors = isDark ? state.themes.dark : state.themes.light;
  for (const [key, value] of Object.entries(colors)) {
    root.style.setProperty(`--${key}`, value);
  }
}

// 创建主题 store
function createThemeStore() {
  const initial = loadThemeFromStorage();
  const { subscribe, set, update } = writable<ThemeState>(initial);

  // 初始化时应用主题
  if (typeof window !== 'undefined') {
    applyThemeToDOM(initial);
    
    // 监听系统主题变化
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    mq?.addEventListener('change', () => {
      const current = get({ subscribe });
      if (current.mode === 'system') {
        applyThemeToDOM(current);
      }
    });
  }

  return {
    subscribe,
    setMode: (mode: ThemeMode) => {
      update(state => {
        const newState = { ...state, mode };
        saveThemeToStorage(newState);
        applyThemeToDOM(newState);
        return newState;
      });
    },
    importTheme: (theme: TweakcnTheme) => {
      update(state => {
        const newState = {
          ...state,
          themeName: theme.name,
          themes: {
            light: theme.cssVars.light,
            dark: theme.cssVars.dark,
          },
          showImportDialog: false,
        };
        saveThemeToStorage(newState);
        applyThemeToDOM(newState);
        return newState;
      });
    },
    importFromJSON: (jsonString: string) => {
      try {
        const theme = JSON.parse(jsonString) as TweakcnTheme;
        if (!theme.cssVars?.light || !theme.cssVars?.dark) {
          throw new Error('Invalid theme format');
        }
        update(state => {
          const newState = {
            ...state,
            themeName: theme.name || 'imported',
            themes: {
              light: theme.cssVars.light,
              dark: theme.cssVars.dark,
            },
            showImportDialog: false,
          };
          saveThemeToStorage(newState);
          applyThemeToDOM(newState);
          return newState;
        });
        return true;
      } catch (e) {
        console.error('Failed to import theme:', e);
        return false;
      }
    },
    resetToDefault: () => {
      update(state => {
        const newState = {
          ...state,
          themeName: 'default',
          themes: { light: DEFAULT_LIGHT, dark: DEFAULT_DARK },
        };
        saveThemeToStorage(newState);
        applyThemeToDOM(newState);
        return newState;
      });
    },
    openImportDialog: () => {
      update(state => ({ ...state, showImportDialog: true }));
    },
    closeImportDialog: () => {
      update(state => ({ ...state, showImportDialog: false }));
    },
  };
}

export const themeStore = createThemeStore();

// 便捷函数
export function toggleThemeMode() {
  const current = get(themeStore);
  const next: ThemeMode = current.mode === 'light' ? 'dark' : current.mode === 'dark' ? 'system' : 'light';
  themeStore.setMode(next);
}

export function openThemeImport() {
  themeStore.openImportDialog();
}

export function closeThemeImport() {
  themeStore.closeImportDialog();
}
