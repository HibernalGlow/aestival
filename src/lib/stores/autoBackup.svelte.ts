/**
 * Aestivus - Auto Backup Store
 * 自动备份管理系统
 * 使用 Python 后端 API 替代 Tauri invoke
 */

import { getApiBaseUrl } from '$lib/stores/backend';
import * as storageClient from '$lib/services/storageClient';
import type { StorageExportData } from '$lib/services/storageClient';

// ==================== 类型定义 ====================

export interface BackupExclusionSettings {
	excludedKeys: string[]; // 手动排除的 localStorage 键名
	excludedModules: string[]; // 排除的模块名
	autoExcludeLargeData: boolean; // 自动排除大数据
	maxLineCount: number; // 超过此行数的数据将被排除（JSON 格式化后计算）
}

export interface BackupSettings {
	enabled: boolean;
	intervalMinutes: number; // 备份间隔（分钟）
	maxBackups: number; // 最大保留备份数量
	backupPath: string; // 备份目录路径
	lastBackupTime: number | null; // 上次备份时间戳
	includeAllLocalStorage: boolean; // 是否包含所有 localStorage 数据
	includeDatabaseStorage: boolean; // 是否包含数据库存储数据（布局、预设等）
	exclusion: BackupExclusionSettings; // 排除配置
}

export interface BackupInfo {
	filename: string;
	timestamp: number;
	size: number;
	path: string;
}

export interface FullBackupPayload {
	version: string;
	timestamp: number;
	backupType: 'auto' | 'manual';
	appSettings: Record<string, unknown>;
	rawLocalStorage: Record<string, string>; // 所有 localStorage 原始数据
	databaseStorage?: StorageExportData; // 数据库存储数据（布局、预设、默认配置）
}

// ==================== 常量 ====================

const SETTINGS_KEY = 'aestivus-auto-backup-settings';
const DEFAULT_EXCLUSION: BackupExclusionSettings = {
	excludedKeys: [],
	excludedModules: [],
	autoExcludeLargeData: true,
	maxLineCount: 1000
};

const DEFAULT_SETTINGS: BackupSettings = {
	enabled: false,
	intervalMinutes: 60, // 默认每小时备份一次
	maxBackups: 10,
	backupPath: '',
	lastBackupTime: null,
	includeAllLocalStorage: true,
	includeDatabaseStorage: true, // 默认包含数据库存储
	exclusion: DEFAULT_EXCLUSION
};

// ==================== API 辅助函数 ====================

/** 获取备份 API 基础 URL */
const getBackupApiUrl = () => `${getApiBaseUrl()}/v1/backup`;

/** 通用 API 请求 */
async function backupApiRequest<T>(
	endpoint: string,
	options: RequestInit = {}
): Promise<T> {
	const response = await fetch(`${getBackupApiUrl()}${endpoint}`, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...options.headers
		}
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`API 请求失败: ${response.status} - ${errorText}`);
	}

	return response.json();
}

// ==================== Store ====================

class AutoBackupStore {
	private settings = $state<BackupSettings>(this.loadSettings());
	private timer: number | null = null;
	private isBackingUp = $state(false);
	private lastError = $state<string | null>(null);
	private initialized = false;

	constructor() {
		// 初始化时启动定时器
		if (typeof window !== 'undefined') {
			this.initializeDefaultPath();
			this.startScheduler();
		}
	}

	/**
	 * 初始化默认备份路径（通过 Python API）
	 */
	private async initializeDefaultPath() {
		if (this.initialized) return;
		this.initialized = true;

		// 如果没有设置备份路径，使用默认路径
		if (!this.settings.backupPath) {
			try {
				const result = await backupApiRequest<{ success: boolean; path: string }>(
					'/default-path'
				);
				if (result.success && result.path) {
					this.settings = { ...this.settings, backupPath: result.path };
					this.saveSettings();
					console.log('[AutoBackup] 默认备份路径:', result.path);
				}
			} catch (e) {
				console.error('[AutoBackup] 初始化默认路径失败:', e);
			}
		}
	}

	// ==================== 设置管理 ====================

	private loadSettings(): BackupSettings {
		if (typeof window === 'undefined') return DEFAULT_SETTINGS;
		try {
			const stored = localStorage.getItem(SETTINGS_KEY);
			if (stored) {
				return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
			}
		} catch (e) {
			console.error('加载备份设置失败:', e);
		}
		return DEFAULT_SETTINGS;
	}

	private saveSettings() {
		if (typeof window === 'undefined') return;
		try {
			localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings));
		} catch (e) {
			console.error('保存备份设置失败:', e);
		}
	}

	get currentSettings() {
		return this.settings;
	}

	get backing() {
		return this.isBackingUp;
	}

	get error() {
		return this.lastError;
	}

	updateSettings(partial: Partial<BackupSettings>) {
		this.settings = { ...this.settings, ...partial };
		this.saveSettings();
		this.restartScheduler();
	}

	// ==================== 定时器管理 ====================

	private startScheduler() {
		this.stopScheduler();

		if (!this.settings.enabled || this.settings.intervalMinutes <= 0) {
			return;
		}

		const intervalMs = this.settings.intervalMinutes * 60 * 1000;

		// 检查是否需要立即备份
		const now = Date.now();
		const lastBackup = this.settings.lastBackupTime || 0;
		const timeSinceLastBackup = now - lastBackup;

		if (timeSinceLastBackup >= intervalMs) {
			// 需要立即备份
			this.performBackup('auto');
		}

		// 设置定时器
		this.timer = window.setInterval(() => {
			this.performBackup('auto');
		}, intervalMs);

		console.log(`[AutoBackup] 定时备份已启动，间隔: ${this.settings.intervalMinutes} 分钟`);
	}

	private stopScheduler() {
		if (this.timer !== null) {
			window.clearInterval(this.timer);
			this.timer = null;
		}
	}

	private restartScheduler() {
		this.startScheduler();
	}

	// ==================== 备份功能 ====================

	/**
	 * 计算字符串的行数（如果是 JSON 则先格式化）
	 */
	private countLines(str: string): number {
		if (!str) return 0;
		
		// 尝试解析为 JSON 并格式化，这样才能正确计算行数
		try {
			const parsed = JSON.parse(str);
			const formatted = JSON.stringify(parsed, null, 2);
			return formatted.split('\n').length;
		} catch {
			// 不是 JSON，直接计算原始行数
			return str.split('\n').length;
		}
	}

	/**
	 * 检查键名是否应被排除
	 */
	private shouldExcludeKey(key: string, value: string): boolean {
		const exclusion = this.settings.exclusion || DEFAULT_EXCLUSION;

		// 检查是否在手动排除列表中
		if (exclusion.excludedKeys.includes(key)) {
			return true;
		}

		// 检查是否超过行数限制
		if (exclusion.autoExcludeLargeData && exclusion.maxLineCount > 0) {
			const lineCount = this.countLines(value);
			if (lineCount > exclusion.maxLineCount) {
				console.log(`[AutoBackup] 自动排除大数据: ${key} (行数: ${lineCount})`);
				return true;
			}
		}

		return false;
	}

	/**
	 * 检查子键是否应被排除
	 */
	private shouldExcludeSubKey(parentKey: string, subKey: string, subValue: unknown): boolean {
		const exclusion = this.settings.exclusion || DEFAULT_EXCLUSION;
		const fullKey = `${parentKey}.${subKey}`;

		// 检查是否在手动排除列表中
		if (exclusion.excludedKeys.includes(fullKey)) {
			return true;
		}

		// 检查是否超过行数限制
		if (exclusion.autoExcludeLargeData && exclusion.maxLineCount > 0) {
			const subValueStr = JSON.stringify(subValue, null, 2);
			const lineCount = subValueStr.split('\n').length;
			if (lineCount > exclusion.maxLineCount) {
				console.log(`[AutoBackup] 自动排除大数据子键: ${fullKey} (行数: ${lineCount})`);
				return true;
			}
		}

		return false;
	}

	/**
	 * 收集所有 localStorage 数据（应用排除规则，支持子键排除）
	 */
	private collectAllLocalStorage(): Record<string, string> {
		const data: Record<string, string> = {};
		if (typeof window === 'undefined' || !window.localStorage) return data;

		// 需要支持子键排除的 localStorage 键名
		const expandableKeys = ['aestival-node-states', 'custom-themes'];

		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i);
			if (key) {
				const value = localStorage.getItem(key);
				if (value === null) continue;

				// 如果整个键被排除，跳过
				if (this.shouldExcludeKey(key, value)) {
					continue;
				}

				// 如果是可展开的键，检查子键排除
				if (expandableKeys.includes(key)) {
					try {
						const parsed = JSON.parse(value);
						if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
							const filtered: Record<string, unknown> = {};
							let hasExcluded = false;

							for (const [subKey, subValue] of Object.entries(parsed)) {
								if (!this.shouldExcludeSubKey(key, subKey, subValue)) {
									filtered[subKey] = subValue;
								} else {
									hasExcluded = true;
								}
							}

							// 如果有子键被排除，存储过滤后的数据
							if (hasExcluded) {
								data[key] = JSON.stringify(filtered);
							} else {
								data[key] = value;
							}
							continue;
						}
					} catch {
						// 解析失败，按原样处理
					}
				}

				data[key] = value;
			}
		}
		return data;
	}

	/**
	 * 分析 localStorage 数据（用于显示给用户）
	 * 支持展开 JSON 对象的子键，子键嵌套在主键内部
	 */
	analyzeLocalStorage(): Array<{
		key: string;
		lines: number;
		size: number;
		excluded: boolean;
		reason?: string;
		children?: Array<{
			subKey: string;
			fullKey: string; // 完整键名，如 aestival-node-states.node-123
			lines: number;
			size: number;
			excluded: boolean;
			reason?: string;
		}>;
	}> {
		const result: Array<{
			key: string;
			lines: number;
			size: number;
			excluded: boolean;
			reason?: string;
			children?: Array<{
				subKey: string;
				fullKey: string;
				lines: number;
				size: number;
				excluded: boolean;
				reason?: string;
			}>;
		}> = [];
		if (typeof window === 'undefined' || !window.localStorage) return result;

		const exclusion = this.settings.exclusion || DEFAULT_EXCLUSION;
		// 需要展开子键的 localStorage 键名
		const expandableKeys = ['aestival-node-states', 'custom-themes'];

		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i);
			if (key) {
				const value = localStorage.getItem(key) || '';
				const lines = this.countLines(value);
				const size = new Blob([value]).size;

				let excluded = false;
				let reason: string | undefined;

				if (exclusion.excludedKeys.includes(key)) {
					excluded = true;
					reason = '手动排除';
				} else if (exclusion.autoExcludeLargeData && lines > exclusion.maxLineCount) {
					excluded = true;
					reason = `超过${exclusion.maxLineCount}行`;
				}

				const item: (typeof result)[0] = { key, lines, size, excluded, reason };

				// 如果是可展开的键，尝试解析并添加子键
				if (expandableKeys.includes(key)) {
					try {
						const parsed = JSON.parse(value);
						if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
							const children: NonNullable<(typeof result)[0]['children']> = [];

							for (const [subKey, subValue] of Object.entries(parsed)) {
								const subValueStr = JSON.stringify(subValue, null, 2);
								const subLines = subValueStr.split('\n').length;
								const subSize = new Blob([subValueStr]).size;
								const fullKey = `${key}.${subKey}`;

								// 检查子键是否被排除
								let subExcluded = false;
								let subReason: string | undefined;

								if (exclusion.excludedKeys.includes(fullKey)) {
									subExcluded = true;
									subReason = '手动排除';
								} else if (exclusion.autoExcludeLargeData && subLines > exclusion.maxLineCount) {
									subExcluded = true;
									subReason = `超过${exclusion.maxLineCount}行`;
								}

								children.push({
									subKey,
									fullKey,
									lines: subLines,
									size: subSize,
									excluded: subExcluded,
									reason: subReason
								});
							}

							// 按大小排序子键
							children.sort((a, b) => b.size - a.size);
							item.children = children;
						}
					} catch {
						// 解析失败，忽略
					}
				}

				result.push(item);
			}
		}

		// 按大小排序
		return result.sort((a, b) => b.size - a.size);
	}

	/**
	 * 构建完整备份数据（包含数据库存储）
	 */
	async buildFullBackupPayload(backupType: 'auto' | 'manual'): Promise<FullBackupPayload> {
		const payload: FullBackupPayload = {
			version: '1.1.0', // 版本升级，支持数据库存储
			timestamp: Date.now(),
			backupType,
			appSettings: {},
			rawLocalStorage: this.settings.includeAllLocalStorage ? this.collectAllLocalStorage() : {}
		};

		// 根据设置决定是否获取数据库存储数据
		if (this.settings.includeDatabaseStorage) {
			try {
				const dbData = await storageClient.exportAllStorage();
				if (dbData) {
					payload.databaseStorage = dbData;
					console.log('[AutoBackup] 已包含数据库存储数据:', {
						layouts: Object.keys(dbData.layouts).length,
						presets: dbData.presets.length,
						defaults: Object.keys(dbData.defaults).length
					});
				}
			} catch (e) {
				console.error('[AutoBackup] 获取数据库存储数据失败:', e);
			}
		}

		return payload;
	}

	/**
	 * 执行备份（通过 Python API）
	 */
	async performBackup(type: 'auto' | 'manual' = 'manual'): Promise<boolean> {
		if (this.isBackingUp) {
			console.log('[AutoBackup] 备份正在进行中，跳过');
			return false;
		}

		if (!this.settings.backupPath) {
			this.lastError = '未设置备份路径';
			console.error('[AutoBackup]', this.lastError);
			return false;
		}

		this.isBackingUp = true;
		this.lastError = null;

		try {
			const payload = await this.buildFullBackupPayload(type);
			const json = JSON.stringify(payload, null, 2);

			// 生成文件名
			const date = new Date();
			const dateStr = date.toISOString().replace(/[:.]/g, '-').slice(0, 19);
			const filename = `aestivus-backup-${type}-${dateStr}.json`;
			const filepath = `${this.settings.backupPath}/${filename}`;

			// 通过 Python API 写入文件
			await backupApiRequest('/write-file', {
				method: 'POST',
				body: JSON.stringify({ path: filepath, content: json })
			});

			// 更新最后备份时间
			this.settings.lastBackupTime = Date.now();
			this.saveSettings();

			// 清理旧备份
			await this.cleanupOldBackups();

			console.log(`[AutoBackup] 备份成功: ${filepath}`);
			return true;
		} catch (e) {
			this.lastError = e instanceof Error ? e.message : String(e);
			console.error('[AutoBackup] 备份失败:', e);
			return false;
		} finally {
			this.isBackingUp = false;
		}
	}

	/**
	 * 清理旧备份（通过 Python API）
	 */
	private async cleanupOldBackups() {
		if (this.settings.maxBackups <= 0) return;

		try {
			const backups = await this.listBackups();
			if (backups.length > this.settings.maxBackups) {
				// 按时间排序，删除最旧的
				const toDelete = backups
					.sort((a, b) => a.timestamp - b.timestamp)
					.slice(0, backups.length - this.settings.maxBackups);

				for (const backup of toDelete) {
					try {
						await backupApiRequest('/delete-file', {
							method: 'POST',
							body: JSON.stringify({ path: backup.path })
						});
						console.log(`[AutoBackup] 已删除旧备份: ${backup.filename}`);
					} catch (e) {
						console.error(`[AutoBackup] 删除旧备份失败: ${backup.filename}`, e);
					}
				}
			}
		} catch (e) {
			console.error('[AutoBackup] 清理旧备份失败:', e);
		}
	}

	/**
	 * 列出所有备份文件（通过 Python API）
	 */
	async listBackups(): Promise<BackupInfo[]> {
		if (!this.settings.backupPath) return [];

		try {
			const files = await backupApiRequest<
				Array<{
					name: string;
					path: string;
					size: number;
					modified: number;
				}>
			>('/list-files', {
				method: 'POST',
				body: JSON.stringify({
					path: this.settings.backupPath,
					pattern: 'aestivus-backup-*.json'
				})
			});

			return files.map((f) => ({
				filename: f.name,
				path: f.path,
				size: f.size,
				timestamp: f.modified
			}));
		} catch (e) {
			console.error('[AutoBackup] 列出备份失败:', e);
			return [];
		}
	}

	/**
	 * 从备份恢复（通过 Python API）
	 * @param backupPath 备份文件路径
	 * @param restoreDatabaseStorage 是否恢复数据库存储数据，默认 true
	 */
	async restoreFromBackup(backupPath: string, restoreDatabaseStorage: boolean = true): Promise<boolean> {
		try {
			const result = await backupApiRequest<{ success: boolean; content: string }>(
				'/read-file',
				{
					method: 'POST',
					body: JSON.stringify({ path: backupPath })
				}
			);
			const payload = JSON.parse(result.content) as FullBackupPayload;

			// 恢复 localStorage 数据
			if (payload.rawLocalStorage && typeof window !== 'undefined') {
				for (const [key, value] of Object.entries(payload.rawLocalStorage)) {
					try {
						localStorage.setItem(key, value);
					} catch (e) {
						console.error(`恢复 localStorage 键失败: ${key}`, e);
					}
				}
			}

			// 根据参数决定是否恢复数据库存储数据（布局、预设、默认配置）
			if (restoreDatabaseStorage && payload.databaseStorage) {
				try {
					const importResult = await storageClient.importAllStorage(payload.databaseStorage, true);
					if (importResult) {
						console.log('[AutoBackup] 数据库存储恢复成功:', {
							layouts: importResult.layouts,
							presets: importResult.presets,
							defaults: importResult.defaults
						});
					}
				} catch (e) {
					console.error('[AutoBackup] 恢复数据库存储失败:', e);
				}
			}

			console.log('[AutoBackup] 恢复成功');
			return true;
		} catch (e) {
			console.error('[AutoBackup] 恢复失败:', e);
			return false;
		}
	}

	/**
	 * 选择备份目录（使用浏览器 prompt 作为临时方案）
	 */
	async selectBackupPath(): Promise<string | null> {
		// 由于不使用 Tauri，这里使用简单的 prompt
		// 实际项目中可以通过 Python API 实现文件夹选择对话框
		const currentPath = this.settings.backupPath || '';
		const newPath = window.prompt('请输入备份目录路径:', currentPath);
		if (newPath && newPath.trim()) {
			this.updateSettings({ backupPath: newPath.trim() });
			return newPath.trim();
		}
		return null;
	}

	/**
	 * 手动触发备份
	 */
	async manualBackup(): Promise<boolean> {
		return this.performBackup('manual');
	}

	/**
	 * 导出到文件（下载到浏览器）
	 */
	async exportToFile(): Promise<boolean> {
		try {
			const date = new Date();
			const dateStr = date.toISOString().replace(/[:.]/g, '-').slice(0, 19);
			const filename = `aestivus-backup-manual-${dateStr}.json`;

			const payload = await this.buildFullBackupPayload('manual');
			const json = JSON.stringify(payload, null, 2);

			// 使用浏览器下载
			const blob = new Blob([json], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = filename;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);

			console.log(`[AutoBackup] 导出成功: ${filename}`);
			return true;
		} catch (e) {
			console.error('[AutoBackup] 导出失败:', e);
			return false;
		}
	}

	/**
	 * 从文件导入（使用浏览器文件选择）
	 * @param restoreDatabaseStorage 是否恢复数据库存储数据，默认 true
	 */
	async importFromFile(restoreDatabaseStorage: boolean = true): Promise<boolean> {
		return new Promise((resolve) => {
			const input = document.createElement('input');
			input.type = 'file';
			input.accept = '.json';
			input.onchange = async (e) => {
				const file = (e.target as HTMLInputElement).files?.[0];
				if (!file) {
					resolve(false);
					return;
				}

				try {
					const content = await file.text();
					const payload = JSON.parse(content) as FullBackupPayload;

					// 恢复 localStorage 数据
					if (payload.rawLocalStorage && typeof window !== 'undefined') {
						for (const [key, value] of Object.entries(payload.rawLocalStorage)) {
							try {
								localStorage.setItem(key, value);
							} catch (err) {
								console.error(`恢复 localStorage 键失败: ${key}`, err);
							}
						}
					}

					// 根据参数决定是否恢复数据库存储数据
					if (restoreDatabaseStorage && payload.databaseStorage) {
						try {
							const importResult = await storageClient.importAllStorage(payload.databaseStorage, true);
							if (importResult) {
								console.log('[AutoBackup] 数据库存储导入成功:', {
									layouts: importResult.layouts,
									presets: importResult.presets,
									defaults: importResult.defaults
								});
							}
						} catch (err) {
							console.error('[AutoBackup] 导入数据库存储失败:', err);
						}
					}

					console.log('[AutoBackup] 导入成功');
					resolve(true);
				} catch (err) {
					console.error('[AutoBackup] 导入失败:', err);
					resolve(false);
				}
			};
			input.click();
		});
	}

	/**
	 * 获取下次备份时间
	 */
	get nextBackupTime(): number | null {
		if (!this.settings.enabled || !this.settings.lastBackupTime) return null;
		return this.settings.lastBackupTime + this.settings.intervalMinutes * 60 * 1000;
	}

	/**
	 * 格式化时间
	 */
	formatTime(timestamp: number | null): string {
		if (!timestamp) return '从未';
		return new Date(timestamp).toLocaleString('zh-CN');
	}

	/**
	 * 获取已迁移到数据库的 localStorage 键名列表
	 * 这些键已经不再需要，可以安全清理
	 */
	getMigratedLocalStorageKeys(): string[] {
		// 已迁移到 SQLite 数据库的 localStorage 键
		const migratedKeys = [
			'aestival-node-layouts',      // 节点布局配置
			'aestival-layout-presets',    // 布局预设
			'aestival-default-preset',    // 默认预设配置
		];
		
		if (typeof window === 'undefined' || !window.localStorage) return [];
		
		// 返回实际存在的已迁移键
		return migratedKeys.filter(key => localStorage.getItem(key) !== null);
	}

	/**
	 * 分析已迁移的 localStorage 数据
	 * 返回每个键的大小信息
	 */
	analyzeMigratedStorage(): Array<{ key: string; size: number; lines: number }> {
		const keys = this.getMigratedLocalStorageKeys();
		return keys.map(key => {
			const value = localStorage.getItem(key) || '';
			return {
				key,
				size: new Blob([value]).size,
				lines: this.countLines(value)
			};
		});
	}

	/**
	 * 清理已迁移到数据库的 localStorage 数据
	 * @returns 清理的键数量
	 */
	cleanupMigratedStorage(): number {
		const keys = this.getMigratedLocalStorageKeys();
		let count = 0;
		
		for (const key of keys) {
			try {
				localStorage.removeItem(key);
				count++;
				console.log(`[AutoBackup] 已清理迁移数据: ${key}`);
			} catch (e) {
				console.error(`[AutoBackup] 清理失败: ${key}`, e);
			}
		}
		
		console.log(`[AutoBackup] 共清理 ${count} 个已迁移的 localStorage 键`);
		return count;
	}

	/**
	 * 销毁
	 */
	destroy() {
		this.stopScheduler();
	}
}

export const autoBackupStore = new AutoBackupStore();
