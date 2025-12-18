/**
 * 节点布局状态存储 - 统一管理节点的所有配置
 * 两种模式共用 GridItem[] 结构，节点模式用静态渲染，全屏模式用 GridStack
 * 
 * Tab 状态内嵌在 ModeLayoutState 中，每个布局独立保存
 * 节点模式读取全屏模式的 Tab 配置
 */

import { Store } from '@tanstack/store';
import type { GridItem } from '$lib/components/ui/dashboard-grid';

const STORAGE_KEY = 'aestival-node-layouts';
const OLD_TAB_STORAGE_KEY = 'aestival-unified-tabs';

// ============ 类型定义 ============

/** 区块尺寸覆盖配置 */
export interface BlockSizeOverride {
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

/** 区块原始位置 */
export interface BlockPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** 单个 Tab 容器的状态 */
export interface TabContainerState {
  /** Tab 容器独立 ID（格式：tab-{timestamp}-{random}） */
  id: string;
  /** 子区块 ID 列表（所有子区块，不再复用第一个作为容器 ID） */
  children: string[];
  /** 当前活动标签索引 */
  activeTab: number;
  /** 子区块原始位置字典 */
  originalPositions: Record<string, BlockPosition>;
  /** 创建时间戳 */
  createdAt: number;
  /** 最后更新时间戳 */
  updatedAt: number;
}

/** 生成唯一的 Tab 容器 ID */
function generateTabId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `tab-${timestamp}-${random}`;
}

/** 模式布局状态（包含 Tab 状态） */
export interface ModeLayoutState {
  /** 布局配置 */
  gridLayout: GridItem[];
  /** 尺寸覆盖 */
  sizeOverrides: Record<string, BlockSizeOverride>;
  /** Tab 状态映射：tabId -> TabContainerState */
  tabStates: Record<string, TabContainerState>;
}


/** 旧版模式布局状态（用于迁移） */
interface LegacyModeLayoutState {
  gridLayout: GridItem[];
  tabStates?: Record<string, { activeTab: number; children: string[] }>;
  tabBlocks?: string[];
  sizeOverrides: Record<string, BlockSizeOverride>;
}

/** 旧版 unifiedTabStore 格式 */
interface OldUnifiedTabConfig {
  version: number;
  containers: Record<string, {
    id: string;
    children: string[];
    activeTab: number;
    createdAt: number;
    updatedAt: number;
  }>;
  containerIds: string[];
}

/** 节点配置 */
export interface NodeConfig {
  nodeType: string;
  fullscreen: ModeLayoutState;
  normal: ModeLayoutState;
  updatedAt: number;
}

type NodeConfigMap = Map<string, NodeConfig>;

// ============ 默认配置 ============

export function createDefaultModeState(defaultGridLayout: GridItem[] = []): ModeLayoutState {
  return {
    gridLayout: defaultGridLayout,
    sizeOverrides: {},
    tabStates: {}
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

// ============ 验证函数 ============

/** 验证 Tab 容器状态 */
export function validateTabContainerState(state: unknown): state is TabContainerState {
  if (!state || typeof state !== 'object') return false;
  const s = state as Record<string, unknown>;
  
  return (
    typeof s.id === 'string' &&
    Array.isArray(s.children) &&
    s.children.every((c: unknown) => typeof c === 'string') &&
    typeof s.activeTab === 'number' &&
    s.originalPositions !== undefined &&
    typeof s.originalPositions === 'object' &&
    typeof s.createdAt === 'number' &&
    typeof s.updatedAt === 'number'
  );
}


/** 验证模式布局状态 */
export function validateModeLayoutState(state: unknown): state is ModeLayoutState {
  if (!state || typeof state !== 'object') return false;
  const s = state as Record<string, unknown>;
  
  if (!Array.isArray(s.gridLayout)) return false;
  if (!s.sizeOverrides || typeof s.sizeOverrides !== 'object') return false;
  if (s.tabStates !== undefined && typeof s.tabStates !== 'object') return false;
  
  if (s.tabStates) {
    for (const tabState of Object.values(s.tabStates as Record<string, unknown>)) {
      if (!validateTabContainerState(tabState)) return false;
    }
  }
  
  return true;
}

/** 清理 Tab 状态（过滤无效 ID、去重、修正 activeTab） */
export function sanitizeTabState(
  state: TabContainerState,
  validBlockIds?: Set<string>
): TabContainerState {
  // 过滤无效 ID
  let children = validBlockIds
    ? state.children.filter(id => validBlockIds.has(id))
    : state.children;
  
  // 去重
  children = [...new Set(children)];
  
  // 修正 activeTab
  const activeTab = children.length > 0 && state.activeTab >= children.length
    ? 0
    : state.activeTab;
  
  // 清理 originalPositions 中不存在的 ID
  const originalPositions: Record<string, BlockPosition> = {};
  for (const childId of children) {
    if (state.originalPositions[childId]) {
      originalPositions[childId] = state.originalPositions[childId];
    }
  }
  
  return {
    ...state,
    children,
    activeTab,
    originalPositions,
    updatedAt: Date.now()
  };
}

/** 获取默认位置 */
function getDefaultPosition(index: number, isFullscreen: boolean): BlockPosition {
  return {
    x: isFullscreen ? 0 : index % 2,
    y: isFullscreen ? index * 2 : Math.floor(index / 2),
    w: 1,
    h: isFullscreen ? 2 : 1
  };
}


// ============ 数据迁移 ============

/** 从旧格式迁移 Tab 状态到新格式 */
function migrateTabStates(
  oldTabConfig: OldUnifiedTabConfig | undefined,
  gridLayout: GridItem[]
): Record<string, TabContainerState> {
  if (!oldTabConfig?.containers) return {};
  
  const result: Record<string, TabContainerState> = {};
  
  for (const [tabId, oldState] of Object.entries(oldTabConfig.containers)) {
    // 从 gridLayout 中获取原始位置
    const originalPositions: Record<string, BlockPosition> = {};
    for (const childId of oldState.children) {
      const item = gridLayout.find(i => i.id === childId);
      if (item) {
        originalPositions[childId] = {
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h
        };
      } else {
        // 使用默认位置
        originalPositions[childId] = getDefaultPosition(Object.keys(originalPositions).length, true);
      }
    }
    
    result[tabId] = {
      id: tabId,
      children: oldState.children,
      activeTab: oldState.activeTab,
      originalPositions,
      createdAt: oldState.createdAt ?? Date.now(),
      updatedAt: oldState.updatedAt ?? Date.now()
    };
  }
  
  return result;
}

/** 验证并修复配置结构（兼容旧格式） */
function validateAndFixConfig(
  config: NodeConfig | { fullscreen?: LegacyModeLayoutState; normal?: LegacyModeLayoutState; nodeType?: string; updatedAt?: number },
  oldTabConfig?: OldUnifiedTabConfig
): NodeConfig {
  const fixModeState = (state: ModeLayoutState | LegacyModeLayoutState | undefined, useOldTabs: boolean): ModeLayoutState => {
    if (!state) return createDefaultModeState();
    
    const gridLayout = Array.isArray(state.gridLayout) ? state.gridLayout : [];
    const sizeOverrides = state.sizeOverrides && typeof state.sizeOverrides === 'object' ? state.sizeOverrides : {};
    
    // 如果已有新格式的 tabStates，直接使用
    if ('tabStates' in state && state.tabStates && typeof state.tabStates === 'object') {
      return { gridLayout, sizeOverrides, tabStates: state.tabStates as Record<string, TabContainerState> };
    }
    
    // 从旧格式迁移
    const tabStates = useOldTabs && oldTabConfig ? migrateTabStates(oldTabConfig, gridLayout) : {};
    
    return { gridLayout, sizeOverrides, tabStates };
  };
  
  return {
    nodeType: config.nodeType || 'unknown',
    fullscreen: fixModeState(config.fullscreen, true),
    normal: fixModeState(config.normal, false), // 节点模式不迁移，读取 fullscreen
    updatedAt: config.updatedAt || Date.now()
  };
}


// ============ 存储 ============

/** 加载旧的 unifiedTabStore 数据 */
function loadOldTabConfig(): Record<string, OldUnifiedTabConfig> {
  if (typeof window === 'undefined') return {};
  try {
    const stored = localStorage.getItem(OLD_TAB_STORAGE_KEY);
    if (!stored) return {};
    return JSON.parse(stored) as Record<string, OldUnifiedTabConfig>;
  } catch {
    return {};
  }
}

/** 清理旧的 unifiedTabStore 数据 */
function clearOldTabConfig(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(OLD_TAB_STORAGE_KEY);
  } catch {
    // 忽略错误
  }
}

function loadFromStorage(): NodeConfigMap {
  if (typeof window === 'undefined') return new Map();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Map();
    const parsed = JSON.parse(stored);
    
    // 加载旧的 Tab 配置用于迁移
    const oldTabConfigs = loadOldTabConfig();
    
    const result = new Map<string, NodeConfig>();
    for (const [nodeType, config] of Object.entries(parsed)) {
      const oldTabConfig = oldTabConfigs[nodeType];
      const fixed = validateAndFixConfig(config as NodeConfig, oldTabConfig);
      result.set(nodeType, fixed);
    }
    
    // 如果有迁移，清理旧数据
    if (Object.keys(oldTabConfigs).length > 0) {
      clearOldTabConfig();
      console.log('[nodeLayoutStore] 已迁移旧 Tab 配置并清理');
    }
    
    return result;
  } catch (e) {
    console.error('[nodeLayoutStore] 加载失败:', e);
    return new Map();
  }
}

function saveToStorage(configs: NodeConfigMap): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(configs)));
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn('[nodeLayoutStore] localStorage 配额已满，仅保留内存状态');
    } else {
      console.warn('[nodeLayoutStore] 保存失败:', e);
    }
  }
}

export const nodeLayoutStore = new Store<NodeConfigMap>(new Map());

let isHydrated = false;

export function hydrateFromStorage(): void {
  if (isHydrated || typeof window === 'undefined') return;
  isHydrated = true;
  const stored = loadFromStorage();
  if (stored.size > 0) {
    nodeLayoutStore.setState(() => stored);
  }
}

nodeLayoutStore.subscribe(() => {
  if (isHydrated) saveToStorage(nodeLayoutStore.state);
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

/** 按 nodeType 设置配置 */
function setNodeConfigByType(nodeType: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, { ...config, updatedAt: Date.now() });
    return next;
  });
}

/**
 * 获取或创建节点配置
 * 注意：使用 nodeType 作为 key，同类型节点共享布局配置
 */
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
      setNodeConfigByType(nodeType, fixed);
      return fixed;
    }
    return existing;
  }
  const newConfig = createDefaultNodeConfig(nodeType, defaultFullscreenLayout, defaultNormalLayout);
  setNodeConfigByType(nodeType, newConfig);
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

// ============ Tab 操作 ============

/** 创建 Tab 容器 */
export function createTab(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  blockIds: string[]
): string | null {
  if (blockIds.length < 2) {
    console.warn('[nodeLayoutStore] 创建 Tab 需要至少 2 个区块');
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
  
  // 检查是否有区块已在其他 Tab 中
  const usedIds = getUsedBlockIds(nodeType, mode);
  const conflicts = blockIds.filter(id => usedIds.includes(id));
  if (conflicts.length > 0) {
    console.warn('[nodeLayoutStore] 区块已在其他 Tab 中:', conflicts);
    return null;
  }
  
  // 生成独立的 Tab 容器 ID
  const tabId = generateTabId();
  const now = Date.now();
  
  // 从 gridLayout 获取每个区块的原始位置
  const originalPositions: Record<string, BlockPosition> = {};
  let firstBlockPosition: BlockPosition | null = null;
  
  for (let i = 0; i < blockIds.length; i++) {
    const blockId = blockIds[i];
    const item = modeState.gridLayout.find(g => g.id === blockId);
    if (item) {
      originalPositions[blockId] = { x: item.x, y: item.y, w: item.w, h: item.h };
      if (i === 0) firstBlockPosition = originalPositions[blockId];
    }
    // 不再使用默认位置，因为已校验区块必须存在
  }
  
  console.log('[nodeLayoutStore] createTab - 保存原始位置:', {
    blockIds,
    originalPositions,
    firstBlockPosition
  });
  
  // 创建 Tab 状态
  const newTabState: TabContainerState = {
    id: tabId,
    children: blockIds,
    activeTab: 0,
    originalPositions,
    createdAt: now,
    updatedAt: now
  };
  
  // 更新 gridLayout：移除被合并区块，添加 Tab 容器
  const newGridLayout = modeState.gridLayout.filter(item => !blockIds.includes(item.id));
  if (firstBlockPosition) {
    newGridLayout.push({
      id: tabId,
      x: firstBlockPosition.x,
      y: firstBlockPosition.y,
      w: firstBlockPosition.w,
      h: firstBlockPosition.h,
      minW: 1,
      minH: 1
    });
  }
  
  // 更新配置
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        gridLayout: newGridLayout,
        tabStates: { ...modeState.tabStates, [tabId]: newTabState }
      },
      updatedAt: now
    });
    return next;
  });
  
  console.log('[nodeLayoutStore] 创建 Tab 完成:', { 
    nodeType, 
    mode, 
    tabId, 
    children: blockIds,
    originalPositions,
    newGridLayout: newGridLayout.map(i => i.id)
  });
  return tabId;
}

/** 删除 Tab 容器 */
export function removeTab(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string
): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) {
    console.warn('[nodeLayoutStore] removeTab - 配置不存在:', nodeType);
    return;
  }
  
  const modeState = config[mode];
  const tabState = modeState.tabStates[tabId];
  if (!tabState) {
    console.warn('[nodeLayoutStore] removeTab - Tab 不存在:', { nodeType, mode, tabId, availableTabs: Object.keys(modeState.tabStates) });
    return;
  }
  
  // 恢复所有子区块到 gridLayout
  console.log('[nodeLayoutStore] removeTab - 开始恢复:', {
    tabId,
    children: tabState.children,
    originalPositions: tabState.originalPositions,
    currentGridLayout: modeState.gridLayout.map(i => ({ id: i.id, x: i.x, y: i.y, w: i.w, h: i.h }))
  });
  
  const restoredItems: GridItem[] = tabState.children.map((childId, index) => {
    const pos = tabState.originalPositions[childId];
    const hasOriginal = !!pos;
    const finalPos = pos || getDefaultPosition(index, mode === 'fullscreen');
    
    console.log('[nodeLayoutStore] removeTab - 恢复区块:', { 
      childId, 
      hasOriginal,
      originalPos: pos,
      finalPos
    });
    
    return {
      id: childId,
      x: finalPos.x,
      y: finalPos.y,
      w: finalPos.w,
      h: finalPos.h,
      minW: 1,
      minH: 1
    };
  });
  
  // 从 gridLayout 移除 Tab 容器，添加恢复的区块
  const newGridLayout = modeState.gridLayout.filter(item => item.id !== tabId);
  newGridLayout.push(...restoredItems);
  
  // 从 tabStates 删除
  const newTabStates = { ...modeState.tabStates };
  delete newTabStates[tabId];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        gridLayout: newGridLayout,
        tabStates: newTabStates
      },
      updatedAt: Date.now()
    });
    return next;
  });
  
  console.log('[nodeLayoutStore] removeTab - 完成:', { 
    nodeType, 
    mode, 
    tabId,
    restoredCount: restoredItems.length,
    newGridLayoutIds: newGridLayout.map(i => i.id)
  });
}


/** 设置活动标签 */
export function setActiveTab(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  index: number
): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const modeState = config[mode];
  const tabState = modeState.tabStates[tabId];
  if (!tabState) return;
  
  // 处理越界
  const safeIndex = index >= tabState.children.length ? 0 : Math.max(0, index);
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        tabStates: {
          ...modeState.tabStates,
          [tabId]: { ...tabState, activeTab: safeIndex, updatedAt: Date.now() }
        }
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 添加子区块到 Tab */
export function addChildToTab(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  blockId: string
): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const modeState = config[mode];
  const tabState = modeState.tabStates[tabId];
  if (!tabState) return;
  if (tabState.children.includes(blockId)) return;
  
  // 获取区块原始位置
  const item = modeState.gridLayout.find(g => g.id === blockId);
  const originalPosition = item 
    ? { x: item.x, y: item.y, w: item.w, h: item.h }
    : getDefaultPosition(tabState.children.length, mode === 'fullscreen');
  
  // 从 gridLayout 移除该区块
  const newGridLayout = modeState.gridLayout.filter(g => g.id !== blockId);
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        gridLayout: newGridLayout,
        tabStates: {
          ...modeState.tabStates,
          [tabId]: {
            ...tabState,
            children: [...tabState.children, blockId],
            originalPositions: { ...tabState.originalPositions, [blockId]: originalPosition },
            updatedAt: Date.now()
          }
        }
      },
      updatedAt: Date.now()
    });
    return next;
  });
}


/** 从 Tab 移除子区块 */
export function removeChildFromTab(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  blockId: string
): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const modeState = config[mode];
  const tabState = modeState.tabStates[tabId];
  if (!tabState) return;
  
  const newChildren = tabState.children.filter(id => id !== blockId);
  
  // 如果 children < 2，自动删除 Tab 容器
  if (newChildren.length < 2) {
    removeTab(nodeType, mode, tabId);
    return;
  }
  
  // 恢复区块到 gridLayout
  const pos = tabState.originalPositions[blockId] || getDefaultPosition(0, mode === 'fullscreen');
  const restoredItem: GridItem = {
    id: blockId,
    x: pos.x,
    y: pos.y,
    w: pos.w,
    h: pos.h,
    minW: 1,
    minH: 1
  };
  
  // 修正 activeTab
  const activeTab = tabState.activeTab >= newChildren.length
    ? newChildren.length - 1
    : tabState.activeTab;
  
  // 清理 originalPositions
  const newOriginalPositions = { ...tabState.originalPositions };
  delete newOriginalPositions[blockId];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        gridLayout: [...modeState.gridLayout, restoredItem],
        tabStates: {
          ...modeState.tabStates,
          [tabId]: {
            ...tabState,
            children: newChildren,
            activeTab,
            originalPositions: newOriginalPositions,
            updatedAt: Date.now()
          }
        }
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 重排序 Tab 子区块 */
export function reorderTabChildren(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  newOrder: string[]
): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const modeState = config[mode];
  const tabState = modeState.tabStates[tabId];
  if (!tabState) return;
  
  // 找到当前活动区块的 ID
  const activeBlockId = tabState.children[tabState.activeTab];
  
  // 更新顺序后，找到活动区块的新索引
  const newActiveTab = newOrder.indexOf(activeBlockId);
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        tabStates: {
          ...modeState.tabStates,
          [tabId]: {
            ...tabState,
            children: newOrder,
            activeTab: newActiveTab >= 0 ? newActiveTab : 0,
            updatedAt: Date.now()
          }
        }
      },
      updatedAt: Date.now()
    });
    return next;
  });
}


// ============ Tab 辅助方法 ============

/** 获取 Tab 状态 */
export function getTabState(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string
): TabContainerState | undefined {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return undefined;
  return config[mode].tabStates[tabId];
}

/** 获取所有被 Tab 使用的区块 ID（Tab 容器使用独立 ID，所以返回所有子区块） */
export function getUsedBlockIds(
  nodeType: string,
  mode: 'fullscreen' | 'normal'
): string[] {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return [];
  
  const ids: string[] = [];
  for (const tabState of Object.values(config[mode].tabStates)) {
    // Tab 容器使用独立 ID，所以所有子区块都是"被使用"的
    ids.push(...tabState.children);
  }
  return ids;
}

/** 检查区块是否是 Tab 容器 */
export function isTabContainer(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  blockId: string
): boolean {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return false;
  return blockId in config[mode].tabStates;
}

/** 获取所有 Tab 容器 ID */
export function getTabContainerIds(
  nodeType: string,
  mode: 'fullscreen' | 'normal'
): string[] {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return [];
  return Object.keys(config[mode].tabStates);
}

/** 清除所有 Tab 状态并恢复子区块（重置布局时调用） */
export function clearTabStates(
  nodeType: string,
  mode: 'fullscreen' | 'normal'
): void {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return;
  
  const modeState = config[mode];
  const tabIds = Object.keys(modeState.tabStates);
  
  // 如果没有 Tab，直接返回
  if (tabIds.length === 0) {
    console.log('[nodeLayoutStore] 没有 Tab 需要清除:', { nodeType, mode });
    return;
  }
  
  // 收集所有需要恢复的区块
  const restoredItems: GridItem[] = [];
  const tabContainerIds = new Set<string>();
  
  for (const tabState of Object.values(modeState.tabStates)) {
    tabContainerIds.add(tabState.id);
    
    // 恢复所有子区块到原始位置
    tabState.children.forEach((childId, index) => {
      const pos = tabState.originalPositions[childId] || getDefaultPosition(index, mode === 'fullscreen');
      restoredItems.push({
        id: childId,
        x: pos.x,
        y: pos.y,
        w: pos.w,
        h: pos.h,
        minW: 1,
        minH: 1
      });
    });
  }
  
  // 从 gridLayout 移除 Tab 容器，添加恢复的区块
  const newGridLayout = modeState.gridLayout.filter(item => !tabContainerIds.has(item.id));
  newGridLayout.push(...restoredItems);
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, {
      ...config,
      [mode]: {
        ...modeState,
        gridLayout: newGridLayout,
        tabStates: {}
      },
      updatedAt: Date.now()
    });
    return next;
  });
  
  console.log('[nodeLayoutStore] 清除 Tab 状态并恢复区块:', { nodeType, mode, restored: restoredItems.length });
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
    setNodeConfigByType(nodeType, JSON.parse(json) as NodeConfig);
    return true;
  } catch {
    return false;
  }
}
