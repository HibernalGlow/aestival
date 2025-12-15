/**
 * TrenameNode 工具函数和类型定义
 */
import type { GridItem } from '$lib/components/ui/dashboard-grid';

// ==================== 类型定义 ====================

/** 文件节点 */
export interface FileNode {
  src: string;
  tgt: string;
}

/** 目录节点 */
export interface DirNode {
  src_dir: string;
  tgt_dir: string;
  children: TreeNode[];
}

/** 树节点（文件或目录） */
export type TreeNode = FileNode | DirNode;

/** 操作历史记录 */
export interface OperationRecord {
  id: string;
  time: string;
  count: number;
  canUndo: boolean;
}

/** 节点运行阶段 */
export type Phase = 'idle' | 'scanning' | 'ready' | 'renaming' | 'completed' | 'error';

/** 统计信息 */
export interface TrenameStats {
  total: number;
  pending: number;
  ready: number;
  conflicts: number;
}

/** 节点持久化状态 */
export interface TrenameState {
  phase: Phase;
  logs: string[];
  showTree: boolean;
  showOptions: boolean;
  showJsonInput: boolean;
  jsonInputText: string;
  scanPath: string;
  includeHidden: boolean;
  excludeExts: string;
  maxLines: number;
  useCompact: boolean;
  basePath: string;
  dryRun: boolean;
  treeData: TreeNode[];
  segments: string[];
  currentSegment: number;
  stats: TrenameStats;
  conflicts: string[];
  lastOperationId: string;
  operationHistory: OperationRecord[];
  gridLayout?: GridItem[];
}

// ==================== 工具函数 ====================

/** 判断节点是否为目录 */
export function isDir(node: TreeNode): node is DirNode {
  return 'src_dir' in node;
}

/** 获取节点状态：pending(待翻译) / ready(就绪) / same(无变化) */
export function getNodeStatus(node: TreeNode): 'pending' | 'ready' | 'same' {
  const tgt = isDir(node) ? node.tgt_dir : node.tgt;
  const src = isDir(node) ? node.src_dir : node.src;
  if (!tgt || tgt === '') return 'pending';
  if (tgt === src) return 'same';
  return 'ready';
}

/** 解析 JSON 字符串为树结构 */
export function parseTree(json: string): TreeNode[] {
  try {
    return JSON.parse(json).root || [];
  } catch {
    return [];
  }
}

/** 获取状态对应的 CSS 类名 */
export function getStatusColorClass(status: 'pending' | 'ready' | 'same'): string {
  switch (status) {
    case 'ready': return 'bg-green-500';
    case 'pending': return 'bg-yellow-500';
    case 'same': return 'bg-gray-300';
  }
}

/** 获取阶段对应的边框样式 */
export function getPhaseBorderClass(phase: Phase): string {
  switch (phase) {
    case 'error': return 'border-destructive/50';
    case 'completed': return 'border-primary/50';
    case 'scanning':
    case 'renaming': return 'border-primary shadow-sm';
    default: return 'border-border';
  }
}

/** 默认 GridStack 布局配置 */
export const DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
  { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
  { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
  { id: 'importExport', x: 0, y: 2, w: 2, h: 1, minW: 2, minH: 1 },
  { id: 'tree', x: 0, y: 3, w: 3, h: 4, minW: 2, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 5, minW: 1, minH: 2 }
];

/** 默认统计信息 */
export const DEFAULT_STATS: TrenameStats = {
  total: 0,
  pending: 0,
  ready: 0,
  conflicts: 0
};

/** 默认排除的文件扩展名 */
export const DEFAULT_EXCLUDE_EXTS = '.json,.txt,.html,.htm,.md,.log';

/** 生成下载文件名 */
export function generateDownloadFilename(segmentIndex: number): string {
  const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  return `trename_seg${segmentIndex + 1}_${timestamp}.json`;
}