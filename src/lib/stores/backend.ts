/**
 * 后端配置 Store
 * 管理后端 API 端口，支持多实例场景
 */
import { writable, derived, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

// 默认端口
const DEFAULT_PORT = 8009;

// 后端端口 store
export const backendPort = writable<number>(DEFAULT_PORT);

// 是否已初始化
export const backendReady = writable<boolean>(false);

// 派生的 API 基础 URL
export const apiBaseUrl = derived(backendPort, ($port) => `http://127.0.0.1:${$port}`);
export const apiV1Url = derived(backendPort, ($port) => `http://127.0.0.1:${$port}/v1`);
export const wsBaseUrl = derived(backendPort, ($port) => `ws://127.0.0.1:${$port}`);

/**
 * 初始化后端连接
 * 从 Tauri 获取实际端口，并监听端口变化事件
 */
export async function initBackend(): Promise<number> {
  try {
    // 从 Tauri 获取端口
    const port = await invoke<number>('get_backend_port');
    backendPort.set(port);
    backendReady.set(true);
    console.log(`[backend] 已连接到端口 ${port}`);
    return port;
  } catch (e) {
    // 非 Tauri 环境，使用默认端口
    console.log(`[backend] 使用默认端口 ${DEFAULT_PORT}`);
    backendReady.set(true);
    return DEFAULT_PORT;
  }
}

/**
 * 监听后端就绪事件
 */
export async function listenBackendReady(): Promise<void> {
  try {
    await listen<number>('python-ready', (event) => {
      const port = event.payload;
      backendPort.set(port);
      backendReady.set(true);
      console.log(`[backend] Python 就绪，端口 ${port}`);
    });
  } catch (e) {
    // 非 Tauri 环境，忽略
  }
}

/**
 * 获取当前 API 基础 URL（同步）
 */
export function getApiBaseUrl(): string {
  return `http://127.0.0.1:${get(backendPort)}`;
}

/**
 * 获取当前 API V1 URL（同步）
 */
export function getApiV1Url(): string {
  return `http://127.0.0.1:${get(backendPort)}/v1`;
}

/**
 * 获取当前 WebSocket URL（同步）
 */
export function getWsBaseUrl(): string {
  return `ws://127.0.0.1:${get(backendPort)}`;
}
