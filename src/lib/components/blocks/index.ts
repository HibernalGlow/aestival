/**
 * 区块系统导出
 */
export { default as BlockCard } from './BlockCard.svelte';
export { default as TabGroupCard } from './TabGroupCard.svelte';
export { default as TabConfigPanel } from './TabConfigPanel.svelte';
export { default as NodeLayoutRenderer } from './NodeLayoutRenderer.svelte';
export * from './blockRegistry';

// 旧版兼容（已废弃，将在后续版本移除）
export { default as TabBlockCard } from './TabBlockCard.svelte';
