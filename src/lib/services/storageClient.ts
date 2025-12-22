/**
 * 后端存储客户端
 * 替代 localStorage，使用 SQLModel + SQLite 后端存储
 * 
 * 特性：
 * - 内存缓存减少 API 调用
 * - 自动从 localStorage 迁移数据
 * - 网络错误时队列写入并重试
 */

import { getApiV1Url } from '$lib/stores/backend';
import type { NodeConfig, ModeLayoutState, TabGroup } from '$lib/stores/nodeLayoutStore';

// ============ 类型定义 ============

/** 布局预设（后端格式） */
export interface LayoutPresetBackend {
  id: string;
  name: string;
  nodeType: string;
  layout: GridItem[];
  tabGroups?: TabGroup[];
  createdAt: number;
  isBuiltin: boolean;
}

/** GridItem 类型 */
interface GridItem {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

/** 默认预设配置 */
export interface DefaultPresetConfig {
  nodeType: string;
  fullscreenPresetId: string | null;
  normalPresetId: string | null;
}

// ============ 缓存配置 ============

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const CACHE_TTL = 5 * 60 * 1000; // 5 分钟
const layoutCache = new Map<string, CacheEntry<NodeConfig>>();
const presetCache = new Map<string, CacheEntry<LayoutPresetBackend[]>>();
const defaultsCache = new Map<string, CacheEntry<DefaultPresetConfig>>();

// 写入队列（离线时使用）
interface QueuedWrite {
  type: 'layout' | 'preset' | 'defaults';
  action: 'set' | 'delete';
  key: string;
  data?: unknown;
}
const writeQueue: QueuedWrite[] = [];
let isProcessingQueue = false;

// ============ 工具函数 ============

const getApiBase = () => getApiV1Url();

/** 导出 API 基础 URL（供 sendBeacon 使用） */
export { getApiBase };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    },
    ...options
  });
  
  if (!res.ok) {
    throw new Error(`Storage API Error: ${res.status} ${res.statusText}`);
  }
  
  return res.json();
}

function isCacheValid<T>(entry: CacheEntry<T> | undefined): entry is CacheEntry<T> {
  return entry !== undefined && Date.now() - entry.timestamp < CACHE_TTL;
}

// ============ Layouts API ============

/**
 * 获取节点布局配置
 */
export async function getLayout(nodeType: string): Promise<NodeConfig | null> {
  // 检查缓存
  const cached = layoutCache.get(nodeType);
  if (isCacheValid(cached)) {
    return cached.data;
  }
  
  try {
    const data = await request<NodeConfig | null>(`/storage/layouts/${nodeType}`);
    
    if (data) {
      layoutCache.set(nodeType, { data, timestamp: Date.now() });
    }
    
    return data;
  } catch (error) {
    console.error('[storageClient] getLayout failed:', error);
    return null;
  }
}

/**
 * 保存节点布局配置
 */
export async function setLayout(nodeType: string, config: NodeConfig): Promise<boolean> {
  try {
    await request('/storage/layouts/' + nodeType, {
      method: 'PUT',
      body: JSON.stringify({ config })
    });
    
    // 更新缓存
    layoutCache.set(nodeType, { data: config, timestamp: Date.now() });
    
    return true;
  } catch (error) {
    console.error('[storageClient] setLayout failed:', error);
    
    // 加入写入队列
    writeQueue.push({
      type: 'layout',
      action: 'set',
      key: nodeType,
      data: config
    });
    
    return false;
  }
}

/**
 * 删除节点布局配置
 */
export async function deleteLayout(nodeType: string): Promise<boolean> {
  try {
    await request(`/storage/layouts/${nodeType}`, { method: 'DELETE' });
    
    // 清除缓存
    layoutCache.delete(nodeType);
    
    return true;
  } catch (error) {
    console.error('[storageClient] deleteLayout failed:', error);
    return false;
  }
}

/**
 * 列出所有布局
 */
export async function listLayouts(): Promise<string[]> {
  try {
    return await request<string[]>('/storage/layouts');
  } catch (error) {
    console.error('[storageClient] listLayouts failed:', error);
    return [];
  }
}

// ============ Presets API ============

/**
 * 获取预设列表
 */
export async function getPresets(nodeType?: string): Promise<LayoutPresetBackend[]> {
  const cacheKey = nodeType || '__all__';
  
  // 检查缓存
  const cached = presetCache.get(cacheKey);
  if (isCacheValid(cached)) {
    return cached.data;
  }
  
  try {
    const url = nodeType 
      ? `/storage/presets?node_type=${encodeURIComponent(nodeType)}`
      : '/storage/presets';
    
    const data = await request<LayoutPresetBackend[]>(url);
    
    presetCache.set(cacheKey, { data, timestamp: Date.now() });
    
    return data;
  } catch (error) {
    console.error('[storageClient] getPresets failed:', error);
    return [];
  }
}

/**
 * 创建预设
 */
export async function createPreset(preset: {
  id: string;
  name: string;
  nodeType: string;
  layout: GridItem[];
  tabGroups?: TabGroup[];
  isBuiltin?: boolean;
}): Promise<LayoutPresetBackend | null> {
  try {
    const data = await request<LayoutPresetBackend>('/storage/presets', {
      method: 'POST',
      body: JSON.stringify({
        id: preset.id,
        name: preset.name,
        node_type: preset.nodeType,
        layout: preset.layout,
        tab_groups: preset.tabGroups,
        is_builtin: preset.isBuiltin || false
      })
    });
    
    // 清除预设缓存
    presetCache.clear();
    
    return data;
  } catch (error) {
    console.error('[storageClient] createPreset failed:', error);
    return null;
  }
}

/**
 * 更新预设
 */
export async function updatePreset(
  presetId: string, 
  updates: { name?: string; layout?: GridItem[]; tabGroups?: TabGroup[] }
): Promise<LayoutPresetBackend | null> {
  try {
    const data = await request<LayoutPresetBackend>(`/storage/presets/${presetId}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: updates.name,
        layout: updates.layout,
        tab_groups: updates.tabGroups
      })
    });
    
    // 清除预设缓存
    presetCache.clear();
    
    return data;
  } catch (error) {
    console.error('[storageClient] updatePreset failed:', error);
    return null;
  }
}

/**
 * 删除预设
 */
export async function deletePreset(presetId: string): Promise<boolean> {
  try {
    await request(`/storage/presets/${presetId}`, { method: 'DELETE' });
    
    // 清除预设缓存
    presetCache.clear();
    
    return true;
  } catch (error) {
    console.error('[storageClient] deletePreset failed:', error);
    return false;
  }
}

// ============ Defaults API ============

/**
 * 获取默认预设配置
 */
export async function getDefaults(nodeType: string): Promise<DefaultPresetConfig | null> {
  // 检查缓存
  const cached = defaultsCache.get(nodeType);
  if (isCacheValid(cached)) {
    return cached.data;
  }
  
  try {
    const data = await request<DefaultPresetConfig | null>(`/storage/defaults/${nodeType}`);
    
    if (data) {
      defaultsCache.set(nodeType, { data, timestamp: Date.now() });
    }
    
    return data;
  } catch (error) {
    console.error('[storageClient] getDefaults failed:', error);
    return null;
  }
}

/**
 * 设置默认预设配置
 */
export async function setDefaults(
  nodeType: string, 
  config: { fullscreenPresetId?: string | null; normalPresetId?: string | null }
): Promise<boolean> {
  try {
    await request(`/storage/defaults/${nodeType}`, {
      method: 'PUT',
      body: JSON.stringify({
        fullscreen_preset_id: config.fullscreenPresetId,
        normal_preset_id: config.normalPresetId
      })
    });
    
    // 更新缓存
    const newConfig: DefaultPresetConfig = {
      nodeType,
      fullscreenPresetId: config.fullscreenPresetId ?? null,
      normalPresetId: config.normalPresetId ?? null
    };
    defaultsCache.set(nodeType, { data: newConfig, timestamp: Date.now() });
    
    return true;
  } catch (error) {
    console.error('[storageClient] setDefaults failed:', error);
    return false;
  }
}

// ============ 迁移 API ============

/**
 * 从 localStorage 迁移数据到后端
 */
export async function migrateFromLocalStorage(): Promise<{ layouts: number; presets: number }> {
  if (typeof window === 'undefined') {
    return { layouts: 0, presets: 0 };
  }
  
  let layoutCount = 0;
  let presetCount = 0;
  
  // 迁移布局数据
  const layoutsKey = 'aestival-node-layouts';
  const layoutsData = localStorage.getItem(layoutsKey);
  
  if (layoutsData) {
    try {
      const layouts = JSON.parse(layoutsData);
      
      // 检查后端是否已有数据
      const existingLayouts = await listLayouts();
      
      if (existingLayouts.length === 0) {
        // 批量迁移
        await request('/storage/bulk/layouts', {
          method: 'POST',
          body: JSON.stringify({ layouts })
        });
        
        layoutCount = Object.keys(layouts).length;
        console.log(`[storageClient] 已迁移 ${layoutCount} 个布局配置`);
        
        // 清除 localStorage
        localStorage.removeItem(layoutsKey);
      }
    } catch (error) {
      console.error('[storageClient] 迁移布局数据失败:', error);
    }
  }
  
  // 迁移预设数据
  const presetsKey = 'aestival-layout-presets';
  const presetsData = localStorage.getItem(presetsKey);
  
  if (presetsData) {
    try {
      const presets = JSON.parse(presetsData);
      
      // 检查后端是否已有数据
      const existingPresets = await getPresets();
      
      if (existingPresets.length === 0 && Array.isArray(presets) && presets.length > 0) {
        // 转换格式并批量迁移
        const formattedPresets = presets.map((p: any) => ({
          id: p.id,
          name: p.name,
          node_type: p.nodeType,
          layout: p.layout,
          tab_groups: p.tabGroups,
          is_builtin: p.isBuiltin || false
        }));
        
        await request('/storage/bulk/presets', {
          method: 'POST',
          body: JSON.stringify({ presets: formattedPresets })
        });
        
        presetCount = presets.length;
        console.log(`[storageClient] 已迁移 ${presetCount} 个布局预设`);
        
        // 清除 localStorage
        localStorage.removeItem(presetsKey);
      }
    } catch (error) {
      console.error('[storageClient] 迁移预设数据失败:', error);
    }
  }
  
  // 迁移默认预设配置
  const defaultsKey = 'aestival-default-preset';
  const defaultsData = localStorage.getItem(defaultsKey);
  
  if (defaultsData) {
    try {
      const defaults = JSON.parse(defaultsData);
      
      for (const [nodeType, config] of Object.entries(defaults)) {
        const typedConfig = config as { fullscreen?: string; normal?: string };
        await setDefaults(nodeType, {
          fullscreenPresetId: typedConfig.fullscreen,
          normalPresetId: typedConfig.normal
        });
      }
      
      console.log('[storageClient] 已迁移默认预设配置');
      localStorage.removeItem(defaultsKey);
    } catch (error) {
      console.error('[storageClient] 迁移默认预设配置失败:', error);
    }
  }
  
  return { layouts: layoutCount, presets: presetCount };
}

// ============ 队列处理 ============

/**
 * 处理写入队列（网络恢复后调用）
 */
export async function processWriteQueue(): Promise<void> {
  if (isProcessingQueue || writeQueue.length === 0) {
    return;
  }
  
  isProcessingQueue = true;
  
  while (writeQueue.length > 0) {
    const item = writeQueue[0];
    
    try {
      if (item.type === 'layout') {
        if (item.action === 'set' && item.data) {
          await setLayout(item.key, item.data as NodeConfig);
        } else if (item.action === 'delete') {
          await deleteLayout(item.key);
        }
      }
      
      // 成功后移除
      writeQueue.shift();
    } catch (error) {
      console.error('[storageClient] 队列处理失败:', error);
      break; // 停止处理，等待下次重试
    }
  }
  
  isProcessingQueue = false;
}

// ============ 缓存管理 ============

/**
 * 清除所有缓存
 */
export function clearCache(): void {
  layoutCache.clear();
  presetCache.clear();
  defaultsCache.clear();
}

/**
 * 清除指定类型的缓存
 */
export function invalidateCache(type: 'layout' | 'preset' | 'defaults', key?: string): void {
  if (type === 'layout') {
    if (key) {
      layoutCache.delete(key);
    } else {
      layoutCache.clear();
    }
  } else if (type === 'preset') {
    presetCache.clear();
  } else if (type === 'defaults') {
    if (key) {
      defaultsCache.delete(key);
    } else {
      defaultsCache.clear();
    }
  }
}

// ============ 备份/恢复 API ============

/** 存储数据导出格式 */
export interface StorageExportData {
  layouts: Record<string, NodeConfig>;
  presets: LayoutPresetBackend[];
  defaults: Record<string, { fullscreenPresetId: string | null; normalPresetId: string | null }>;
}

/**
 * 导出所有存储数据（用于备份）
 */
export async function exportAllStorage(): Promise<StorageExportData | null> {
  try {
    const data = await request<StorageExportData>('/storage/export');
    return data;
  } catch (error) {
    console.error('[storageClient] exportAllStorage failed:', error);
    return null;
  }
}

/**
 * 导入存储数据（用于恢复备份）
 * @param data 要导入的数据
 * @param merge true: 合并模式（保留现有数据），false: 覆盖模式（清空后导入）
 */
export async function importAllStorage(
  data: StorageExportData, 
  merge: boolean = true
): Promise<{ success: boolean; layouts: number; presets: number; defaults: number } | null> {
  try {
    const result = await request<{ success: boolean; layouts: number; presets: number; defaults: number }>(
      '/storage/import',
      {
        method: 'POST',
        body: JSON.stringify({ data, merge })
      }
    );
    
    // 清除所有缓存，确保下次读取时获取最新数据
    clearCache();
    
    return result;
  } catch (error) {
    console.error('[storageClient] importAllStorage failed:', error);
    return null;
  }
}
