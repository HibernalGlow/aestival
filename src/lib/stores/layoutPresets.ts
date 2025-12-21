/**
 * 布局预设管理
 * 支持保存、加载、导出布局配置
 */
import type { GridItem } from '$lib/components/ui/dashboard-grid';

// localStorage key
const PRESETS_KEY = 'aestival-layout-presets';
const DEFAULT_PRESET_KEY = 'aestival-default-preset';  // 存储每个 nodeType 的默认预设 ID（按模式分开）

/** 布局模式类型 */
export type PresetMode = 'fullscreen' | 'normal';

/** 默认预设配置结构 */
interface DefaultPresetConfig {
  fullscreen?: string;  // 全屏模式默认预设 ID
  normal?: string;      // 节点模式默认预设 ID
}

/** Tab 分组配置（与 nodeLayoutStore 中的 TabGroup 保持一致） */
export interface PresetTabGroup {
  id: string;
  blockIds: string[];
  activeIndex: number;
}

/** 布局预设 */
export interface LayoutPreset {
  id: string;
  name: string;
  nodeType: string;  // 适用的节点类型，如 'trename', 'repacku'
  layout: GridItem[];
  tabGroups?: PresetTabGroup[];  // Tab 分组配置（可选，兼容旧预设）
  createdAt: number;
  isBuiltin?: boolean;  // 是否为内置预设
}

/** 内置预设 */
const BUILTIN_PRESETS: LayoutPreset[] = [
  // ========== TrenameNode 预设 ==========
  {
    id: 'trename-default',
    name: '默认布局',
    nodeType: 'trename',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'importExport', x: 0, y: 2, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 3, w: 3, h: 4, minW: 2, minH: 2 },
      { id: 'log', x: 3, y: 2, w: 1, h: 5, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'trename-compact',
    name: '紧凑布局',
    nodeType: 'trename',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 1, minW: 1, minH: 1 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 1, minW: 1, minH: 1 },
      { id: 'importExport', x: 0, y: 1, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 2, w: 2, h: 3, minW: 2, minH: 2 },
      { id: 'log', x: 2, y: 1, w: 2, h: 4, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'trename-tree-focus',
    name: '文件树优先',
    nodeType: 'trename',
    layout: [
      { id: 'tree', x: 0, y: 0, w: 3, h: 6, minW: 2, minH: 2 },
      { id: 'path', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'operation', x: 3, y: 2, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 4, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'importExport', x: 0, y: 6, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'log', x: 2, y: 6, w: 2, h: 1, minW: 1, minH: 1 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  // ========== RepackuNode 预设 ==========
  {
    id: 'repacku-default',
    name: '默认布局',
    nodeType: 'repacku',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 3, minW: 2, minH: 2 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'progress', x: 2, y: 2, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 3, w: 3, h: 4, minW: 2, minH: 2 },
      { id: 'log', x: 3, y: 3, w: 1, h: 4, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'repacku-compact',
    name: '紧凑布局',
    nodeType: 'repacku',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
      { id: 'progress', x: 0, y: 2, w: 4, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 3, w: 2, h: 3, minW: 2, minH: 2 },
      { id: 'log', x: 2, y: 3, w: 2, h: 3, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'repacku-tree-focus',
    name: '文件树优先',
    nodeType: 'repacku',
    layout: [
      { id: 'tree', x: 0, y: 0, w: 3, h: 6, minW: 2, minH: 2 },
      { id: 'path', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'operation', x: 3, y: 2, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 4, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'progress', x: 0, y: 6, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'log', x: 2, y: 6, w: 2, h: 1, minW: 1, minH: 1 }
    ],
    createdAt: 0,
    isBuiltin: true
  }
];

/** 从 localStorage 加载用户预设 */
function loadUserPresets(): LayoutPreset[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(PRESETS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

/** 估算数据大小（字节） */
function estimateSize(data: unknown): number {
  return JSON.stringify(data).length * 2; // UTF-16
}

/** 清理旧预设，保留最近的 N 个 */
function cleanupOldPresets(presets: LayoutPreset[], maxCount: number = 20): LayoutPreset[] {
  if (presets.length <= maxCount) return presets;
  
  // 按创建时间排序，保留最新的
  const sorted = [...presets].sort((a, b) => b.createdAt - a.createdAt);
  const removed = sorted.slice(maxCount);
  
  if (removed.length > 0) {
    console.log(`[layoutPresets] 清理 ${removed.length} 个旧预设:`, removed.map(p => p.name));
  }
  
  return sorted.slice(0, maxCount);
}

/** 保存用户预设到 localStorage */
function saveUserPresets(presets: LayoutPreset[]): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn('[layoutPresets] localStorage 配额已满，尝试清理...');
      
      // 清理旧预设
      const cleaned = cleanupOldPresets(presets, 10);
      
      try {
        localStorage.setItem(PRESETS_KEY, JSON.stringify(cleaned));
        console.log('[layoutPresets] 清理后保存成功');
      } catch (e2) {
        console.error('[layoutPresets] 清理后仍无法保存，只保留最新 5 个');
        const minimal = cleanupOldPresets(presets, 5);
        try {
          localStorage.setItem(PRESETS_KEY, JSON.stringify(minimal));
        } catch {
          console.error('[layoutPresets] 无法保存预设');
        }
      }
    } else {
      console.warn('[layoutPresets] Failed to save:', e);
    }
  }
}

/** 获取所有预设（内置 + 用户） */
export function getAllPresets(nodeType?: string): LayoutPreset[] {
  const userPresets = loadUserPresets();
  const all = [...BUILTIN_PRESETS, ...userPresets];
  return nodeType ? all.filter(p => p.nodeType === nodeType) : all;
}

/** 获取单个预设 */
export function getPreset(id: string): LayoutPreset | undefined {
  return getAllPresets().find(p => p.id === id);
}

/** 保存新预设（包含 Tab 分组） */
export function savePreset(
  name: string, 
  nodeType: string, 
  layout: GridItem[], 
  tabGroups?: PresetTabGroup[]
): LayoutPreset {
  const preset: LayoutPreset = {
    id: `${nodeType}-${Date.now()}`,
    name,
    nodeType,
    layout: JSON.parse(JSON.stringify(layout)), // 深拷贝
    tabGroups: tabGroups ? JSON.parse(JSON.stringify(tabGroups)) : undefined,
    createdAt: Date.now()
  };
  const userPresets = loadUserPresets();
  userPresets.push(preset);
  saveUserPresets(userPresets);
  return preset;
}

/** 删除用户预设 */
export function deletePreset(id: string): boolean {
  const userPresets = loadUserPresets();
  const index = userPresets.findIndex(p => p.id === id);
  if (index === -1) return false;
  userPresets.splice(index, 1);
  saveUserPresets(userPresets);
  return true;
}

/** 重命名用户预设 */
export function renamePreset(id: string, newName: string): boolean {
  const userPresets = loadUserPresets();
  const preset = userPresets.find(p => p.id === id);
  if (!preset) return false;
  preset.name = newName;
  saveUserPresets(userPresets);
  return true;
}

/** 更新用户预设的布局（覆盖，包含 Tab 分组） */
export function updatePreset(id: string, layout: GridItem[], tabGroups?: PresetTabGroup[]): boolean {
  const userPresets = loadUserPresets();
  const preset = userPresets.find(p => p.id === id);
  if (!preset) return false;
  preset.layout = JSON.parse(JSON.stringify(layout)); // 深拷贝
  preset.tabGroups = tabGroups ? JSON.parse(JSON.stringify(tabGroups)) : undefined;
  saveUserPresets(userPresets);
  return true;
}

/** 导出预设为 JSON 字符串 */
export function exportPreset(id: string): string | null {
  const preset = getPreset(id);
  if (!preset) return null;
  return JSON.stringify(preset, null, 2);
}

/** 导入预设 */
export function importPreset(json: string): LayoutPreset | null {
  try {
    const preset = JSON.parse(json) as LayoutPreset;
    if (!preset.name || !preset.nodeType || !Array.isArray(preset.layout)) {
      return null;
    }
    // 生成新 ID 避免冲突
    preset.id = `${preset.nodeType}-imported-${Date.now()}`;
    preset.createdAt = Date.now();
    preset.isBuiltin = false;
    
    const userPresets = loadUserPresets();
    userPresets.push(preset);
    saveUserPresets(userPresets);
    return preset;
  } catch {
    return null;
  }
}

/** 加载默认预设配置（新格式：按模式分开） */
function loadDefaultPresets(): Record<string, DefaultPresetConfig> {
  if (typeof window === 'undefined') return {};
  try {
    const stored = localStorage.getItem(DEFAULT_PRESET_KEY);
    if (!stored) return {};
    const parsed = JSON.parse(stored);
    
    // 兼容旧格式：如果值是字符串，转换为新格式
    const result: Record<string, DefaultPresetConfig> = {};
    for (const [nodeType, value] of Object.entries(parsed)) {
      if (typeof value === 'string') {
        // 旧格式：单个预设 ID，同时设为两种模式的默认
        result[nodeType] = { fullscreen: value, normal: value };
      } else if (typeof value === 'object' && value !== null) {
        // 新格式
        result[nodeType] = value as DefaultPresetConfig;
      }
    }
    return result;
  } catch {
    return {};
  }
}

/** 保存默认预设配置 */
function saveDefaultPresets(defaults: Record<string, DefaultPresetConfig>): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(DEFAULT_PRESET_KEY, JSON.stringify(defaults));
  } catch (e) {
    console.warn('[layoutPresets] Failed to save defaults:', e);
  }
}

/** 设置默认预设（指定模式） */
export function setDefaultPreset(nodeType: string, presetId: string, mode: PresetMode): void {
  const defaults = loadDefaultPresets();
  if (!defaults[nodeType]) {
    defaults[nodeType] = {};
  }
  defaults[nodeType][mode] = presetId;
  saveDefaultPresets(defaults);
}

/** 取消默认预设（指定模式） */
export function unsetDefaultPreset(nodeType: string, mode: PresetMode): void {
  const defaults = loadDefaultPresets();
  if (defaults[nodeType]) {
    delete defaults[nodeType][mode];
    // 如果两种模式都没有默认了，删除整个 nodeType 条目
    if (!defaults[nodeType].fullscreen && !defaults[nodeType].normal) {
      delete defaults[nodeType];
    }
    saveDefaultPresets(defaults);
  }
}

/** 获取默认预设 ID（指定模式） */
export function getDefaultPresetId(nodeType: string, mode?: PresetMode): string | null {
  const defaults = loadDefaultPresets();
  const config = defaults[nodeType];
  if (!config) return null;
  
  // 如果指定了模式，返回该模式的默认
  if (mode) {
    return config[mode] || null;
  }
  
  // 未指定模式时，优先返回 fullscreen，兼容旧代码
  return config.fullscreen || config.normal || null;
}

/** 获取预设的默认模式列表（用于显示圆点指示器） */
export function getPresetDefaultModes(nodeType: string, presetId: string): PresetMode[] {
  const defaults = loadDefaultPresets();
  const config = defaults[nodeType];
  if (!config) return [];
  
  const modes: PresetMode[] = [];
  if (config.fullscreen === presetId) modes.push('fullscreen');
  if (config.normal === presetId) modes.push('normal');
  return modes;
}

/** 获取默认预设（如果没有设置，返回第一个内置预设） */
export function getDefaultPreset(nodeType: string, mode?: PresetMode): LayoutPreset | null {
  const defaultId = getDefaultPresetId(nodeType, mode);
  if (defaultId) {
    const preset = getPreset(defaultId);
    if (preset) return preset;
  }
  // 返回第一个内置预设作为默认
  const builtinPreset = BUILTIN_PRESETS.find(p => p.nodeType === nodeType);
  return builtinPreset || null;
}

// ============ 存储管理 ============

/** 获取用户预设数量和大小 */
export function getPresetsInfo(): { count: number; sizeKB: number } {
  const presets = loadUserPresets();
  const size = estimateSize(presets);
  return {
    count: presets.length,
    sizeKB: Math.round(size / 1024)
  };
}

/** 清理所有用户预设 */
export function clearAllUserPresets(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(PRESETS_KEY);
  console.log('[layoutPresets] 已清理所有用户预设');
}

/** 清理指定节点类型的用户预设 */
export function clearPresetsForNodeType(nodeType: string): number {
  const presets = loadUserPresets();
  const filtered = presets.filter(p => p.nodeType !== nodeType);
  const removed = presets.length - filtered.length;
  
  if (removed > 0) {
    saveUserPresets(filtered);
    console.log(`[layoutPresets] 清理了 ${removed} 个 ${nodeType} 预设`);
  }
  
  return removed;
}
