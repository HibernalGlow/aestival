/**
 * RepackuNode 文件树预览相关类型定义
 */

/** 压缩模式类型 */
export type CompressMode = 'entire' | 'selective' | 'skip' | null;

/** 文件夹节点类型（对应后端 FolderInfo.to_tree_dict()） */
export interface FolderNode {
  path: string;
  name: string;
  depth: number;
  weight: number;
  total_files: number;
  total_size: number;
  size_mb: number;
  compress_mode: CompressMode;
  recommendation: string;
  file_types: Record<string, number>;
  file_extensions: Record<string, number>;
  dominant_types: string[];
  children?: FolderNode[];
}

/** 压缩统计信息类型 */
export interface CompressionStats {
  total: number;
  entire: number;
  selective: number;
  skip: number;
}

/** 卡片大小类型 */
export type CardSize = 'small' | 'medium' | 'large' | 'wide';

/** 文件夹卡片类型（用于 Bento Grid 布局） */
export interface FolderCard {
  node: FolderNode;
  depth: number;
  parentPath: string;
  hasChildren: boolean;
  expanded: boolean;
  colSpan: number;
  rowSpan: number;
}

/** Bento Grid 布局配置 */
export interface BentoGridConfig {
  columns: number;
  gap: number;
  minCardWidth: number;
  borderRadius: number;
}
