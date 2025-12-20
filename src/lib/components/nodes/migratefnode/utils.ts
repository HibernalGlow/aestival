/**
 * MigrateFNode 辅助函数模块
 * 文件迁移节点工具函数
 */

export interface MigrateStats {
  total: number;
  moved: number;
  skipped: number;
  failed: number;
}

export interface MigrateItem {
  source: string;
  target: string;
  status: 'pending' | 'moved' | 'skipped' | 'failed';
  reason?: string;
}

/**
 * 获取状态颜色类
 */
export function getStatusColorClass(status: MigrateItem['status']): string {
  switch (status) {
    case 'moved': return 'bg-green-500';
    case 'skipped': return 'bg-yellow-500';
    case 'failed': return 'bg-red-500';
    case 'pending': default: return 'bg-gray-400';
  }
}

/**
 * 获取状态文本颜色类
 */
export function getStatusTextColorClass(status: MigrateItem['status']): string {
  switch (status) {
    case 'moved': return 'text-green-600';
    case 'skipped': return 'text-yellow-600';
    case 'failed': return 'text-red-600';
    case 'pending': default: return 'text-gray-500';
  }
}

/**
 * 获取状态名称
 */
export function getStatusName(status: MigrateItem['status']): string {
  switch (status) {
    case 'moved': return '已迁移';
    case 'skipped': return '已跳过';
    case 'failed': return '失败';
    case 'pending': default: return '待处理';
  }
}

/**
 * 统计迁移结果
 */
export function countMigrateStats(items: MigrateItem[]): MigrateStats {
  const stats: MigrateStats = { total: 0, moved: 0, skipped: 0, failed: 0 };
  
  for (const item of items) {
    stats.total++;
    switch (item.status) {
      case 'moved': stats.moved++; break;
      case 'skipped': stats.skipped++; break;
      case 'failed': stats.failed++; break;
    }
  }
  
  return stats;
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
