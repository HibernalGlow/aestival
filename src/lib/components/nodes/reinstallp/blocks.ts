/**
 * Reinstallp 节点区块配置
 * Python 可编辑包重新安装工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Settings, Play, ScrollText, List } from '@lucide/svelte';

export const REINSTALLP_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '扫描路径', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '选项', icon: Settings, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'projects', title: '项目列表', icon: List, iconClass: 'text-green-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: ScrollText, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const REINSTALLP_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 1, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'projects', x: 0, y: 4, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 0, y: 8, w: 2, h: 2, minW: 1, minH: 1 }
];
