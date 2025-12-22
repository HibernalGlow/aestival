/**
 * 节点布局状态存储 - 统一管理节点的所有配置
 * 
 * 存储后端：使用 SQLModel + SQLite 后端存储（通过 storageClient）
 * 
 * Tab 分组采用"虚拟分组"模式：
 * - 区块始终保留在 gridLayout 中，Tab 只是渲染层的逻辑分组
 * - Tab 分组使用主区块（第一个区块）的位置渲染
 * - 解散时无需恢复位置，区块位置一直在 gridLayout 中
 * - tabGroups 只存储在 fullscreen 模式，normal 模式读取 fullscreen 的配置
 */

import { Store } from '@tanstack/store';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import * as storageClient from '$lib/services/storageClient';

// 旧的 localStorage key（用于迁移检测）
const LEGACY_STORAGE_KEY = 'aestival-node-layouts';

// ============ 类型定义 ============

/** 区块尺寸覆盖配置 */
export interface BlockSizeOverride {
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

/** Tab 分组配置 - 极简设计，不存储位置信息 */
export interface TabGroup {
  /** 分组 ID（使用主区块 ID） */
  id: string;
  /** 分组内的区块 ID 列表，第一个为主区块 */
  blockIds: string[];
  /** 当前活动区块索引 */
  activeIndex: number;
}

/** 模式布局状态 */
export interface ModeLayoutState {
  /** 布局配置 - 所有区块始终在此 */
  gridLayout: GridItem[];
  /** 尺寸覆盖 */
  sizeOverrides: Record<string, BlockSizeOverride>;
  /** Tab 分组配置（仅 fullscreen 模式使用） */
  tabGroups: TabGroup[];
}

/** 节点配置 */
export interface NodeConfig {
  nodeType: string;
  fullscreen: ModeLayoutState;
  normal: ModeLayoutState;
  updatedAt: number;
}

type NodeConfigMap = Map<string, NodeConfig>;

// ============ 旧版类型（用于迁移） ============

interface LegacyTabContainerState {
  id: string;
  children: string[];
  activeTab: number;
  originalPositions?: Record<string, { x: number; y: number; w: number; h: number }>;
  createdAt?: number;
  updatedAt?: number;
}

interface LegacyModeLayoutState {
  gridLayout: GridItem[];
  sizeOverrides: Record<string, BlockSizeOverride>;
  tabStates?: Record<string, LegacyTabContainerState>;
}

// ============ 默认配置 ============

export function createDefaultModeState(defaultGridLayout: GridItem[] = []): ModeLayoutState {
  return {
    gridLayout: defaultGridLayout,
    sizeOverrides: {},
    tabGroups: []
  };
}

export function createDefaultNodeConfig(
  nodeType: string, 
  defaultFullscreenLayout: GridItem[] = [],
  defaultNormalLayout: GridItem[] = []
): NodeConfig {
  return {
    nodeType,
    fullscreen: createDefaultModeState(defaultFullscreenLayout),
    normal: createDefaultModeState(defaultNormalLayout),
    updatedAt: Date.now()
  };
}

// ============ 验证和清理 ============

/** 验证 TabGroup */
function validateTabGroup(group: unknown): group is TabGroup {
  if (!group || typeof group !== 'object') return false;
  const g = group as Record<string, unknown>;
  return (
    typeof g.id === 'string' &&
    Array.isArray(g.blockIds) &&
    g.blockIds.every((id: unknown) => typeof id === 'string') &&
    typeof g.activeIndex === 'number'
  );
}

/** 清理 TabGroup（过滤无效 ID、修正 activeIndex） */
function sanitizeTabGroup(group: TabGroup, validBlockIds: Set<string>): TabGroup | null {
  const blockIds = group.blockIds.filter(id => validBlockIds.has(id));
  // 如果有效区块少于 2 个，返回 null 表示应删除此分组
  if (blockIds.length < 2) return null;
  
  const activeIndex = group.activeIndex >= blockIds.length ? 0 : Math.max(0, group.activeIndex);
  return {
    id: blockIds[0], // 主区块 ID 作为分组 ID
    blockIds,
    activeIndex
  };
}

/** 从旧格式迁移 Tab 状态 */
function migrateFromLegacy(
  legacyState: LegacyModeLayoutState,
  validBlockIds: Set<string>
): ModeLayoutState {
  const gridLayout = Array.isArray(legacyState.gridLayout) ? legacyState.gridLayout : [];
  const sizeOverrides = legacyState.sizeOverrides && typeof legacyState.sizeOverrides === 'object' 
    ? legacyState.sizeOverrides : {};
  
  const tabGroups: TabGroup[] = [];
  
  if (legacyState.tabStates) {
    for (const oldTab of Object.values(legacyState.tabStates)) {
      if (!oldTab.children || oldTab.children.length < 2) continue;
      
      // 恢复子区块到 gridLayout（如果不存在）
      const restoredLayout = [...gridLayout];
      for (const childId of oldTab.children) {
        if (!restoredLayout.some(item => item.id === childId)) {
          const pos = oldTab.originalPositions?.[childId];
          restoredLayout.push({
            id: childId,
            x: pos?.x ?? 0,
            y: pos?.y ?? restoredLayout.length,
            w: pos?.w ?? 1,
            h: pos?.h ?? 2,
            minW: 1,
            minH: 1
          });
        }
      }
      
      // 移除旧的 Tab 容器 ID（如果存在）
      const finalLayout = restoredLayout.filter(item => !item.id.startsWith('tab-'));
      
      // 创建新的 TabGroup
      const newGroup = sanitizeTabGroup({
        id: oldTab.children[0],
        blockIds: oldTab.children,
        activeIndex: oldTab.activeTab ?? 0
      }, new Set(finalLayout.map(i => i.id)));
      
      if (newGroup) {
        tabGroups.push(newGroup);
        // 更新 gridLayout
        gridLayout.length = 0;
        gridLayout.push(...finalLayout);
      }
    }
  }
  
  return { gridLayout, sizeOverrides, tabGroups };
}

/** 验证并修复配置 */
function validateAndFixConfig(config: unknown): NodeConfig {
  if (!config || typeof config !== 'object') {
    return createDefaultNodeConfig('unknown');
  }
  
  const c = config as Record<string, unknown>;
  const nodeType = typeof c.nodeType === 'string' ? c.nodeType : 'unknown';
  
  const fixModeState = (state: unknown): ModeLayoutState => {
    if (!state || typeof state !== 'object') return createDefaultModeState();
    const s = state as Record<string, unknown>;
    
    const gridLayout = Array.isArray(s.gridLayout) ? s.gridLayout as GridItem[] : [];
    const sizeOverrides = s.sizeOverrides && typeof s.sizeOverrides === 'object' 
      ? s.sizeOverrides as Record<string, BlockSizeOverride> : {};
    
    // 检查是否是旧格式（有 tabStates）
    if ('tabStates' in s && s.tabStates && typeof s.tabStates === 'object') {
      const validIds = new Set(gridLayout.map(i => i.id));
      return migrateFromLegacy(s as unknown as LegacyModeLayoutState, validIds);
    }
    
    // 新格式
    let tabGroups: TabGroup[] = [];
    if (Array.isArray(s.tabGroups)) {
      const validIds = new Set(gridLayout.map(i => i.id));
      for (const group of s.tabGroups) {
        if (validateTabGroup(group)) {
          const sanitized = sanitizeTabGroup(group, validIds);
          if (sanitized) tabGroups.push(sanitized);
        }
      }
    }
    
    return { gridLayout, sizeOverrides, tabGroups };
  };
  
  return {
    nodeType,
    fullscreen: fixModeState(c.fullscreen),
    normal: fixModeState(c.normal),
    updatedAt: typeof c.updatedAt === 'number' ? c.updatedAt : Date.now()
  };
}

// ============ 存储 ============

// 防抖保存定时器 - 每个 nodeType 独立的定时器
const saveDebounceTimers = new Map<string, ReturnType<typeof setTimeout>>();
const SAVE_DEBOUNCE_MS = 300; // 缩短防抖时间

/** 从后端加载配置（异步） */
async function loadFromBackend(nodeType: string): Promise<NodeConfig | null> {
  try {
    const config = await storageClient.getLayout(nodeType);
    if (config) {
      return validateAndFixConfig(config);
    }
    return null;
  } catch (e) {
    console.error('[nodeLayoutStore] 从后端加载失败:', e);
    return null;
  }
}

/** 保存到后端（异步，带防抖） - 每个 nodeType 独立防抖 */
function saveToBackend(nodeType: string, config: NodeConfig): void {
  // 清除该 nodeType 之前的定时器
  const existingTimer = saveDebounceTimers.get(nodeType);
  if (existingTimer) {
    clearTimeout(existingTimer);
  }
  
  // 防抖保存 - 每个 nodeType 独立
  const timer = setTimeout(async () => {
    try {
      const compressed = compressConfig(config);
      await storageClient.setLayout(nodeType, compressed);
      saveDebounceTimers.delete(nodeType);
    } catch (e) {
      console.error('[nodeLayoutStore] 保存到后端失败:', e);
    }
  }, SAVE_DEBOUNCE_MS);
  
  saveDebounceTimers.set(nodeType, timer);
}

/** 立即保存所有待保存的配置（页面卸载前调用） */
export function flushPendingSaves(): void {
  // 清除所有定时器并立即保存
  for (const [nodeType, timer] of saveDebounceTimers) {
    clearTimeout(timer);
    const config = nodeLayoutStore.state.get(nodeType);
    if (config) {
      const compressed = compressConfig(config);
      // 使用 sendBeacon 或同步保存
      try {
        navigator.sendBeacon?.(
          `${storageClient.getApiBase?.() || ''}/storage/layouts/${nodeType}`,
          JSON.stringify({ config: compressed })
        );
      } catch (e) {
        console.error('[nodeLayoutStore] flushPendingSaves 失败:', e);
      }
    }
  }
  saveDebounceTimers.clear();
}

/** 从 localStorage 加载（仅用于迁移） */
function loadFromLocalStorage(): NodeConfigMap {
  if (typeof window === 'undefined') return new Map();
  try {
    const stored = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!stored) return new Map();
    const parsed = JSON.parse(stored);
    
    const result = new Map<string, NodeConfig>();
    for (const [nodeType, config] of Object.entries(parsed)) {
      result.set(nodeType, validateAndFixConfig(config));
    }
    return result;
  } catch (e) {
    console.error('[nodeLayoutStore] 从 localStorage 加载失败:', e);
    return new Map();
  }
}

/** 压缩配置数据（移除不必要的精度和空值） */
function compressConfig(config: NodeConfig): NodeConfig {
  const compressLayout = (layout: GridItem[]): GridItem[] => 
    layout.map(item => ({
      id: item.id,
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
      ...(item.minW !== undefined && { minW: item.minW }),
      ...(item.minH !== undefined && { minH: item.minH }),
      ...(item.maxW !== undefined && { maxW: item.maxW }),
      ...(item.maxH !== undefined && { maxH: item.maxH })
    }));

  const compressModeState = (state: ModeLayoutState): ModeLayoutState => ({
    gridLayout: compressLayout(state.gridLayout),
    sizeOverrides: Object.keys(state.sizeOverrides).length > 0 ? state.sizeOverrides : {},
    tabGroups: state.tabGroups.length > 0 ? state.tabGroups : []
  });

  return {
    nodeType: config.nodeType,
    fullscreen: compressModeState(config.fullscreen),
    normal: compressModeState(config.normal),
    updatedAt: config.updatedAt
  };
}

export const nodeLayoutStore = new Store<NodeConfigMap>(new Map());

let isHydrated = false;

/** 从后端初始化（异步） */
export async function hydrateFromBackend(): Promise<void> {
  if (isHydrated || typeof window === 'undefined') return;
  isHydrated = true;
  
  try {
    // 先尝试迁移 localStorage 数据
    const migrationResult = await storageClient.migrateFromLocalStorage();
    if (migrationResult.layouts > 0) {
      console.log(`[nodeLayoutStore] 已迁移 ${migrationResult.layouts} 个布局配置`);
    }
    
    // 从后端加载所有布局
    const nodeTypes = await storageClient.listLayouts();
    const configs = new Map<string, NodeConfig>();
    
    for (const nodeType of nodeTypes) {
      const config = await storageClient.getLayout(nodeType);
      if (config) {
        configs.set(nodeType, validateAndFixConfig(config));
      }
    }
    
    if (configs.size > 0) {
      nodeLayoutStore.setState(() => configs);
    }
    
    console.log(`[nodeLayoutStore] 从后端加载了 ${configs.size} 个布局配置`);
  } catch (e) {
    console.error('[nodeLayoutStore] 从后端初始化失败，尝试从 localStorage 加载:', e);
    // 降级：从 localStorage 加载
    const stored = loadFromLocalStorage();
    if (stored.size > 0) {
      nodeLayoutStore.setState(() => stored);
    }
  }
}

/** 同步版本的 hydrate（兼容旧代码） */
export function hydrateFromStorage(): void {
  if (isHydrated || typeof window === 'undefined') return;
  
  // 先从 localStorage 加载（快速启动）
  const stored = loadFromLocalStorage();
  if (stored.size > 0) {
    nodeLayoutStore.setState(() => stored);
  }
  
  // 然后异步从后端加载
  hydrateFromBackend().catch(console.error);
  
  isHydrated = true;
}

// 订阅变化并保存到后端
nodeLayoutStore.subscribe(() => {
  if (!isHydrated) return;
  
  // 保存每个变化的配置到后端
  for (const [nodeType, config] of nodeLayoutStore.state) {
    saveToBackend(nodeType, config);
  }
});

// ============ CRUD ============

export function getNodeConfig(nodeType: string): NodeConfig | undefined {
  hydrateFromStorage();
  return nodeLayoutStore.state.get(nodeType);
}

export function setNodeConfig(nodeType: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, { ...config, updatedAt: Date.now() });
    return next;
  });
}

export function getOrCreateNodeConfig(
  _nodeId: string, 
  nodeType: string,
  defaultFullscreenLayout: GridItem[] = [],
  defaultNormalLayout: GridItem[] = []
): NodeConfig {
  hydrateFromStorage();
  const existing = nodeLayoutStore.state.get(nodeType);
  
  if (existing) {
    const fixed = validateAndFixConfig(existing);
    if (JSON.stringify(fixed) !== JSON.stringify(existing)) {
      setNodeConfig(nodeType, fixed);
      return fixed;
    }
    return existing;
  }
  
  const newConfig = createDefaultNodeConfig(nodeType, defaultFullscreenLayout, defaultNormalLayout);
  setNodeConfig(nodeType, newConfig);
  return newConfig;
}

export function deleteNodeConfig(nodeType: string): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeType);
    return next;
  });
}

// ============ 布局操作 ============

export function updateGridLayout(
  nodeType: string, 
  mode: 'fullscreen' | 'normal',
  gridLayout: GridItem[]
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    next.set(nodeType, {
      ...current,
      [mode]: { ...current[mode], gridLayout },
      updatedAt: Date.now()
    });
    return next;
  });
}

export function updateSizeOverride(
  nodeType: string, 
  mode: 'fullscreen' | 'normal',
  blockId: string, 
  override: BlockSizeOverride
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        sizeOverrides: { ...current[mode].sizeOverrides, [blockId]: override }
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

// ============ Tab 分组操作（新 API） ============

type LayoutMode = 'fullscreen' | 'normal';

/** 获取指定模式的 Tab 分组 */
export function getEffectiveTabGroups(nodeType: string, mode: LayoutMode = 'fullscreen'): TabGroup[] {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return [];
  return config[mode].tabGroups;
}

/** 获取所有 Tab 分组（默认 fullscreen） */
export function getTabGroups(nodeType: string, mode: LayoutMode = 'fullscreen'): TabGroup[] {
  return getEffectiveTabGroups(nodeType, mode);
}

/** 获取区块所属的 Tab 分组 */
export function getBlockTabGroup(nodeType: string, blockId: string, mode: LayoutMode = 'fullscreen'): TabGroup | undefined {
  const groups = getEffectiveTabGroups(nodeType, mode);
  return groups.find(g => g.blockIds.includes(blockId));
}

/** 创建 Tab 分组 */
export function createTabGroup(nodeType: string, blockIds: string[], mode: LayoutMode = 'fullscreen'): string | null {
  if (blockIds.length < 2) {
    console.warn('[nodeLayoutStore] 创建 Tab 分组需要至少 2 个区块');
    return null;
  }
  
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType) || createDefaultNodeConfig(nodeType);
  const modeState = config[mode];
  
  // 校验所有区块都存在于 gridLayout 中
  const gridLayoutIds = new Set(modeState.gridLayout.map(item => item.id));
  const missingBlocks = blockIds.filter(id => !gridLayoutIds.has(id));
  if (missingBlocks.length > 0) {
    console.warn('[nodeLayoutStore] 区块不存在于 gridLayout 中:', missingBlocks);
    return null;
  }
  
  // 检查是否有区块已在其他分组中
  const usedIds = new Set(modeState.tabGroups.flatMap(g => g.blockIds));
  const conflicts = blockIds.filter(id => usedIds.has(id));
  if (conflicts.length > 0) {
    console.warn('[nodeLayoutStore] 区块已在其他 Tab 分组中:', conflicts);
    return null;
  }
  
  // 创建新分组，使用第一个区块 ID 作为分组 ID
  const groupId = blockIds[0];
  const newGroup: TabGroup = {
    id: groupId,
    blockIds: [...blockIds],
    activeIndex: 0
  };
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: [...current[mode].tabGroups, newGroup]
      },
      updatedAt: Date.now()
    });
    return next;
  });
  
  console.log('[nodeLayoutStore] 创建 Tab 分组:', { nodeType, mode, groupId, blockIds });
  return groupId;
}

/** 解散 Tab 分组 */
export function dissolveTabGroup(nodeType: string, groupId: string, mode: LayoutMode = 'fullscreen'): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const groupIndex = config[mode].tabGroups.findIndex(g => g.id === groupId);
  if (groupIndex === -1) {
    console.warn('[nodeLayoutStore] Tab 分组不存在:', groupId);
    return;
  }
  
  // 直接删除分组，不需要修改 gridLayout（区块位置一直在）
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return next;
    
    const newTabGroups = current[mode].tabGroups.filter(g => g.id !== groupId);
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: newTabGroups
      },
      updatedAt: Date.now()
    });
    return next;
  });
  
  console.log('[nodeLayoutStore] 解散 Tab 分组:', { nodeType, mode, groupId });
}

/** 切换活动区块 */
export function switchTabGroupActive(nodeType: string, groupId: string, index: number, mode: LayoutMode = 'fullscreen'): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const group = config[mode].tabGroups.find(g => g.id === groupId);
  if (!group) return;
  
  const safeIndex = index >= group.blockIds.length ? 0 : Math.max(0, index);
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return next;
    
    const newTabGroups = current[mode].tabGroups.map(g => 
      g.id === groupId ? { ...g, activeIndex: safeIndex } : g
    );
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: newTabGroups
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 向分组添加区块 */
export function addBlockToTabGroup(nodeType: string, groupId: string, blockId: string, mode: LayoutMode = 'fullscreen'): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const group = config[mode].tabGroups.find(g => g.id === groupId);
  if (!group) return;
  if (group.blockIds.includes(blockId)) return;
  
  // 检查区块是否存在于 gridLayout
  if (!config[mode].gridLayout.some(item => item.id === blockId)) {
    console.warn('[nodeLayoutStore] 区块不存在于 gridLayout:', blockId);
    return;
  }
  
  // 检查区块是否已在其他分组
  const otherGroup = config[mode].tabGroups.find(g => g.id !== groupId && g.blockIds.includes(blockId));
  if (otherGroup) {
    console.warn('[nodeLayoutStore] 区块已在其他分组中:', blockId);
    return;
  }
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return next;
    
    const newTabGroups = current[mode].tabGroups.map(g => 
      g.id === groupId ? { ...g, blockIds: [...g.blockIds, blockId] } : g
    );
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: newTabGroups
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 从分组移除区块 */
export function removeBlockFromTabGroup(nodeType: string, groupId: string, blockId: string, mode: LayoutMode = 'fullscreen'): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const group = config[mode].tabGroups.find(g => g.id === groupId);
  if (!group) return;
  
  const newBlockIds = group.blockIds.filter(id => id !== blockId);
  
  // 如果剩余区块少于 2 个，自动解散分组
  if (newBlockIds.length < 2) {
    dissolveTabGroup(nodeType, groupId, mode);
    return;
  }
  
  // 更新分组 ID（如果移除的是主区块）
  const newGroupId = newBlockIds[0];
  const newActiveIndex = group.activeIndex >= newBlockIds.length ? newBlockIds.length - 1 : group.activeIndex;
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return next;
    
    const newTabGroups = current[mode].tabGroups.map(g => 
      g.id === groupId ? { id: newGroupId, blockIds: newBlockIds, activeIndex: newActiveIndex } : g
    );
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: newTabGroups
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 重排序分组内区块 */
export function reorderTabGroupBlocks(nodeType: string, groupId: string, newOrder: string[], mode: LayoutMode = 'fullscreen'): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const group = config[mode].tabGroups.find(g => g.id === groupId);
  if (!group) return;
  
  // 找到当前活动区块的新索引
  const activeBlockId = group.blockIds[group.activeIndex];
  const newActiveIndex = newOrder.indexOf(activeBlockId);
  const newGroupId = newOrder[0];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return next;
    
    const newTabGroups = current[mode].tabGroups.map(g => 
      g.id === groupId ? { 
        id: newGroupId, 
        blockIds: newOrder, 
        activeIndex: newActiveIndex >= 0 ? newActiveIndex : 0 
      } : g
    );
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: newTabGroups
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 清除所有 Tab 分组 */
export function clearTabGroups(nodeType: string, mode: LayoutMode = 'fullscreen'): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return next;
    
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        tabGroups: []
      },
      updatedAt: Date.now()
    });
    return next;
  });
  
  console.log('[nodeLayoutStore] 清除所有 Tab 分组:', { nodeType, mode });
}

// ============ 渲染辅助 ============

/** 有效渲染项类型 */
export type EffectiveItem = 
  | { type: 'block'; gridItem: GridItem }
  | { type: 'tab-group'; gridItem: GridItem; group: TabGroup };

/** 计算有效的渲染项 */
export function computeEffectiveItems(
  gridLayout: GridItem[],
  tabGroups: TabGroup[]
): EffectiveItem[] {
  // 收集所有非主区块（被分组但不是第一个的区块）
  const groupedNonPrimaryIds = new Set(
    tabGroups.flatMap(g => g.blockIds.slice(1))
  );
  
  // 主区块 ID 到分组的映射
  const primaryToGroup = new Map(
    tabGroups.map(g => [g.blockIds[0], g])
  );
  
  const items: EffectiveItem[] = [];
  
  for (const gridItem of gridLayout) {
    // 跳过非主区块
    if (groupedNonPrimaryIds.has(gridItem.id)) continue;
    
    // 检查是否是某个分组的主区块
    const group = primaryToGroup.get(gridItem.id);
    
    if (group) {
      items.push({ type: 'tab-group', gridItem, group });
    } else {
      items.push({ type: 'block', gridItem });
    }
  }
  
  return items;
}

/** 获取所有被 Tab 分组使用的区块 ID */
export function getUsedBlockIds(nodeType: string, mode: LayoutMode = 'fullscreen'): string[] {
  const groups = getEffectiveTabGroups(nodeType, mode);
  return groups.flatMap(g => g.blockIds);
}

/** 检查区块是否是 Tab 分组的主区块 */
export function isTabGroupPrimary(nodeType: string, blockId: string, mode: LayoutMode = 'fullscreen'): boolean {
  const groups = getEffectiveTabGroups(nodeType, mode);
  return groups.some(g => g.blockIds[0] === blockId);
}

/** 导出 LayoutMode 类型供外部使用 */
export type { LayoutMode };

// ============ 存储管理 ============

/** 获取存储信息（后端存储无配额限制） */
export function getStorageInfo(): { used: number; total: number; percent: number; nodeCount: number } {
  return {
    used: 0,
    total: Infinity,
    percent: 0,
    nodeCount: nodeLayoutStore.state.size
  };
}

/** 清理所有节点布局配置 */
export async function clearAllNodeConfigs(): Promise<void> {
  if (typeof window === 'undefined') return;
  
  // 清理后端
  const nodeTypes = await storageClient.listLayouts();
  for (const nodeType of nodeTypes) {
    await storageClient.deleteLayout(nodeType);
  }
  
  // 清理内存
  nodeLayoutStore.setState(() => new Map());
  
  // 清理旧的 localStorage（如果有）
  localStorage.removeItem(LEGACY_STORAGE_KEY);
  
  console.log('[nodeLayoutStore] 已清理所有节点配置');
}

/** 清理指定时间之前的配置 */
export async function clearOldConfigs(beforeTimestamp: number): Promise<number> {
  let count = 0;
  
  const toDelete: string[] = [];
  for (const [key, config] of nodeLayoutStore.state) {
    if (config.updatedAt < beforeTimestamp) {
      toDelete.push(key);
    }
  }
  
  for (const nodeType of toDelete) {
    await storageClient.deleteLayout(nodeType);
    count++;
  }
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    for (const key of toDelete) {
      next.delete(key);
    }
    return next;
  });
  
  console.log(`[nodeLayoutStore] 清理了 ${count} 个旧配置`);
  return count;
}

// ============ 订阅 ============

export function subscribeNodeConfig(
  nodeType: string,
  callback: (config: NodeConfig | undefined) => void
): () => void {
  return nodeLayoutStore.subscribe(() => {
    callback(nodeLayoutStore.state.get(nodeType));
  });
}

// ============ 导出/导入 ============

export function exportNodeConfig(nodeType: string): string | null {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  return config ? JSON.stringify(config, null, 2) : null;
}

export function importNodeConfig(nodeType: string, json: string): boolean {
  try {
    const parsed = JSON.parse(json);
    const validated = validateAndFixConfig(parsed);
    setNodeConfig(nodeType, validated);
    return true;
  } catch {
    return false;
  }
}
