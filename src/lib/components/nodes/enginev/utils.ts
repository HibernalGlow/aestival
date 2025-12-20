/**
 * EngineVNode 辅助函数模块
 * Wallpaper Engine 工坊管理工具
 */
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import type { TabBlockState } from '$lib/components/blocks/blockRegistry';

// ============ 类型定义 ============

/** 壁纸数据 */
export interface WallpaperItem {
  path: string;
  folder_name: string;
  workshop_id: string;
  title: string;
  description: string;
  content_rating: string;
  rating_sex: string;
  rating_violence: string;
  tags: string[];
  file_name: string;
  preview: string;
  wallpaper_type: string;
  created_time: string;
  modified_time: string;
  size: number;
}

/**
 * 获取壁纸预览图的 URL
 * 通过 Python 后端 API 提供文件访问
 */
export function getPreviewUrl(wallpaper: WallpaperItem, apiBase: string): string | null {
  if (!wallpaper.preview || !wallpaper.path) return null;
  const fullPath = `${wallpaper.path}/${wallpaper.preview}`.replace(/\\/g, '/');
  return `${apiBase}/file?path=${encodeURIComponent(fullPath)}`;
}

/** 过滤条件 */
export interface FilterOptions {
  title: string;
  contentrating: string;
  type: string;
  ratingsex: string;
  ratingviolence: string;
  tags: string[];
}

/** 统计信息 */
export interface EngineVStats {
  total: number;
  filtered: number;
  byType: Record<string, number>;
  byRating: Record<string, number>;
}

/** 重命名配置 */
export interface RenameConfig {
  template: string;
  descMaxLength: number;
  nameMaxLength: number;
  dryRun: boolean;
  copyMode: boolean;
  targetPath: string;
}

/** 操作阶段 */
export type Phase = 'idle' | 'scanning' | 'filtering' | 'renaming' | 'ready' | 'completed' | 'error';

/** 节点状态 */
export interface EngineVState {
  phase: Phase;
  logs: string[];
  workshopPath: string;
  wallpapers: WallpaperItem[];
  filteredWallpapers: WallpaperItem[];
  stats: EngineVStats;
  filters: FilterOptions;
  renameConfig: RenameConfig;
  gridLayout?: GridItem[];
  selectedIds: Set<string>;
  viewMode: 'grid' | 'list';
  tabStates?: Record<string, TabBlockState>;
  dynamicTabBlocks?: string[];
  tabBlockCounter?: number;
}

// ============ 默认值 ============

export const DEFAULT_STATS: EngineVStats = {
  total: 0, filtered: 0, byType: {}, byRating: {}
};

export const DEFAULT_FILTERS: FilterOptions = {
  title: '', contentrating: '', type: '', ratingsex: '', ratingviolence: '', tags: []
};

export const DEFAULT_RENAME_CONFIG: RenameConfig = {
  template: '[#{id}]{original_name}+{title}',
  descMaxLength: 18, nameMaxLength: 120, dryRun: true, copyMode: false, targetPath: ''
};

export const DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'filter', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 1, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'rename', x: 2, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'gallery', x: 0, y: 4, w: 3, h: 4, minW: 2, minH: 2 },
  { id: 'log', x: 3, y: 4, w: 1, h: 4, minW: 1, minH: 1 }
];

// ============ 工具函数 ============

export function getPhaseBorderClass(phase: Phase): string {
  switch (phase) {
    case 'scanning': case 'filtering': case 'renaming': return 'border-blue-500/50';
    case 'ready': return 'border-green-500/50';
    case 'completed': return 'border-green-600/50';
    case 'error': return 'border-red-500/50';
    default: return 'border-border';
  }
}

export function getRatingInfo(rating: string): { name: string; color: string } {
  const ratingMap: Record<string, { name: string; color: string }> = {
    'Everyone': { name: '全年龄', color: 'text-green-500' },
    'Mature': { name: '成熟', color: 'text-yellow-500' },
    'Adult': { name: '成人', color: 'text-red-500' },
    'Questionable': { name: '存疑', color: 'text-orange-500' }
  };
  return ratingMap[rating] || { name: rating || '未知', color: 'text-muted-foreground' };
}

export function getTypeInfo(type: string): { name: string; icon: string } {
  const typeMap: Record<string, { name: string; icon: string }> = {
    'Video': { name: '视频', icon: 'Video' },
    'Scene': { name: '场景', icon: 'Layers' },
    'Web': { name: '网页', icon: 'Globe' },
    'Application': { name: '应用', icon: 'AppWindow' },
    'Preset': { name: '预设', icon: 'Settings' }
  };
  return typeMap[type] || { name: type || '未知', icon: 'File' };
}

export function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatDate(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  } catch { return isoString; }
}

export function generateNewName(wallpaper: WallpaperItem, template: string, descMaxLength: number = 18, nameMaxLength: number = 120): string {
  let descClean = (wallpaper.description || '').trim().replace(/[\n\r]/g, ' ');
  if (descMaxLength > 0 && descClean.length > descMaxLength) descClean = descClean.slice(0, descMaxLength) + '…';

  const replacements: Record<string, string> = {
    '{id}': wallpaper.workshop_id, '{title}': wallpaper.title, '{original_name}': wallpaper.folder_name,
    '{type}': wallpaper.wallpaper_type, '{rating}': wallpaper.content_rating, '{desc}': descClean
  };

  let newName = template;
  for (const [placeholder, value] of Object.entries(replacements)) {
    newName = newName.replace(new RegExp(placeholder.replace(/[{}]/g, '\\$&'), 'g'), value || '');
  }

  const invalidChars = '<>:"/\\|?*';
  for (const char of invalidChars) newName = newName.replace(new RegExp(`\\${char}`, 'g'), '_');
  newName = newName.split(/\s+/).join(' ').trim();
  if (nameMaxLength > 0 && newName.length > nameMaxLength) newName = newName.slice(0, nameMaxLength - 1) + '…';
  return newName;
}

export function calculateStats(wallpapers: WallpaperItem[], filtered: WallpaperItem[]): EngineVStats {
  const stats: EngineVStats = { total: wallpapers.length, filtered: filtered.length, byType: {}, byRating: {} };
  for (const w of wallpapers) {
    if (w.wallpaper_type) stats.byType[w.wallpaper_type] = (stats.byType[w.wallpaper_type] || 0) + 1;
    if (w.content_rating) stats.byRating[w.content_rating] = (stats.byRating[w.content_rating] || 0) + 1;
  }
  return stats;
}

export function filterWallpapers(wallpapers: WallpaperItem[], filters: FilterOptions): WallpaperItem[] {
  return wallpapers.filter(w => {
    if (filters.title && !w.title.toLowerCase().includes(filters.title.toLowerCase())) return false;
    if (filters.contentrating && w.content_rating !== filters.contentrating) return false;
    if (filters.type && w.wallpaper_type !== filters.type) return false;
    if (filters.ratingsex && w.rating_sex !== filters.ratingsex) return false;
    if (filters.ratingviolence && w.rating_violence !== filters.ratingviolence) return false;
    if (filters.tags.length > 0 && !filters.tags.some(tag => w.tags.includes(tag))) return false;
    return true;
  });
}

export function getAllTags(wallpapers: WallpaperItem[]): string[] {
  const tagSet = new Set<string>();
  for (const w of wallpapers) for (const tag of w.tags) tagSet.add(tag);
  return Array.from(tagSet).sort();
}

export function generateExportFilename(format: 'json' | 'paths'): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `enginev_export_${timestamp}.${format === 'json' ? 'json' : 'txt'}`;
}
