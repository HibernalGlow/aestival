/**
 * Findz 节点共享类型定义
 */

/** 文件数据接口 */
export interface FileData {
  name: string;
  path: string;
  size: number;
  size_formatted: string;
  date: string;
  time: string;
  type: string;
  ext: string;
  archive: string;
  container: string;
}

/** 搜索结果统计 */
export interface SearchResult {
  total_count: number;
  file_count: number;
  dir_count: number;
  archive_count: number;
  nested_count: number;
}

/** 节点状态（用于持久化） */
export interface FindzNodeState {
  phase: 'idle' | 'searching' | 'completed' | 'error';
  progress: number;
  searchResult: SearchResult | null;
  files: FileData[];
  byExtension: Record<string, number>;
  targetPath: string;
  whereClause: string;
}

/** 分组分析数据 */
export interface GroupAnalysis {
  key: string;
  name: string;
  fileCount: number;
  totalSize: number;
  avgSize: number;
  avgSizeFormatted: string;
  totalSizeFormatted: string;
  subStats: Record<string, number>;
}

/** 过滤条件 */
export interface AnalysisFilter {
  countMin: number | null;
  countMax: number | null;
  avgSizeMin: number | null;
  avgSizeMax: number | null;
  totalSizeMin: number | null;
  totalSizeMax: number | null;
}
