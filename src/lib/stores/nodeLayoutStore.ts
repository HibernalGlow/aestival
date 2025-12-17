/**
 * 节点布局状态存储 - 统一管理节点的所有配置
 * 包括：节点模式布局、全屏模式布局、Tab 状态、区块尺寸覆盖
 * 所有配置存储在一个 JSON 中，支持持久化
 */

import { Store } from '@tanstack/store';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import type { TabBlockState } from '$lib/components/blocks/blockRegistry';

// localStorage key
const STORAGE_KEY = 'aestival-node-layouts';

/** 区块尺寸覆盖配置（覆盖代码默认值） */
export interface BlockSizeOverride {
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
  /** 节点模式下的 colSpan */
  colSpan?: 1 | 2;
}

/** 节点模式区块配置 */
export interface NormalBlockConfig {
  /** 区块 ID */
  id: string;
  /** 显示顺序 */
  order: number;
  /** 是否可见 */
  visible: boolean;
  /** 尺寸覆盖 */
  sizeOverride?: BlockSizeOverride;
}

/** 节点模式布局状态 */
export interface NormalModeState {
  /** 区块配置列表（按 order 排序） */
  blocks: NormalBlockConfig[];
  /** Tab 区块状态 */
  tabStates: Record<string, TabBlockState>;
  /** 哪些区块是 Tab 容器 */
  tabBlocks: string[];
}

/** 全屏模式布局状态 */
export interface FullscreenModeState {
  /** GridStack 布局配置 */
  gridLayout: GridItem[];
  /** Tab 区块状态 */
  tabStates: Record<string, TabBlockState>;
  /** 哪些区块是 Tab 容器 */
  tabBlocks: string[];
  /** 区块尺寸覆盖（按 blockId） */
  sizeOverrides: Record<string, BlockSizeOverride>;
}

/** 完整节点配置（一个 JSON 搞定） */
export interface NodeConfig {
  /** 节点类型 */
  nodeType: string;
  /** 全屏模式配置 */
  fullscreen: FullscreenModeState;
  /** 节点模式配置 */
  normal: NormalModeState;
  /** 最后更新时间 */
  updatedAt: number;
}

/** 节点配置 Map 类型 */
type NodeConfigMap = Map<string, NodeConfig>;

// ============ 默认配置创建 ============

/** 创建默认的节点模式状态 */
export function createDefaultNormalState(): NormalModeState {
  return {
    blocks: [],
    tabStates: {},
    tabBlocks: []
  };
}

/** 创建默认的全屏模式状态 */
export function createDefaultFullscreenState(defaultGridLayout: GridItem[] = []): FullscreenModeState {
  return {
    gridLayout: defaultGridLayout,
    tabStates: {},
    tabBlocks: [],
    sizeOverrides: {}
  };
}

/** 创建默认的节点配置 */
export function createDefaultNodeConfig(nodeType: string, defaultGridLayout: GridItem[] = []): NodeConfig {
  return {
    nodeType,
    fullscreen: createDefaultFullscreenState(defaultGridLayout),
    normal: createDefaultNormalState(),
    updatedAt: Date.now()
  };
}

// ============ 存储管理 ============

/** 从 localStorage 加载状态 */
function loadFromStorage(): NodeConfigMap {
  if (typeof window === 'undefined') return new Map();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Map();
    const parsed = JSON.parse(stored);
    return new Map(Object.entries(parsed));
  } catch {
    return new Map();
  }
}

/** 保存状态到 localStorage */
function saveToStorage(configs: NodeConfigMap): void {
  if (typeof window === 'undefined') return;
  try {
    const obj = Object.fromEntries(configs);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  } catch (e) {
    console.warn('[nodeLayoutStore] Failed to save to localStorage:', e);
  }
}

// 创建 TanStack Store（初始为空，客户端挂载时加载）
export const nodeLayoutStore = new Store<NodeConfigMap>(new Map());

// 标记是否已从 localStorage 加载
let isHydrated = false;

/** 确保从 localStorage 加载状态（客户端） */
export function hydrateFromStorage(): void {
  if (isHydrated || typeof window === 'undefined') return;
  isHydrated = true;
  
  const stored = loadFromStorage();
  if (stored.size > 0) {
    nodeLayoutStore.setState(() => stored);
  }
}

// 订阅变化，自动保存到 localStorage
nodeLayoutStore.subscribe(() => {
  if (isHydrated) {
    saveToStorage(nodeLayoutStore.state);
  }
});

// ============ 基础 CRUD ============

/** 获取节点配置 */
export function getNodeConfig(nodeId: string): NodeConfig | undefined {
  hydrateFromStorage();
  return nodeLayoutStore.state.get(nodeId);
}

/** 设置节点配置（完全覆盖） */
export function setNodeConfig(nodeId: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeId, { ...config, updatedAt: Date.now() });
    return next;
  });
}

/** 获取或创建节点配置 */
export function getOrCreateNodeConfig(
  nodeId: string, 
  nodeType: string,
  defaultGridLayout: GridItem[] = []
): NodeConfig {
  hydrateFromStorage();
  
  const existing = nodeLayoutStore.state.get(nodeId);
  if (existing) return existing;
  
  const newConfig = createDefaultNodeConfig(nodeType, defaultGridLayout);
  setNodeConfig(nodeId, newConfig);
  return newConfig;
}

/** 删除节点配置 */
export function deleteNodeConfig(nodeId: string): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeId);
    return next;
  });
}

// ============ 兼容旧 API（NodeLayoutState） ============

/** 旧版布局状态类型（兼容） */
export interface NodeLayoutState {
  fullscreen: FullscreenModeState;
  normal: NormalModeState;
}

/** 获取节点布局状态（兼容旧 API） */
export function getNodeLayoutState(nodeId: string): NodeLayoutState | undefined {
  const config = getNodeConfig(nodeId);
  if (!config) return undefined;
  return { fullscreen: config.fullscreen, normal: config.normal };
}

/** 获取或创建节点布局状态（兼容旧 API） */
export function getOrCreateLayoutState(nodeId: string, defaultGridLayout: GridItem[] = []): NodeLayoutState {
  // 尝试获取现有配置
  hydrateFromStorage();
  const existing = nodeLayoutStore.state.get(nodeId);
  if (existing) {
    return { fullscreen: existing.fullscreen, normal: existing.normal };
  }
  
  // 创建新配置（nodeType 暂时用 'unknown'，后续会被正确设置）
  const newConfig = createDefaultNodeConfig('unknown', defaultGridLayout);
  setNodeConfig(nodeId, newConfig);
  return { fullscreen: newConfig.fullscreen, normal: newConfig.normal };
}

// ============ 全屏模式操作 ============

/** 更新全屏模式的 GridStack 布局 */
export function updateFullscreenGridLayout(nodeId: string, gridLayout: GridItem[]): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    
    next.set(nodeId, {
      ...current,
      fullscreen: { ...current.fullscreen, gridLayout },
      updatedAt: Date.now()
    });
    
    return next;
  });
}

/** 更新全屏模式的区块尺寸覆盖 */
export function updateFullscreenSizeOverride(
  nodeId: string, 
  blockId: string, 
  override: BlockSizeOverride
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    
    next.set(nodeId, {
      ...current,
      fullscreen: {
        ...current.fullscreen,
        sizeOverrides: { ...current.fullscreen.sizeOverrides, [blockId]: override }
      },
      updatedAt: Date.now()
    });
    
    return next;
  });
}

// ============ 节点模式操作 ============

/** 更新节点模式的区块配置 */
export function updateNormalBlocks(nodeId: string, blocks: NormalBlockConfig[]): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    
    next.set(nodeId, {
      ...current,
      normal: { ...current.normal, blocks },
      updatedAt: Date.now()
    });
    
    return next;
  });
}

/** 更新节点模式单个区块的可见性 */
export function updateNormalBlockVisibility(nodeId: string, blockId: string, visible: boolean): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    
    const blocks = [...current.normal.blocks];
    const idx = blocks.findIndex(b => b.id === blockId);
    if (idx >= 0) {
      blocks[idx] = { ...blocks[idx], visible };
    } else {
      blocks.push({ id: blockId, order: blocks.length, visible });
    }
    
    next.set(nodeId, {
      ...current,
      normal: { ...current.normal, blocks },
      updatedAt: Date.now()
    });
    
    return next;
  });
}

// ============ Tab 操作（通用） ============

/** 更新 Tab 状态 */
export function updateTabState(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  state: TabBlockState
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...current[mode],
        tabStates: { ...current[mode].tabStates, [tabId]: state }
      },
      updatedAt: Date.now()
    });
    
    return next;
  });
}

/** 创建 Tab 区块（合并多个区块） */
export function createTabBlock(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  blockIds: string[]
): void {
  if (blockIds.length < 2) return;
  
  const tabId = blockIds[0];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    const modeState = current[mode];
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...modeState,
        tabBlocks: [...modeState.tabBlocks, tabId],
        tabStates: { ...modeState.tabStates, [tabId]: { activeTab: 0, children: blockIds } }
      },
      updatedAt: Date.now()
    });
    
    return next;
  });
}

/** 删除 Tab 区块（恢复为独立区块） */
export function removeTabBlock(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  tabId: string
): string[] {
  let childIds: string[] = [];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId);
    if (!current) return prev;
    
    const modeState = current[mode];
    const tabState = modeState.tabStates[tabId];
    
    if (tabState) {
      childIds = tabState.children.slice(1);
    }
    
    const newTabStates = { ...modeState.tabStates };
    delete newTabStates[tabId];
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...modeState,
        tabBlocks: modeState.tabBlocks.filter(id => id !== tabId),
        tabStates: newTabStates
      },
      updatedAt: Date.now()
    });
    
    return next;
  });
  
  return childIds;
}

// ============ 查询辅助函数 ============

/** 检查区块是否是 Tab 容器 */
export function isTabContainer(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  blockId: string
): boolean {
  const config = getNodeConfig(nodeId);
  if (!config) return false;
  return config[mode].tabBlocks.includes(blockId);
}

/** 获取 Tab 状态 */
export function getTabState(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  tabId: string
): TabBlockState | undefined {
  const config = getNodeConfig(nodeId);
  if (!config) return undefined;
  return config[mode].tabStates[tabId];
}

/** 获取已在 Tab 中使用的区块 ID（作为子区块） */
export function getUsedTabBlockIds(
  nodeId: string,
  mode: 'fullscreen' | 'normal'
): string[] {
  const config = getNodeConfig(nodeId);
  if (!config) return [];
  
  const ids: string[] = [];
  for (const tabState of Object.values(config[mode].tabStates)) {
    ids.push(...tabState.children.slice(1));
  }
  return ids;
}

/** 获取区块的尺寸覆盖配置 */
export function getBlockSizeOverride(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  blockId: string
): BlockSizeOverride | undefined {
  const config = getNodeConfig(nodeId);
  if (!config) return undefined;
  
  if (mode === 'fullscreen') {
    return config.fullscreen.sizeOverrides[blockId];
  } else {
    return config.normal.blocks.find(b => b.id === blockId)?.sizeOverride;
  }
}

// ============ 订阅 ============

/** 订阅节点配置变化 */
export function subscribeNodeConfig(
  nodeId: string,
  callback: (config: NodeConfig | undefined) => void
): () => void {
  return nodeLayoutStore.subscribe(() => {
    callback(nodeLayoutStore.state.get(nodeId));
  });
}

/** 订阅节点布局状态变化（兼容旧 API） */
export function subscribeNodeLayoutState(
  nodeId: string,
  callback: (state: NodeLayoutState | undefined) => void
): () => void {
  return nodeLayoutStore.subscribe(() => {
    const config = nodeLayoutStore.state.get(nodeId);
    if (config) {
      callback({ fullscreen: config.fullscreen, normal: config.normal });
    } else {
      callback(undefined);
    }
  });
}

// ============ 导出/导入 ============

/** 导出节点配置为 JSON 字符串 */
export function exportNodeConfig(nodeId: string): string | null {
  const config = getNodeConfig(nodeId);
  if (!config) return null;
  return JSON.stringify(config, null, 2);
}

/** 导入节点配置 */
export function importNodeConfig(nodeId: string, json: string): boolean {
  try {
    const config = JSON.parse(json) as NodeConfig;
    setNodeConfig(nodeId, config);
    return true;
  } catch {
    return false;
  }
}
