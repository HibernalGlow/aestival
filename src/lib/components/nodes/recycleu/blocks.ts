/**
 * Recycleu 节点区块配置
 * 回收站自动清理工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Trash2, Settings, Play, Gauge, Copy } from '@lucide/svelte';

export const RECYCLEU_BLOCKS: BlockDefinition[] = [
  { id: 'settings', title: '清理设置', icon: Settings, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'status', title: '状态', icon: Gauge, iconClass: 'text-cyan-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const RECYCLEU_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'settings', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'status', x: 2, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 1, y: 2, w: 3, h: 3, minW: 1, minH: 1 }
];
