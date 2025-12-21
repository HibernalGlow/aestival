/**
 * Linku 节点区块配置
 * 软链接管理工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Link, Play, ScrollText, List } from '@lucide/svelte';

export const LINKU_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '源路径', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'target', title: '目标路径', icon: Link, iconClass: 'text-green-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'links', title: '已记录链接', icon: List, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: ScrollText, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const LINKU_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'target', x: 0, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 4, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'links', x: 0, y: 6, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 0, y: 9, w: 2, h: 2, minW: 1, minH: 1 }
];
