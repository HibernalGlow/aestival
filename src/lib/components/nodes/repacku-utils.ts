/**
 * RepackuNode 辅助函数模块
 */
import type { FolderNode, CompressionStats, FolderCard, CompressMode, CardSize } from '$lib/types/repacku';

/**
 * 获取压缩模式对应的颜色类
 * @param mode 压缩模式
 * @returns Tailwind CSS 颜色类
 */
export function getModeColorClass(mode: CompressMode): string {
  switch (mode) {
    case 'entire':
      return 'bg-green-500';
    case 'selective':
      return 'bg-yellow-500';
    case 'skip':
    default:
      return 'bg-gray-400';
  }
}

/**
 * 获取压缩模式对应的文本颜色类
 * @param mode 压缩模式
 * @returns Tailwind CSS 文本颜色类
 */
export function getModeTextColorClass(mode: CompressMode): string {
  switch (mode) {
    case 'entire':
      return 'text-green-600';
    case 'selective':
      return 'text-yellow-600';
    case 'skip':
    default:
      return 'text-gray-500';
  }
}

/**
 * 获取压缩模式的显示名称
 * @param mode 压缩模式
 * @returns 显示名称
 */
export function getModeName(mode: CompressMode): string {
  switch (mode) {
    case 'entire':
      return '整体压缩';
    case 'selective':
      return '选择性';
    case 'skip':
      return '跳过';
    default:
      return '未知';
  }
}

/**
 * 递归统计压缩模式数量
 * @param node 文件夹节点
 * @returns 统计信息
 */
export function countCompressionModes(node: FolderNode | null): CompressionStats {
  const stats: CompressionStats = { total: 0, entire: 0, selective: 0, skip: 0 };
  
  if (!node) return stats;
  
  function traverse(n: FolderNode) {
    stats.total++;
    switch (n.compress_mode) {
      case 'entire':
        stats.entire++;
        break;
      case 'selective':
        stats.selective++;
        break;
      case 'skip':
      default:
        stats.skip++;
        break;
    }
    if (n.children) {
      for (const child of n.children) {
        traverse(child);
      }
    }
  }
  
  traverse(node);
  return stats;
}

/**
 * 计算卡片大小类型（基于文件数量）
 * @param node 文件夹节点
 * @returns 卡片大小类型
 */
export function getCardSize(node: FolderNode): CardSize {
  const fileCount = node.total_files;
  if (fileCount >= 200) return 'large';
  if (fileCount >= 100) return 'wide';
  if (fileCount >= 50) return 'medium';
  return 'small';
}

/**
 * 计算卡片网格跨度
 * @param node 文件夹节点
 * @returns { colSpan, rowSpan }
 */
export function calculateCardSpan(node: FolderNode): { colSpan: number; rowSpan: number } {
  const size = getCardSize(node);
  switch (size) {
    case 'large':
      return { colSpan: 2, rowSpan: 2 };
    case 'wide':
      return { colSpan: 2, rowSpan: 1 };
    case 'medium':
      return { colSpan: 1, rowSpan: 2 };
    case 'small':
    default:
      return { colSpan: 1, rowSpan: 1 };
  }
}

/**
 * 扁平化树结构为卡片列表（用于 Bento Grid 布局）
 * @param node 根节点
 * @param maxDepth 最大深度（默认 1，只展示顶层）
 * @returns 卡片列表
 */
export function flattenTreeToCards(
  node: FolderNode | null,
  maxDepth: number = 1,
  parentPath: string = '',
  currentDepth: number = 0
): FolderCard[] {
  if (!node) return [];
  
  const cards: FolderCard[] = [];
  
  // 跳过 skip 模式的文件夹（在顶层）
  if (currentDepth === 0 && node.compress_mode === 'skip') {
    // 仍然处理子节点
    if (node.children && currentDepth < maxDepth) {
      for (const child of node.children) {
        cards.push(...flattenTreeToCards(child, maxDepth, node.path, currentDepth + 1));
      }
    }
    return cards;
  }
  
  const { colSpan, rowSpan } = calculateCardSpan(node);
  
  cards.push({
    node,
    depth: currentDepth,
    parentPath,
    hasChildren: !!(node.children && node.children.length > 0),
    expanded: false,
    colSpan,
    rowSpan
  });
  
  // 递归处理子节点（如果在深度范围内）
  if (node.children && currentDepth < maxDepth - 1) {
    for (const child of node.children) {
      cards.push(...flattenTreeToCards(child, maxDepth, node.path, currentDepth + 1));
    }
  }
  
  return cards;
}

/**
 * 获取文件类型图标名称
 * @param type 文件类型
 * @returns 图标名称
 */
export function getFileTypeIconName(type: string): string {
  const typeMap: Record<string, string> = {
    'image': 'Image',
    'document': 'FileText',
    'video': 'Video',
    'audio': 'Music',
    'archive': 'Archive',
    'code': 'Code',
    'other': 'File'
  };
  return typeMap[type.toLowerCase()] || 'File';
}
