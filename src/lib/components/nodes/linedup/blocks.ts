/**
 * Linedup 节点区块配置
 * 行去重工具 - 过滤包含特定内容的行
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FileText, Filter, Play, List } from '@lucide/svelte';

export const LINEDUP_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '源内容', icon: FileText, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'filter', title: '过滤条件', icon: Filter, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'result', title: '结果', icon: List, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: FileText, iconClass: 'text-muted-foreground', colSpan: 1, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const LINEDUP_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'filter', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 3, minW: 1, minH: 2 },
  { id: 'result', x: 1, y: 2, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 3, minW: 1, minH: 1 }
];
