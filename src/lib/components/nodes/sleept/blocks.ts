/**
 * Sleept 节点区块配置
 * 系统定时器工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Clock, Settings, Play, Activity, Copy } from '@lucide/svelte';

export const SLEEPT_BLOCKS: BlockDefinition[] = [
  { id: 'mode', title: '模式选择', icon: Settings, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'timer', title: '定时设置', icon: Clock, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'monitor', title: '监控设置', icon: Activity, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const SLEEPT_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'mode', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'timer', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'monitor', x: 0, y: 2, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'operation', x: 2, y: 2, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 0, y: 5, w: 4, h: 2, minW: 1, minH: 1 }
];
