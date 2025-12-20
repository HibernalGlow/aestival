/**
 * 全屏节点状态管理
 * 用于控制节点的全屏显示
 * 
 * 支持两种模式：
 * 1. 通过 nodeId 打开已存在的节点
 * 2. 通过 nodeType 直接打开（用于面板预览）
 */
import { writable, get } from 'svelte/store';

export interface FullscreenNodeState {
  isOpen: boolean;
  nodeId: string | null;
  nodeType: string | null;  // 新增：支持直接用类型打开
}

const initialState: FullscreenNodeState = {
  isOpen: false,
  nodeId: null,
  nodeType: null
};

function createFullscreenNodeStore() {
  const { subscribe, set } = writable<FullscreenNodeState>(initialState);

  return {
    subscribe,
    
    /** 打开全屏节点 - 通过 nodeId（已存在的节点） */
    open(nodeId: string) {
      set({
        isOpen: true,
        nodeId,
        nodeType: null
      });
    },
    
    /** 打开全屏节点 - 通过类型（面板预览，无需先添加节点） */
    openByType(nodeType: string) {
      set({
        isOpen: true,
        nodeId: null,
        nodeType
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
