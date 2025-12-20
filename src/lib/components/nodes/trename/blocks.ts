/**
 * Trename 节点区块配置
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, FilePenLine, Play, FolderTree, RefreshCw, Upload, Settings2, Copy } from '@lucide/svelte';

export const TRENAME_BLOCKS: BlockDefinition[] = [
  { id: 'path', title: '扫描路径', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'scan', title: '扫描', icon: RefreshCw, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: false },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'stats', title: '统计', icon: FilePenLine, iconClass: 'text-yellow-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'importExport', title: '导入/导出', icon: Upload, iconClass: 'text-muted-foreground', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '高级选项', icon: Settings2, iconClass: 'text-muted-foreground', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'tree', title: '文件树', icon: FolderTree, iconClass: 'text-yellow-500', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const TRENAME_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'importExport', x: 2, y: 2, w: 2, h: 1, minW: 1, minH: 1 },
  { id: 'tree', x: 0, y: 3, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'options', x: 2, y: 3, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'log', x: 2, y: 5, w: 2, h: 2, minW: 1, minH: 1 }
];
