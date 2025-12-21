/**
 * Crashu 节点区块配置
 * 文件夹名称相似度检测与批量移动
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Folder, Target, Sliders, Play, Zap, List, Copy } from '@lucide/svelte';

export const CRASHU_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '源目录', icon: Folder, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'target', title: '目标配置', icon: Target, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '检测选项', icon: Sliders, iconClass: 'text-purple-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'stats', title: '统计', icon: Zap, iconClass: 'text-yellow-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'results', title: '匹配结果', icon: List, iconClass: 'text-green-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 1, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const CRASHU_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'target', x: 2, y: 0, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'options', x: 0, y: 3, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 2, y: 3, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 3, y: 3, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'results', x: 0, y: 5, w: 3, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 3, y: 5, w: 1, h: 4, minW: 1, minH: 1 }
];
