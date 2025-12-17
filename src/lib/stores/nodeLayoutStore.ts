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

/**
 * 获取或创建节点配置
 * 注意：使用 nodeType 作为 key，而不是 nodeId，这样同类型节点共享布局配置
 */
export function getOrCreateNodeConfig(
  nodeId: string, 
  nodeType: string,
  defaultFullscreenLayout: GridItem[] = [],
  defaultNormalLayout: GridItem[] = []
): NodeConfig {
  hydrateFromStorage();
  // 使用 nodeType 作为 key，而不是 nodeId
  const configKey = nodeType;
  const existing = nodeLayoutStore.state.get(configKey);
  
  if (existing) {
    // 验证并修复现有配置
    const fixed = validateAndFixConfig(existing);
    // 如果配置被修复了，保存修复后的版本
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

/** 按 nodeType 设置配置 */
function setNodeConfigByType(nodeType: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, { ...config, updatedAt: Date.now() });
    return next;
  });
}

export function deleteNodeConfig(nodeType: string): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeType);
    return next;
  });
}

// ============ 布局操作 ============
// 注意：所有函数使用 nodeType 作为 key，而不是 nodeId

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

export function updateTabState(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  state: TabBlockState
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    next.set(nodeType, {
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
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  blockIds: string[],
  removeFromLayout: boolean = true
): void {
  if (blockIds.length < 2) return;
  const tabId = blockIds[0];
  const otherBlockIds = blockIds.slice(1);
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    const modeState = current[mode];
    
    // 从布局中移除被合并的区块（保留第一个作为 Tab 容器）
    const newGridLayout = removeFromLayout 
      ? modeState.gridLayout.filter(item => !otherBlockIds.includes(item.id))
      : modeState.gridLayout;
    
    const newModeState = {
      ...modeState,
      gridLayout: newGridLayout,
      tabBlocks: [...modeState.tabBlocks, tabId],
      tabStates: { ...modeState.tabStates, [tabId]: { activeTab: 0, children: blockIds } }
    };
    
    next.set(nodeType, {
      ...current,
      [mode]: newModeState,
      updatedAt: Date.now()
    });
    return next;
  });
}

export function removeTabBlock(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  restoreToLayout: boolean = true,
  isFullscreen: boolean = false
): string[] {
  let childIds: string[] = [];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return prev;
    
    const modeState = current[mode];
    const tabState = modeState.tabStates[tabId];
    if (tabState) childIds = tabState.children.slice(1);
    
    const newTabStates = { ...modeState.tabStates };
    delete newTabStates[tabId];
    
    // 恢复被隐藏的区块到布局中
    let newGridLayout = modeState.gridLayout;
    if (restoreToLayout && childIds.length > 0) {
      const tabItem = modeState.gridLayout.find(item => item.id === tabId);
      const baseY = tabItem?.y ?? 0;
      const baseX = (tabItem?.x ?? 0) + (tabItem?.w ?? 2);
      
      const restoredItems: GridItem[] = childIds.map((childId, index) => ({
        id: childId,
        x: isFullscreen ? baseX : index % 2,
        y: isFullscreen ? baseY + index * 2 : Math.floor(index / 2) + baseY + 1,
        w: 1,
        h: isFullscreen ? 2 : 1,
        minW: 1,
        minH: 1
      }));
      
      newGridLayout = [...modeState.gridLayout, ...restoredItems];
    }
    
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...modeState,
        gridLayout: newGridLayout,
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

export function getUsedTabBlockIds(nodeType: string, mode: 'fullscreen' | 'normal'): string[] {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  if (!config) return [];
  const ids: string[] = [];
  for (const tabState of Object.values(config[mode].tabStates)) {
    ids.push(...tabState.children.slice(1));
  }
  return ids;
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
