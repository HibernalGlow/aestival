/**
 * MigrateF 节点区块配置
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderInput, FolderOutput, Settings2, Play, BarChart3, ArrowRight, Copy } from '@lucide/svelte';

export const MIGRATEF_BLOCKS: BlockDefinition[] = [
  { id: 'path', title: '路径配置', icon: FolderInput, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'source', title: '源目录', icon: FolderInput, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: false, visibleInFullscreen: true },
  { id: 'target', title: '目标目录', icon: FolderOutput, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: false, visibleInFullscreen: true },
  { id: 'options', title: '迁移选项', icon: Settings2, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'stats', title: '统计', icon: BarChart3, iconClass: 'text-yellow-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'progress', title: '状态', icon: ArrowRight, iconClass: 'text-muted-foreground', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const MIGRATEF_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'target', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 0, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 2, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 3, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'progress', x: 0, y: 4, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'log', x: 2, y: 4, w: 2, h: 2, minW: 1, minH: 1 }
];
