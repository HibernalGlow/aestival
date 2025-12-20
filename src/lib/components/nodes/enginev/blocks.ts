/**
 * EngineV 节点区块配置
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Filter, BarChart3, Play, Pencil, Grid3X3, Copy } from '@lucide/svelte';

export const ENGINEV_BLOCKS: BlockDefinition[] = [
  { id: 'path', title: '工坊路径', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'filter', title: '过滤条件', icon: Filter, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'stats', title: '统计', icon: BarChart3, iconClass: 'text-yellow-500', colSpan: 1, collapsible: true, defaultExpanded: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'rename', title: '重命名', icon: Pencil, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'gallery', title: '壁纸列表', icon: Grid3X3, iconClass: 'text-purple-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const ENGINEV_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'filter', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 1, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'rename', x: 2, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'gallery', x: 0, y: 4, w: 3, h: 4, minW: 2, minH: 2 },
  { id: 'log', x: 3, y: 4, w: 1, h: 4, minW: 1, minH: 1 }
];
