/**
 * 全屏节点状态管理
 * 用于控制节点的全屏显示
 */
import { writable, get } from 'svelte/store';

export interface FullscreenNodeState {
  isOpen: boolean;
  nodeId: string | null;
}

const initialState: FullscreenNodeState = {
  isOpen: false,
  nodeId: null
};

function createFullscreenNodeStore() {
  const { subscribe, set } = writable<FullscreenNodeState>(initialState);

  return {
    subscribe,
    
    /** 打开全屏节点 */
    open(nodeId: string) {
      set({
        isOpen: true,
        nodeId
      });
    },
    
    /** 关闭全屏节点 */
    close() {
      set(initialState);
    },
    
    /** 检查某个节点是否在全屏模式 */
    isFullscreen(nodeId: string): boolean {
      const state = get({ subscribe });
      return state.isOpen && state.nodeId === nodeId;
    }
  };
}

export const fullscreenNodeStore = createFullscreenNodeStore();
