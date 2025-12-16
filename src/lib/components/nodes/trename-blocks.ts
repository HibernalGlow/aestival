/**
 * TrenameNode 区块定义
 * 配置驱动的统一区块，自动适配普通模式和全屏模式
 */
import type { BlockDefinition } from '$lib/components/ui/node-blocks';
import { 
  FolderOpen, Play, FilePenLine, Upload, Folder, FileText
} from '@lucide/svelte';

/** TrenameNode 的所有区块定义 */
export const TRENAME_BLOCKS: BlockDefinition[] = [
  {
    id: 'path',
    title: '扫描路径',
    icon: FolderOpen,
    normalLayout: { colSpan: 2, order: 0 },
    fullscreenLayout: { x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
  },
  {
    id: 'scan',
    title: '扫描',
    icon: FolderOpen,
    normalLayout: { colSpan: 1, order: 1 },
    fullscreenLayout: { x: 2, y: 0, w: 1, h: 1, minW: 1, minH: 1 },
    // 全屏模式下合并到 path 区块，普通模式单独显示
  },
  {
    id: 'operation',
    title: '操作',
    icon: Play,
    normalLayout: { colSpan: 1, order: 2 },
    fullscreenLayout: { x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
  },
  {
    id: 'stats',
    title: '统计',
    icon: FilePenLine,
    normalLayout: { colSpan: 1, order: 3 },
    fullscreenLayout: { x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
  },
  {
    id: 'importExport',
    title: '导入/导出',
    icon: Upload,
    normalLayout: { colSpan: 1, order: 4 },
    fullscreenLayout: { x: 0, y: 2, w: 2, h: 1, minW: 2, minH: 1 },
  },
  {
    id: 'tree',
    title: '文件树',
    icon: Folder,
    normalLayout: { colSpan: 2, order: 5, hidden: true }, // 普通模式下隐藏，通过按钮切换
    fullscreenLayout: { x: 0, y: 3, w: 3, h: 4, minW: 2, minH: 2 },
    collapsible: true,
  },
  {
    id: 'log',
    title: '日志',
    icon: FileText,
    normalLayout: { colSpan: 2, order: 6, hidden: true }, // 普通模式下隐藏
    fullscreenLayout: { x: 3, y: 2, w: 1, h: 5, minW: 1, minH: 2 },
    collapsible: true,
  },
];

/** 获取默认 GridStack 布局 */
export function getTrenameDefaultLayout() {
  return TRENAME_BLOCKS.map(block => ({
    id: block.id,
    x: block.fullscreenLayout.x,
    y: block.fullscreenLayout.y,
    w: block.fullscreenLayout.w,
    h: block.fullscreenLayout.h,
    minW: block.fullscreenLayout.minW,
    minH: block.fullscreenLayout.minH,
  }));
}
