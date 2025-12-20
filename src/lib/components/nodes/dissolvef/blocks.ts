/**
 * Dissolvef 节点区块配置
 * 文件夹解散工具 - 解散嵌套/单媒体/单压缩包文件夹
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Settings, Play, FileText, Copy } from '@lucide/svelte';

export const DISSOLVEF_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '路径来源', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'mode', title: '解散模式', icon: Settings, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '选项', icon: Settings, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'result', title: '结果', icon: FileText, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const DISSOLVEF_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'mode', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'result', x: 1, y: 2, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 4, minW: 1, minH: 1 }
];
