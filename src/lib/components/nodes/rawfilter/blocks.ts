/**
 * Rawfilter 节点区块配置
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Settings2, Play, Search, Copy } from '@lucide/svelte';

export const RAWFILTER_BLOCKS: BlockDefinition[] = [
  { id: 'path', title: '目标路径', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '过滤选项', icon: Settings2, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'stats', title: '统计', icon: Search, iconClass: 'text-yellow-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'progress', title: '状态', icon: Search, iconClass: 'text-muted-foreground', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const RAWFILTER_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 1, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'progress', x: 2, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'log', x: 0, y: 4, w: 4, h: 3, minW: 1, minH: 1 }
];
