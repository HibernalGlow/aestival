/**
 * 节点区块系统 - 类型定义
 * 配置驱动的统一区块，自动适配普通模式和全屏模式
 */
import type { Component } from 'svelte';
import type { GridItem } from '$lib/components/ui/dashboard-grid';

/** 区块定义 */
export interface BlockDefinition {
  id: string;
  title: string;
  icon?: Component;
  /** 普通模式下的布局配置 */
  normalLayout: {
    /** 列跨度 (1-2) */
    colSpan?: 1 | 2;
    /** 行跨度 */
    rowSpan?: number;
    /** 是否在普通模式下隐藏 */
    hidden?: boolean;
    /** 优先级（数字越小越靠前） */
    order?: number;
  };
  /** 全屏模式下的默认 GridStack 配置 */
  fullscreenLayout: {
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
  };
  /** 是否可折叠 */
  collapsible?: boolean;
  /** 默认折叠状态 */
  defaultCollapsed?: boolean;
}

/** 区块配置（运行时状态） */
export interface BlockConfig {
  id: string;
  visible: boolean;
  collapsed: boolean;
  /** 全屏模式下的当前位置 */
  gridItem?: GridItem;
}

/** 节点区块注册表 */
export interface NodeBlockRegistry {
  nodeType: string;
  blocks: BlockDefinition[];
}

/** 从区块定义生成默认 GridItem 列表 */
export function getDefaultGridLayout(blocks: BlockDefinition[]): GridItem[] {
  return blocks.map(block => ({
    id: block.id,
    x: block.fullscreenLayout.x,
    y: block.fullscreenLayout.y,
    w: block.fullscreenLayout.w,
    h: block.fullscreenLayout.h,
    minW: block.fullscreenLayout.minW,
    minH: block.fullscreenLayout.minH,
  }));
}

/** 获取普通模式下可见的区块（按 order 排序） */
export function getNormalModeBlocks(blocks: BlockDefinition[]): BlockDefinition[] {
  return blocks
    .filter(b => !b.normalLayout.hidden)
    .sort((a, b) => (a.normalLayout.order ?? 99) - (b.normalLayout.order ?? 99));
}
