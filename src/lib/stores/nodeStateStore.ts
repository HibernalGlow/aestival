/**
 * 节点状态存储
 * 用于在全屏/普通模式切换时保持节点内部状态
 * 使用 Map 按节点 ID 存储任意状态对象
 */

import { writable, get } from 'svelte/store';

// 节点状态 Map: nodeId -> state object
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const nodeStates = writable<Map<string, any>>(new Map());

export const nodeStateStore = {
  /**
   * 获取节点状态
   */
  get<T>(nodeId: string): T | undefined {
    return get(nodeStates).get(nodeId) as T | undefined;
  },

  /**
   * 设置节点状态（完全覆盖）
   */
  set<T>(nodeId: string, state: T): void {
    nodeStates.update(map => {
      map.set(nodeId, state);
      return new Map(map);
    });
  },

  /**
   * 更新节点状态（合并）
   */
  update<T>(nodeId: string, partial: Partial<T>): void {
    nodeStates.update(map => {
      const current = map.get(nodeId) || {};
      map.set(nodeId, { ...current, ...partial });
      return new Map(map);
    });
  },

  /**
   * 删除节点状态
   */
  delete(nodeId: string): void {
    nodeStates.update(map => {
      map.delete(nodeId);
      return new Map(map);
    });
  },

  /**
   * 清空所有状态
   */
  clear(): void {
    nodeStates.set(new Map());
  },

  /**
   * 订阅特定节点的状态变化
   */
  subscribe: nodeStates.subscribe
};

/**
 * 创建节点状态的响应式 hook
 * 用于在 Svelte 组件中方便地读写状态
 */
export function useNodeState<T>(
  nodeId: string,
  initialState: T
): {
  state: T;
  setState: (newState: T) => void;
  updateState: (partial: Partial<T>) => void;
} {
  // 从存储中获取或使用初始状态
  let state = $state<T>(nodeStateStore.get<T>(nodeId) ?? initialState);

  // 如果存储中没有，初始化
  if (!nodeStateStore.get(nodeId)) {
    nodeStateStore.set(nodeId, initialState);
  }

  return {
    get state() { return state; },
    setState(newState: T) {
      state = newState;
      nodeStateStore.set(nodeId, newState);
    },
    updateState(partial: Partial<T>) {
      state = { ...state, ...partial };
      nodeStateStore.update(nodeId, partial);
    }
  };
}
