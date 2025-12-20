import type { Flow } from '$lib/types';
import { getApiV1Url } from '$lib/stores/backend';

// 动态获取 API 基础 URL
const getApiBase = () => getApiV1Url();

// 重试配置
const RETRY_CONFIG = {
  maxRetries: 3,
  initialDelay: 1000,  // 1秒
  maxDelay: 5000,      // 5秒
  backoffMultiplier: 2
};

// 延迟函数
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// 带重试的请求函数
async function requestWithRetry<T>(
  path: string, 
  options?: RequestInit,
  retryCount = 0
): Promise<T> {
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      ...options
    });
    
    if (!res.ok) {
      throw new Error(`API Error: ${res.status} ${res.statusText}`);
    }
    
    return res.json();
  } catch (error) {
    // 检查是否是网络错误（后端未就绪）
    const isNetworkError = error instanceof TypeError && error.message.includes('fetch');
    
    if (isNetworkError && retryCount < RETRY_CONFIG.maxRetries) {
      const delayMs = Math.min(
        RETRY_CONFIG.initialDelay * Math.pow(RETRY_CONFIG.backoffMultiplier, retryCount),
        RETRY_CONFIG.maxDelay
      );
      console.log(`[API] Backend not ready, retrying in ${delayMs}ms (attempt ${retryCount + 1}/${RETRY_CONFIG.maxRetries})`);
      await delay(delayMs);
      return requestWithRetry<T>(path, options, retryCount + 1);
    }
    
    throw error;
  }
}

// 简单请求（不重试）
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  return requestWithRetry<T>(path, options);
}

export const api = {
  // 流程管理
  async getFlows(): Promise<Flow[]> {
    return request('/flows');
  },

  async getFlow(id: string): Promise<Flow> {
    return request(`/flows/${id}`);
  },

  async createFlow(flow: Partial<Flow>): Promise<Flow> {
    return request('/flows', {
      method: 'POST',
      body: JSON.stringify(flow)
    });
  },

  async updateFlow(id: string, flow: Partial<Flow>): Promise<Flow> {
    return request(`/flows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(flow)
    });
  },

  async deleteFlow(id: string): Promise<void> {
    await request(`/flows/${id}`, { method: 'DELETE' });
  },

  // 任务执行
  async executeFlow(flowId: string, inputs?: Record<string, unknown>): Promise<{ taskId: string }> {
    return request('/tasks/execute', {
      method: 'POST',
      body: JSON.stringify({ flowId, inputs })
    });
  },

  async getTask(taskId: string): Promise<unknown> {
    return request(`/tasks/${taskId}`);
  },

  async cancelTask(taskId: string): Promise<void> {
    await request(`/tasks/${taskId}/cancel`, { method: 'POST' });
  },

  // 工具管理
  async getTools(): Promise<unknown[]> {
    return request('/tools');
  },

  async getToolSchema(toolName: string): Promise<unknown> {
    return request(`/tools/${toolName}/schema`);
  },

  async getToolDefaults(toolName: string): Promise<{ parameters: Record<string, unknown> }> {
    return request(`/tools/${toolName}/defaults`);
  },

  async updateToolDefaults(toolName: string, parameters: Record<string, unknown>): Promise<void> {
    await request(`/tools/${toolName}/defaults`, {
      method: 'PUT',
      body: JSON.stringify({ parameters })
    });
  },

  async getToolPresets(toolName: string): Promise<unknown[]> {
    return request(`/tools/${toolName}/presets`);
  },

  async createPreset(data: {
    name: string;
    description: string;
    tool_name: string;
    parameters: Record<string, unknown>;
  }): Promise<void> {
    await request('/tools/presets', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async getLastParams(toolName: string): Promise<{ parameters: Record<string, unknown> | null }> {
    return request(`/tools/${toolName}/last-params`);
  },

  // 节点执行 API
  async executeNode(nodeType: string, config: Record<string, unknown>, options?: {
    taskId?: string;
    nodeId?: string;
  }): Promise<{
    success: boolean;
    message: string;
    data?: unknown;
    stats?: Record<string, number>;
    output_path?: string;
  }> {
    return request('/execute/node', {
      method: 'POST',
      body: JSON.stringify({
        node_type: nodeType,
        config,
        task_id: options?.taskId,
        node_id: options?.nodeId
      })
    });
  },

  async executeFlowNodes(nodes: Array<{
    id: string;
    type: string;
    config: Record<string, unknown>;
  }>, edges: Array<{
    source: string;
    target: string;
  }>): Promise<{
    success: boolean;
    message: string;
    node_results: Record<string, unknown>;
    execution_order: string[];
  }> {
    return request('/execute/flow', {
      method: 'POST',
      body: JSON.stringify({ nodes, edges })
    });
  },

  // 节点类型 API
  async getNodeTypes(): Promise<Array<{
    name: string;
    displayName: string;
    description: string;
    category: string;
    icon: string;
  }>> {
    return request('/nodes/types');
  },

  async getNodeSchema(name: string): Promise<{
    inputSchema: unknown;
    outputSchema: unknown;
  }> {
    return request(`/nodes/types/${name}/schema`);
  },

  // 系统功能
  async readClipboard(): Promise<string> {
    const data = await request<{ content: string }>('/system/clipboard');
    return data.content;
  },

  async health(): Promise<{ status: string }> {
    return request('/health');
  }
};
