/**
 * 区块注册表 - 类型定义和注册逻辑
 * 
 * 各节点的 block 配置已拆分到各自目录下的 blocks.ts
 * 此文件只负责类型定义、注册表管理和工具函数
 */
import type { Component } from 'svelte';
import type { GridItem } from '$lib/components/ui/dashboard-grid';

// ============ 类型定义 ============

/** 区块定义 */
export interface BlockDefinition {
  /** 区块 ID */
  id: string;
  /** 显示标题 */
  title: string;
  /** 图标组件 */
  icon?: Component;
  /** 图标颜色类 */
  iconClass?: string;
  /** 是否可折叠 */
  collapsible?: boolean;
  /** 默认展开 */
  defaultExpanded?: boolean;
  /** 占满高度 */
  fullHeight?: boolean;
  /** 隐藏标题栏 */
  hideHeader?: boolean;
  /** 紧凑模式 */
  compact?: boolean;
  /** 普通模式下的 grid 跨度 (col-span-X) */
  colSpan?: 1 | 2;
  /** 普通模式下是否可见 */
  visibleInNormal?: boolean;
  /** 全屏模式下是否可见 */
  visibleInFullscreen?: boolean;
  /** Tab 区块特有：子区块 ID 列表 */
  tabChildren?: string[];
  /** 是否为 Tab 容器类型 */
  isTabContainer?: boolean;
}

/** Tab 区块配置 */
export interface TabBlockConfig {
  id: string;
  children: string[];
  activeTab: number;
}

/** Tab 区块状态（用于持久化） */
export interface TabBlockState {
  activeTab: number;
  children: string[];
}

/** 扩展 GridItem 以支持 Tab 区块数据 */
export interface TabGridItem extends GridItem {
  tabData?: TabBlockState;
}

/** 区块配置（运行时状态） */
export interface BlockConfig {
  id: string;
  visible: boolean;
  expanded: boolean;
  order: number;
}

/** 节点区块布局配置 */
export interface NodeBlockLayout {
  nodeType: string;
  blocks: BlockDefinition[];
  defaultGridLayout: GridItem[];
}

// ============ 导入各节点的 block 配置 ============

import { FINDZ_BLOCKS, FINDZ_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/findz/blocks';
import { REPACKU_BLOCKS, REPACKU_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/repacku/blocks';
import { TRENAME_BLOCKS, TRENAME_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/trename/blocks';
import { ENGINEV_BLOCKS, ENGINEV_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/enginev/blocks';
import { RAWFILTER_BLOCKS, RAWFILTER_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/rawfilter/blocks';
import { CRASHU_BLOCKS, CRASHU_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/crashu/blocks';
import { MIGRATEF_BLOCKS, MIGRATEF_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/migratefnode/blocks';
import { FORMATV_BLOCKS, FORMATV_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/formatv/blocks';
import { BANDIA_BLOCKS, BANDIA_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/bandia/blocks';
import { DISSOLVEF_BLOCKS, DISSOLVEF_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/dissolvef/blocks';
import { SLEEPT_BLOCKS, SLEEPT_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/sleept/blocks';
import { OWITHU_BLOCKS, OWITHU_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/owithu/blocks';
import { LINKU_BLOCKS, LINKU_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/linku/blocks';
import { SCOOLP_BLOCKS, SCOOLP_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/scoolp/blocks';
import { REINSTALLP_BLOCKS, REINSTALLP_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/reinstallp/blocks';
import { RECYCLEU_BLOCKS, RECYCLEU_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/recycleu/blocks';
import { ENCODEB_BLOCKS, ENCODEB_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/encodeb/blocks';
import { KAVVKA_BLOCKS, KAVVKA_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/kavvka/blocks';
import { LINEDUP_BLOCKS, LINEDUP_DEFAULT_GRID_LAYOUT } from '$lib/components/nodes/linedup/blocks';

// 重新导出供外部使用
export { FINDZ_BLOCKS, FINDZ_DEFAULT_GRID_LAYOUT };
export { REPACKU_BLOCKS, REPACKU_DEFAULT_GRID_LAYOUT };
export { TRENAME_BLOCKS, TRENAME_DEFAULT_GRID_LAYOUT };
export { ENGINEV_BLOCKS, ENGINEV_DEFAULT_GRID_LAYOUT };
export { RAWFILTER_BLOCKS, RAWFILTER_DEFAULT_GRID_LAYOUT };
export { CRASHU_BLOCKS, CRASHU_DEFAULT_GRID_LAYOUT };
export { MIGRATEF_BLOCKS, MIGRATEF_DEFAULT_GRID_LAYOUT };
export { FORMATV_BLOCKS, FORMATV_DEFAULT_GRID_LAYOUT };
export { BANDIA_BLOCKS, BANDIA_DEFAULT_GRID_LAYOUT };
export { DISSOLVEF_BLOCKS, DISSOLVEF_DEFAULT_GRID_LAYOUT };
export { SLEEPT_BLOCKS, SLEEPT_DEFAULT_GRID_LAYOUT };
export { OWITHU_BLOCKS, OWITHU_DEFAULT_GRID_LAYOUT };
export { LINKU_BLOCKS, LINKU_DEFAULT_GRID_LAYOUT };
export { SCOOLP_BLOCKS, SCOOLP_DEFAULT_GRID_LAYOUT };
export { REINSTALLP_BLOCKS, REINSTALLP_DEFAULT_GRID_LAYOUT };
export { RECYCLEU_BLOCKS, RECYCLEU_DEFAULT_GRID_LAYOUT };
export { ENCODEB_BLOCKS, ENCODEB_DEFAULT_GRID_LAYOUT };
export { KAVVKA_BLOCKS, KAVVKA_DEFAULT_GRID_LAYOUT };
export { LINEDUP_BLOCKS, LINEDUP_DEFAULT_GRID_LAYOUT };

// ============ 注册表 ============
export const nodeBlockRegistry: Record<string, NodeBlockLayout> = {
  findz: { nodeType: 'findz', blocks: FINDZ_BLOCKS, defaultGridLayout: FINDZ_DEFAULT_GRID_LAYOUT },
  repacku: { nodeType: 'repacku', blocks: REPACKU_BLOCKS, defaultGridLayout: REPACKU_DEFAULT_GRID_LAYOUT },
  trename: { nodeType: 'trename', blocks: TRENAME_BLOCKS, defaultGridLayout: TRENAME_DEFAULT_GRID_LAYOUT },
  enginev: { nodeType: 'enginev', blocks: ENGINEV_BLOCKS, defaultGridLayout: ENGINEV_DEFAULT_GRID_LAYOUT },
  rawfilter: { nodeType: 'rawfilter', blocks: RAWFILTER_BLOCKS, defaultGridLayout: RAWFILTER_DEFAULT_GRID_LAYOUT },
  crashu: { nodeType: 'crashu', blocks: CRASHU_BLOCKS, defaultGridLayout: CRASHU_DEFAULT_GRID_LAYOUT },
  migratef: { nodeType: 'migratef', blocks: MIGRATEF_BLOCKS, defaultGridLayout: MIGRATEF_DEFAULT_GRID_LAYOUT },
  formatv: { nodeType: 'formatv', blocks: FORMATV_BLOCKS, defaultGridLayout: FORMATV_DEFAULT_GRID_LAYOUT },
  bandia: { nodeType: 'bandia', blocks: BANDIA_BLOCKS, defaultGridLayout: BANDIA_DEFAULT_GRID_LAYOUT },
  dissolvef: { nodeType: 'dissolvef', blocks: DISSOLVEF_BLOCKS, defaultGridLayout: DISSOLVEF_DEFAULT_GRID_LAYOUT },
  sleept: { nodeType: 'sleept', blocks: SLEEPT_BLOCKS, defaultGridLayout: SLEEPT_DEFAULT_GRID_LAYOUT },
  owithu: { nodeType: 'owithu', blocks: OWITHU_BLOCKS, defaultGridLayout: OWITHU_DEFAULT_GRID_LAYOUT },
  linku: { nodeType: 'linku', blocks: LINKU_BLOCKS, defaultGridLayout: LINKU_DEFAULT_GRID_LAYOUT },
  scoolp: { nodeType: 'scoolp', blocks: SCOOLP_BLOCKS, defaultGridLayout: SCOOLP_DEFAULT_GRID_LAYOUT },
  reinstallp: { nodeType: 'reinstallp', blocks: REINSTALLP_BLOCKS, defaultGridLayout: REINSTALLP_DEFAULT_GRID_LAYOUT },
  recycleu: { nodeType: 'recycleu', blocks: RECYCLEU_BLOCKS, defaultGridLayout: RECYCLEU_DEFAULT_GRID_LAYOUT },
  encodeb: { nodeType: 'encodeb', blocks: ENCODEB_BLOCKS, defaultGridLayout: ENCODEB_DEFAULT_GRID_LAYOUT },
  kavvka: { nodeType: 'kavvka', blocks: KAVVKA_BLOCKS, defaultGridLayout: KAVVKA_DEFAULT_GRID_LAYOUT },
  linedup: { nodeType: 'linedup', blocks: LINEDUP_BLOCKS, defaultGridLayout: LINEDUP_DEFAULT_GRID_LAYOUT }
};

// ============ 工具函数 ============

/** 获取节点的区块布局配置 */
export function getNodeBlockLayout(nodeType: string): NodeBlockLayout | undefined {
  return nodeBlockRegistry[nodeType];
}

/** 获取区块定义 */
export function getBlockDefinition(nodeType: string, blockId: string): BlockDefinition | undefined {
  const layout = nodeBlockRegistry[nodeType];
  return layout?.blocks.find(b => b.id === blockId);
}

/** 获取 Tab 区块的子区块定义列表 */
export function getTabBlockChildren(nodeType: string, childIds: string[]): BlockDefinition[] {
  const layout = nodeBlockRegistry[nodeType];
  if (!layout) return [];
  return childIds
    .map(id => layout.blocks.find(b => b.id === id))
    .filter((b): b is BlockDefinition => b !== undefined);
}

/** 序列化 TabBlockConfig */
export function serializeTabBlockConfig(config: TabBlockConfig): string {
  return JSON.stringify(config);
}

/** 反序列化 TabBlockConfig */
export function deserializeTabBlockConfig(json: string): TabBlockConfig | null {
  try {
    const parsed = JSON.parse(json);
    if (typeof parsed.id === 'string' && Array.isArray(parsed.children) && typeof parsed.activeTab === 'number') {
      return parsed as TabBlockConfig;
    }
    return null;
  } catch {
    return null;
  }
}
