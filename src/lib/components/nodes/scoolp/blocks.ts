/**
 * Scoolp 节点区块配置
 * Scoop 包管理工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Package, Settings, Play, ScrollText, List } from '@lucide/svelte';

export const SCOOLP_BLOCKS: BlockDefinition[] = [
  { id: 'packages', title: '包管理', icon: Package, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'buckets', title: 'Buckets', icon: List, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'status', title: '状态', icon: Settings, iconClass: 'text-cyan-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: ScrollText, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const SCOOLP_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'packages', x: 0, y: 0, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'buckets', x: 0, y: 3, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 1, y: 3, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'status', x: 0, y: 5, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'log', x: 0, y: 7, w: 2, h: 2, minW: 1, minH: 1 }
];
