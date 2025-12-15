/**
 * 后端 API 封装
 * 提供与 FastAPI 后端通信的统一接口
 */

const API_BASE_URL = 'http://127.0.0.1:8009';

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface NodeType {
  name: string;
  displayName: string;
  description: string;
  schema: Record<string, unknown>;
}

export interface ExecutionResult {
  success: boolean;
  message: string;
  data?: unknown;
  stats?: Record<string, number>;
}

export interface FlowData {
  id: string;
  name: string;
  description?: string;
  nodes: unknown[];
  edges: unknown[];
  createdAt: string;
  updatedAt: string;
}

/**
 * 通用 API 请求函数
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        error: `HTTP ${response.status}: ${errorText}`
      };
    }

    const data = await response.json();
    return {
      success: true,
      data
    };
  } catch (error) {
    console.error(`[BackendAPI] Request failed: ${endpoint}`, error);
    return {
      success: false,
      error: error instanceof Error ? error.message : '网络请求失败'
    };
  }
}

/**
 * 后端 API 类
 */
export class BackendAPI {
  // ==================== 健康检查 ====================

  /** 检查后端服务是否可用 */
  async healthCheck(): Promise<boolean> {
    const result = await apiRequest<{ status: string }>('/api/v1/health');
    return result.success && result.data?.status === 'ok';
  }

  // ==================== 节点类型 ====================

  /** 获取所有可用节点类型 */
  async getNodeTypes(): Promise<NodeType[]> {
    const result = await apiRequest<NodeType[]>('/api/v1/nodes/types');
    return result.data || [];
  }

  /** 获取节点类型的参数 Schema */
  async getNodeSchema(typeName: string): Promise<Record<string, unknown> | null> {
    const result = await apiRequest<Record<string, unknown>>(
      `/api/v1/nodes/types/${typeName}/schema`
    );
    return result.data || null;
  }

  // ==================== 节点执行 ====================

  /** 执行单个节点 */
  async executeNode(
    nodeType: string,
    config: Record<string, unknown>
  ): Promise<ExecutionResult> {
    const result = await apiRequest<ExecutionResult>('/api/v1/execute/node', {
      method: 'POST',
      body: JSON.stringify({ type: nodeType, config })
    });

    if (result.success && result.data) {
      return result.data;
    }

    return {
      success: false,
      message: result.error || '执行失败'
    };
  }

  /** 执行整个流程 */
  async executeFlow(flowData: FlowData): Promise<ExecutionResult> {
    const result = await apiRequest<ExecutionResult>('/api/v1/execute/flow', {
      method: 'POST',
      body: JSON.stringify(flowData)
    });

    if (result.success && result.data) {
      return result.data;
    }

    return {
      success: false,
      message: result.error || '流程执行失败'
    };
  }

  // ==================== 流程管理 ====================

  /** 保存流程 */
  async saveFlow(flowData: FlowData): Promise<ApiResponse<{ id: string }>> {
    return apiRequest('/api/v1/flows', {
      method: 'POST',
      body: JSON.stringify(flowData)
    });
  }

  /** 加载流程 */
  async loadFlow(flowId: string): Promise<FlowData | null> {
    const result = await apiRequest<FlowData>(`/api/v1/flows/${flowId}`);
    return result.data || null;
  }

  /** 获取所有流程列表 */
  async listFlows(): Promise<FlowData[]> {
    const result = await apiRequest<FlowData[]>('/api/v1/flows');
    return result.data || [];
  }

  /** 删除流程 */
  async deleteFlow(flowId: string): Promise<boolean> {
    const result = await apiRequest(`/api/v1/flows/${flowId}`, {
      method: 'DELETE'
    });
    return result.success;
  }

  // ==================== 系统功能 ====================

  /** 验证路径 */
  async validatePath(path: string): Promise<{
    valid: boolean;
    exists: boolean;
    isDir: boolean;
    isFile: boolean;
    message: string;
  }> {
    const result = await apiRequest<{
      valid: boolean;
      exists: boolean;
      is_dir: boolean;
      is_file: boolean;
      message: string;
    }>('/api/v1/system/validate-path', {
      method: 'POST',
      body: JSON.stringify({ path })
    });

    if (result.success && result.data) {
      return {
        valid: result.data.valid,
        exists: result.data.exists,
        isDir: result.data.is_dir,
        isFile: result.data.is_file,
        message: result.data.message
      };
    }

    return {
      valid: false,
      exists: false,
      isDir: false,
      isFile: false,
      message: '验证失败'
    };
  }
}

/** 后端 API 单例 */
export const backendAPI = new BackendAPI();
