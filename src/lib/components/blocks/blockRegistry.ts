/**
 * 区块注册表 - 定义所有可用的区块类型
 * 参考 neoview 的 cardRegistry 设计
 */
import type { Component } from 'svelte';
import type { GridItem } from '$lib/components/ui/dashboard-grid';

// 区块定义
export interface BlockDefinition {
  /** 区块 ID */
  id: string;
  /** 显示标题 */
  title: string;
  /** 图标组件 */
  icon?: Component;
  /** 图标颜色类 */
  iconClass?: string;
  /** 是否可折叠 */
  collapsible?: boolean;
  /** 默认展开 */
  defaultExpanded?: boolean;
  /** 占满高度 */
  fullHeight?: boolean;
  /** 隐藏标题栏 */
  hideHeader?: boolean;
  /** 紧凑模式 */
  compact?: boolean;
  /** 普通模式下的 grid 跨度 (col-span-X) */
  colSpan?: 1 | 2;
  /** 普通模式下是否可见 */
  visibleInNormal?: boolean;
  /** 全屏模式下是否可见 */
  visibleInFullscreen?: boolean;
}

// 区块配置（运行时状态）
export interface BlockConfig {
  id: string;
  visible: boolean;
  expanded: boolean;
  order: number;
}

// 节点区块布局配置
export interface NodeBlockLayout {
  /** 节点类型 */
  nodeType: string;
  /** 区块定义列表 */
  blocks: BlockDefinition[];
  /** 全屏模式默认 GridStack 布局 */
  defaultGridLayout: GridItem[];
}

// ============ Repacku 节点区块定义 ============
import { 
  FolderOpen, FileText, Play, FolderTree, Package, Copy
} from '@lucide/svelte';

export const REPACKU_BLOCKS: BlockDefinition[] = [
  {
    id: 'path',
    title: '目标路径',
    icon: FolderOpen,
    iconClass: 'text-primary',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'types',
    title: '文件类型',
    icon: FileText,
    iconClass: 'text-blue-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'operation',
    title: '操作',
    icon: Play,
    iconClass: 'text-green-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'stats',
    title: '统计',
    icon: FolderTree,
    iconClass: 'text-yellow-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'progress',
    title: '状态',
    icon: Package,
    iconClass: 'text-muted-foreground',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'tree',
    title: '文件夹结构',
    icon: FolderTree,
    iconClass: 'text-yellow-500',
    colSpan: 2,
    fullHeight: true,
    collapsible: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'log',
    title: '日志',
    icon: Copy,
    iconClass: 'text-muted-foreground',
    colSpan: 2,
    collapsible: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  }
];

export const REPACKU_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'progress', x: 2, y: 2, w: 2, h: 1, minW: 1, minH: 1 },
  { id: 'tree', x: 0, y: 3, w: 3, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 3, y: 3, w: 1, h: 4, minW: 1, minH: 1 }
];

// ============ Trename 节点区块定义 ============
import { FilePenLine, RefreshCw, Upload, Settings2 } from '@lucide/svelte';

export const TRENAME_BLOCKS: BlockDefinition[] = [
  {
    id: 'path',
    title: '扫描路径',
    icon: FolderOpen,
    iconClass: 'text-primary',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'scan',
    title: '扫描',
    icon: RefreshCw,
    iconClass: 'text-blue-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: false // 全屏模式合并到 path
  },
  {
    id: 'operation',
    title: '操作',
    icon: Play,
    iconClass: 'text-green-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'stats',
    title: '统计',
    icon: FilePenLine,
    iconClass: 'text-yellow-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'importExport',
    title: '导入/导出',
    icon: Upload,
    iconClass: 'text-muted-foreground',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'options',
    title: '高级选项',
    icon: Settings2,
    iconClass: 'text-muted-foreground',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'tree',
    title: '文件树',
    icon: FolderTree,
    iconClass: 'text-yellow-500',
    colSpan: 2,
    fullHeight: true,
    collapsible: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'log',
    title: '日志',
    icon: Copy,
    iconClass: 'text-muted-foreground',
    colSpan: 2,
    collapsible: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  }
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

// ============ EngineV 节点区块定义 ============
import { 
  Image, Filter, BarChart3, Pencil, Grid3X3, Video, Globe, Layers
} from '@lucide/svelte';

export const ENGINEV_BLOCKS: BlockDefinition[] = [
  {
    id: 'path',
    title: '工坊路径',
    icon: FolderOpen,
    iconClass: 'text-primary',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'filter',
    title: '过滤条件',
    icon: Filter,
    iconClass: 'text-blue-500',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'stats',
    title: '统计',
    icon: BarChart3,
    iconClass: 'text-yellow-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'operation',
    title: '操作',
    icon: Play,
    iconClass: 'text-green-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'rename',
    title: '重命名',
    icon: Pencil,
    iconClass: 'text-orange-500',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'gallery',
    title: '壁纸列表',
    icon: Grid3X3,
    iconClass: 'text-purple-500',
    colSpan: 2,
    fullHeight: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'log',
    title: '日志',
    icon: Copy,
    iconClass: 'text-muted-foreground',
    colSpan: 2,
    collapsible: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  }
];

export const ENGINEV_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'filter', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 1, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'rename', x: 2, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'gallery', x: 0, y: 4, w: 3, h: 4, minW: 2, minH: 2 },
  { id: 'log', x: 3, y: 4, w: 1, h: 4, minW: 1, minH: 1 }
];

// ============ 注册表 ============
export const nodeBlockRegistry: Record<string, NodeBlockLayout> = {
  repacku: {
    nodeType: 'repacku',
    blocks: REPACKU_BLOCKS,
    defaultGridLayout: REPACKU_DEFAULT_GRID_LAYOUT
  },
  trename: {
    nodeType: 'trename',
    blocks: TRENAME_BLOCKS,
    defaultGridLayout: TRENAME_DEFAULT_GRID_LAYOUT
  },
  enginev: {
    nodeType: 'enginev',
    blocks: ENGINEV_BLOCKS,
    defaultGridLayout: ENGINEV_DEFAULT_GRID_LAYOUT
  }
};

// 获取节点的区块布局配置
export function getNodeBlockLayout(nodeType: string): NodeBlockLayout | undefined {
  return nodeBlockRegistry[nodeType];
}

// 获取区块定义
export function getBlockDefinition(nodeType: string, blockId: string): BlockDefinition | undefined {
  const layout = nodeBlockRegistry[nodeType];
  return layout?.blocks.find(b => b.id === blockId);
}
