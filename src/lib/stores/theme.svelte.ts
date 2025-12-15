/**
 * AestivalFlow - 主题系统
 * 参考 neoview 实现，支持明暗模式切换和主题导入
 */
import { writable, get } from 'svelte/store';

export type ThemeMode = 'light' | 'dark' | 'system';

export interface ThemeColors {
  [key: string]: string;
}

export interface ThemeConfig {
  name: string;
  description: string;
  colors: {
    light: ThemeColors;
    dark: ThemeColors;
  };
}

export interface ThemeState {
  mode: ThemeMode;
  themeName: string;
  systemPrefersDark: boolean;
  showImportDialog: boolean;
}

// 预设主题
export const presetThemes: ThemeConfig[] = [
  {
    name: 'Default',
    description: '默认主题',
    colors: {
      light: {
        'background': 'oklch(1 0 0)',
        'foreground': 'oklch(0.145 0 0)',
        'card': 'oklch(1 0 0)',
        'card-foreground': 'oklch(0.145 0 0)',
        'primary': 'oklch(0.205 0 0)',
        'primary-foreground': 'oklch(0.985 0 0)',
        'secondary': 'oklch(0.97 0 0)',
        'secondary-foreground': 'oklch(0.205 0 0)',
        'muted': 'oklch(0.97 0 0)',
        'muted-foreground': 'oklch(0.556 0 0)',
        'accent': 'oklch(0.97 0 0)',
        'accent-foreground': 'oklch(0.205 0 0)',
        'destructive': 'oklch(0.577 0.245 27.325)',
        'border': 'oklch(0.922 0 0)',
        'input': 'oklch(0.922 0 0)',
        'ring': 'oklch(0.708 0 0)',
      },
      dark: {
        'background': 'oklch(0.145 0 0)',
        'foreground': 'oklch(0.985 0 0)',
        'card': 'oklch(0.205 0 0)',
        'card-foreground': 'oklch(0.985 0 0)',
        'primary': 'oklch(0.922 0 0)',
        'primary-foreground': 'oklch(0.205 0 0)',
        'secondary': 'oklch(0.269 0 0)',
        'secondary-foreground': 'oklch(0.985 0 0)',
        'muted': 'oklch(0.269 0 0)',
        'muted-foreground': 'oklch(0.708 0 0)',
        'accent': 'oklch(0.269 0 0)',
        'accent-foreground': 'oklch(0.985 0 0)',
        'destructive': 'oklch(0.704 0.191 22.216)',
        'border': 'oklch(1 0 0 / 10%)',
        'input': 'oklch(1 0 0 / 15%)',
        'ring': 'oklch(0.556 0 0)',
      }
    }
  },
  {
    name: 'Ocean',
    description: '海洋蓝主题',
    colors: {
      light: {
        'primary': 'oklch(0.55 0.18 240)',
        'background': 'oklch(0.98 0.004 240)',
      },
      dark: {
        'primary': 'oklch(0.71 0.16 240)',
        'background': 'oklch(0.22 0.02 240)',
      }
    }
  },
  {
    name: 'Forest',
    description: '森林绿主题',
    colors: {
      light: {
        'primary': 'oklch(0.55 0.18 140)',
        'background': 'oklch(0.98 0.004 140)',
      },
      dark: {
        'primary': 'oklch(0.71 0.16 140)',
        'background': 'oklch(0.22 0.02 140)',
      }
    }
  }
];

// 从 localStorage 加载
function loadFromStorage(): { mode: ThemeMode; themeName: string; customThemes: ThemeConfig[] } {
  if (typeof window === 'undefined') {
    return { mode: 'system', themeName: 'Default', customThemes: [] };
  }
  try {
    const mode = (localStorage.getItem('theme-mode') as ThemeMode) || 'system';
    const themeName = localStorage.getItem('theme-name') || 'Default';
    const rawCustom = localStorage.getItem('custom-themes');
    const customThemes = rawCustom ? JSON.parse(rawCustom) : [];
    return { mode, themeName, customThemes };
  } catch {
    return { mode: 'system', themeName: 'Default', customThemes: [] };
  }
}

// 保存到 localStorage
function saveToStorage(mode: ThemeMode, themeName: string) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem('theme-mode', mode);
    localStorage.setItem('theme-name', themeName);
  } catch {}
}

// 应用主题到 DOM
function applyThemeToDOM(mode: ThemeMode, theme: ThemeConfig, systemPrefersDark: boolean) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  const isDark = mode === 'dark' || (mode === 'system' && systemPrefersDark);

  // 设置 dark class
  if (isDark) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }

  // 应用颜色变量
  const colors = isDark ? theme.colors.dark : theme.colors.light;
  for (const [key, value] of Object.entries(colors)) {
    if (typeof value === 'string') {
      root.style.setProperty(`--${key}`, value);
    }
  }
}

// 查找主题
function findTheme(name: string, customThemes: ThemeConfig[]): ThemeConfig {
  return presetThemes.find(t => t.name === name) 
    || customThemes.find(t => t.name === name) 
    || presetThemes[0];
}

// 创建主题 store
function createThemeStore() {
  const { mode: initialMode, themeName: initialThemeName, customThemes: initialCustomThemes } = loadFromStorage();
  const systemPrefersDark = typeof window !== 'undefined' 
    ? window.matchMedia?.('(prefers-color-scheme: dark)').matches 
    : false;

  const { subscribe, update } = writable<ThemeState>({
    mode: initialMode,
    themeName: initialThemeName,
    systemPrefersDark,
    showImportDialog: false,
  });

  let customThemes = initialCustomThemes;
  let currentTheme = findTheme(initialThemeName, customThemes);

  // 初始化时应用主题
  if (typeof window !== 'undefined') {
    applyThemeToDOM(initialMode, currentTheme, systemPrefersDark);

    // 监听系统主题变化
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    mq?.addEventListener('change', (e) => {
      update(state => {
        const newState = { ...state, systemPrefersDark: e.matches };
        if (state.mode === 'system') {
          applyThemeToDOM('system', currentTheme, e.matches);
        }
        return newState;
      });
    });
  }

  return {
    subscribe,
    
    setMode: (mode: ThemeMode) => {
      update(state => {
        saveToStorage(mode, state.themeName);
        applyThemeToDOM(mode, currentTheme, state.systemPrefersDark);
        return { ...state, mode };
      });
    },

    setTheme: (themeName: string) => {
      currentTheme = findTheme(themeName, customThemes);
      update(state => {
        saveToStorage(state.mode, themeName);
        applyThemeToDOM(state.mode, currentTheme, state.systemPrefersDark);
        return { ...state, themeName };
      });
    },

    importThemeJSON: (jsonString: string): boolean => {
      try {
        const parsed = JSON.parse(jsonString);
        if (parsed.cssVars?.light) {
          const base = parsed.cssVars.theme ?? {};
          const light = { ...base, ...parsed.cssVars.light };
          const dark = { ...base, ...(parsed.cssVars.dark ?? parsed.cssVars.light) };
          const newTheme: ThemeConfig = {
            name: parsed.name || 'Imported',
            description: '导入的主题',
            colors: { light, dark }
          };
          customThemes = [...customThemes.filter(t => t.name !== newTheme.name), newTheme];
          localStorage.setItem('custom-themes', JSON.stringify(customThemes));
          currentTheme = newTheme;
          update(state => {
            saveToStorage(state.mode, newTheme.name);
            applyThemeToDOM(state.mode, currentTheme, state.systemPrefersDark);
            return { ...state, themeName: newTheme.name, showImportDialog: false };
          });
          return true;
        }
        return false;
      } catch {
        return false;
      }
    },

    getCustomThemes: () => customThemes,
    
    openImportDialog: () => update(state => ({ ...state, showImportDialog: true })),
    closeImportDialog: () => update(state => ({ ...state, showImportDialog: false })),
  };
}

export const themeStore = createThemeStore();

// 便捷函数：循环切换主题模式
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
