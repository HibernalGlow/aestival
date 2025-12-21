/**
 * Owithu 节点区块配置
 * Windows 右键菜单注册工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FileText, Settings, Play, ScrollText, MousePointer } from '@lucide/svelte';

export const OWITHU_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '配置文件', icon: FileText, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '选项', icon: Settings, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'entries', title: '菜单项', icon: MousePointer, iconClass: 'text-green-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: ScrollText, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const OWITHU_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'entries', x: 0, y: 2, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'operation', x: 2, y: 2, w: 1, h: 3, minW: 1, minH: 1 },
  { id: 'log', x: 0, y: 5, w: 3, h: 2, minW: 1, minH: 1 }
];
