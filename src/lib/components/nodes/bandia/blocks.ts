/**
 * Bandia 节点区块配置
 * 批量解压工具 - 使用 Bandizip
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FileArchive, FolderOpen, Play, Trash2, Copy } from '@lucide/svelte';

export const BANDIA_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '压缩包来源', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '选项', icon: Trash2, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'files', title: '待解压文件', icon: FileArchive, iconClass: 'text-blue-500', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const BANDIA_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'files', x: 0, y: 2, w: 3, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 4, minW: 1, minH: 1 }
];
