/**
 * 节点布局状态存储 - 统一管理节点的所有配置
 * 两种模式共用 GridItem[] 结构，节点模式用静态渲染，全屏模式用 GridStack
 */

import { Store } from '@tanstack/store';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import type { TabBlockState } from '$lib/components/blocks/blockRegistry';

const STORAGE_KEY = 'aestival-node-layouts';

/** 区块尺寸覆盖配置 */
export interface BlockSizeOverride {
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

/** 模式布局状态（全屏和节点模式共用） */
export interface ModeLayoutState {
  /** 布局配置 */
  gridLayout: GridItem[];
  /** Tab 区块状态 */
  tabStates: Record<string, TabBlockState>;
  /** Tab 容器列表 */
  tabBlocks: string[];
  /** 尺寸覆盖 */
  sizeOverrides: Record<string, BlockSizeOverride>;
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
    tabStates: {},
    tabBlocks: [],
    sizeOverrides: {}
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

// ============ 存储 ============

function loadFromStorage(): NodeConfigMap {
  if (typeof window === 'undefined') return new Map();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Map();
    return new Map(Object.entries(JSON.parse(stored)));
  } catch {
    return new Map();
  }
}

function saveToStorage(configs: NodeConfigMap): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(configs)));
  } catch (e) {
    console.warn('[nodeLayoutStore] 保存失败:', e);
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

export function getNodeConfig(nodeId: string): NodeConfig | undefined {
  hydrateFromStorage();
  return nodeLayoutStore.state.get(nodeId);
}

export function setNodeConfig(nodeId: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeId, { ...config, updatedAt: Date.now() });
    return next;
  });
}

/** 验证并修复配置结构 */
function validateAndFixConfig(config: NodeConfig): NodeConfig {
  // 确保 fullscreen 和 normal 都有完整结构
  const fixModeState = (state: ModeLayoutState | undefined): ModeLayoutState => {
    if (!state) return createDefaultModeState();
    return {
      gridLayout: Array.isArray(state.gridLayout) ? state.gridLayout : [],
      tabStates: state.tabStates && typeof state.tabStates === 'object' ? state.tabStates : {},
      tabBlocks: Array.isArray(state.tabBlocks) ? state.tabBlocks : [],
      sizeOverrides: state.sizeOverrides && typeof state.sizeOverrides === 'object' ? state.sizeOverrides : {}
    };
  };
  
  return {
    nodeType: config.nodeType || 'unknown',
    fullscreen: fixModeState(config.fullscreen),
    normal: fixModeState(config.normal),
    updatedAt: config.updatedAt || Date.now()
  };
}

export function getOrCreateNodeConfig(
  nodeId: string, 
  nodeType: string,
  defaultFullscreenLayout: GridItem[] = [],
  defaultNormalLayout: GridItem[] = []
): NodeConfig {
  hydrateFromStorage();
  const existing = nodeLayoutStore.state.get(nodeId);
  
  if (existing) {
    // 验证并修复现有配置
    const fixed = validateAndFixConfig(existing);
    // 如果配置被修复了，保存修复后的版本
    if (JSON.stringify(fixed) !== JSON.stringify(existing)) {
      setNodeConfig(nodeId, fixed);
      return fixed;
    }
    return existing;
  }
  
  const newConfig = createDefaultNodeConfig(nodeType, defaultFullscreenLayout, defaultNormalLayout);
  setNodeConfig(nodeId, newConfig);
  return newConfig;
}

export function deleteNodeConfig(nodeId: string): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeId);
    return next;
  });
}

// ============ 布局操作 ============

export function updateGridLayout(
  nodeId: string, 
  mode: 'fullscreen' | 'normal',
  gridLayout: GridItem[]
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    next.set(nodeId, {
      ...current,
      [mode]: { ...current[mode], gridLayout },
      updatedAt: Date.now()
    });
    return next;
  });
}

export function updateSizeOverride(
  nodeId: string, 
  mode: 'fullscreen' | 'normal',
  blockId: string, 
  override: BlockSizeOverride
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultNodeConfig('unknown');
    next.set(nodeId, {
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
    if (tabState) childIds = tabState.children.slice(1);
    
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

// ============ 查询 ============

export function getUsedTabBlockIds(nodeId: string, mode: 'fullscreen' | 'normal'): string[] {
  const config = getNodeConfig(nodeId);
  if (!config) return [];
  const ids: string[] = [];
  for (const tabState of Object.values(config[mode].tabStates)) {
    ids.push(...tabState.children.slice(1));
  }
  return ids;
}

// ============ 订阅 ============

export function subscribeNodeConfig(
  nodeId: string,
  callback: (config: NodeConfig | undefined) => void
): () => void {
  return nodeLayoutStore.subscribe(() => {
    callback(nodeLayoutStore.state.get(nodeId));
  });
}

// ============ 导出/导入 ============

export function exportNodeConfig(nodeId: string): string | null {
  const config = getNodeConfig(nodeId);
  return config ? JSON.stringify(config, null, 2) : null;
}

export function importNodeConfig(nodeId: string, json: string): boolean {
  try {
    setNodeConfig(nodeId, JSON.parse(json) as NodeConfig);
    return true;
  } catch {
    return false;
  }
}
