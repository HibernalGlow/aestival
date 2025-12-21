/**
 * 区块编辑模式 Context 定义
 * 用于在 NodeWrapper 和 NodeLayoutRenderer 之间传递编辑模式状态
 */
import type { Writable } from "svelte/store";

// Context key
export const BLOCK_EDIT_MODE_KEY = Symbol('blockEditMode');

// Context 类型
export interface BlockEditModeContext {
  editMode: Writable<boolean>;
  isFullscreen: boolean;
}
