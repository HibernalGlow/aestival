/**
 * 节点状态存储 - 使用 TanStack Store + localStorage 持久化
 * 用于在全屏/普通模式切换时保持节点内部状态
 * 支持页面刷新后恢复状态
 */

import { Store } from '@tanstack/store';

// localStorage key
const STORAGE_KEY = 'aestival-node-states';

// 节点状态 Map 类型
type NodeStatesMap = Map<string, unknown>;

/**
 * 从 localStorage 加载状态
 */
function loadFromStorage(): NodeStatesMap {
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

/**
 * 保存状态到 localStorage
 */
function saveToStorage(states: NodeStatesMap): void {
  if (typeof window === 'undefined') return;
  try {
    const obj = Object.fromEntries(states);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  } catch (e) {
    console.warn('[nodeStateStore] Failed to save to localStorage:', e);
  }
}

// 创建 TanStack Store，从 localStorage 初始化
export const nodeStateStore = new Store<NodeStatesMap>(loadFromStorage());

// 订阅变化，自动保存到 localStorage
nodeStateStore.subscribe(() => {
  saveToStorage(nodeStateStore.state);
});

/**
 * 获取节点状态
 */
export function getNodeState<T>(nodeId: string): T | undefined {
  return nodeStateStore.state.get(nodeId) as T | undefined;
}

/**
 * 设置节点状态（完全覆盖）
 */
export function setNodeState<T>(nodeId: string, state: T): void {
  nodeStateStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeId, state);
    return next;
  });
}

/**
 * 更新节点状态（合并）
 */
export function updateNodeState<T>(nodeId: string, partial: Partial<T>): void {
  nodeStateStore.setState((prev) => {
    const next = new Map(prev);
    const current = (next.get(nodeId) || {}) as T;
    next.set(nodeId, { ...current, ...partial });
    return next;
  });
}

/**
 * 删除节点状态
 */
export function deleteNodeState(nodeId: string): void {
  nodeStateStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeId);
    return next;
  });
}

/**
 * 清空所有状态
 */
export function clearNodeStates(): void {
  nodeStateStore.setState(() => new Map());
}

/**
 * 订阅特定节点的状态变化
 */
export function subscribeNodeState<T>(
  nodeId: string,
  callback: (state: T | undefined) => void
): () => void {
  return nodeStateStore.subscribe(() => {
    callback(nodeStateStore.state.get(nodeId) as T | undefined);
  });
}
