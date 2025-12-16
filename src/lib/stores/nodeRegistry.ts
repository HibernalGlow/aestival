/**
 * 节点注册表 - 统一管理节点定义和组件映射
 * 
 * 添加新节点只需要在 NODE_REGISTRY 中添加一条记录
 */
import type { ComponentType } from 'svelte';
import type { NodeDefinition } from '$lib/types';

// 导入所有节点组件
import InputNode from '$lib/components/nodes/InputNode.svelte';
import OutputNode from '$lib/components/nodes/OutputNode.svelte';
import RepackuNode from '$lib/components/nodes/RepackuNode.svelte';
import RawfilterNode from '$lib/components/nodes/RawfilterNode.svelte';
import CrashuNode from '$lib/components/nodes/CrashuNode.svelte';
import TerminalNode from '$lib/components/nodes/TerminalNode.svelte';
import TrenameNode from '$lib/components/nodes/TrenameNode.svelte';
import EngineVNode from '$lib/components/nodes/EngineVNode.svelte';

/** 节点注册项 - 包含定义和组件 */
export interface NodeRegistryEntry extends NodeDefinition {
  component: ComponentType;
}

/** 节点注册表 - 所有节点的唯一定义处 */
export const NODE_REGISTRY: NodeRegistryEntry[] = [
  // ========== 输入节点 ==========
  {
    type: 'clipboard_input',
    category: 'input',
    label: '剪贴板',
    description: '读取系统剪贴板内容',
    icon: 'Clipboard',
    inputs: [],
    outputs: ['text'],
    component: InputNode
  },
  {
    type: 'folder_input',
    category: 'input',
    label: '文件夹',
    description: '选择文件夹路径',
    icon: 'Folder',
    inputs: [],
    outputs: ['path'],
    component: InputNode,
    configSchema: {
      path: { type: 'path', label: '路径', required: true }
    }
  },
  {
    type: 'path_input',
    category: 'input',
    label: '路径输入',
    description: '手动输入或拖拽路径',
    icon: 'FileInput',
    inputs: [],
    outputs: ['path'],
    component: InputNode,
    configSchema: {
      path: { type: 'string', label: '路径', required: true }
    }
  },

  // ========== 工具节点 ==========
  {
    type: 'repacku',
    category: 'tool',
    label: 'repacku',
    description: '分析目录结构并打包为压缩文件',
    icon: 'Package',
    inputs: ['path'],
    outputs: ['path'],
    component: RepackuNode,
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      types: { type: 'array', label: '文件类型', default: [] },
      delete_after: { type: 'boolean', label: '压缩后删除源', default: false }
    }
  },
  {
    type: 'rawfilter',
    category: 'tool',
    label: 'rawfilter',
    description: '分析并处理相似的压缩包文件',
    icon: 'Search',
    inputs: ['path'],
    outputs: ['path'],
    component: RawfilterNode,
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      name_only_mode: { type: 'boolean', label: '仅名称模式', default: false },
      create_shortcuts: { type: 'boolean', label: '创建快捷方式', default: false },
      trash_only: { type: 'boolean', label: '仅移动到 trash', default: false }
    }
  },
  {
    type: 'crashu',
    category: 'tool',
    label: 'crashu',
    description: '检测文件夹相似度并批量移动',
    icon: 'AlertTriangle',
    inputs: ['path'],
    outputs: ['path'],
    component: CrashuNode,
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      similarity_threshold: { type: 'number', label: '相似度阈值', default: 0.6 },
      auto_move: { type: 'boolean', label: '自动移动', default: false }
    }
  },
  {
    type: 'trename',
    category: 'tool',
    label: 'trename',
    description: '扫描目录生成 JSON，支持批量重命名和撤销',
    icon: 'FileText',
    inputs: ['path'],
    outputs: ['path'],
    component: TrenameNode,
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      include_root: { type: 'boolean', label: '包含根目录', default: true },
      include_hidden: { type: 'boolean', label: '包含隐藏文件', default: false },
      dry_run: { type: 'boolean', label: '模拟执行', default: false }
    }
  },
  {
    type: 'enginev',
    category: 'tool',
    label: 'enginev',
    description: 'Wallpaper Engine 工坊管理：扫描、过滤、预览、批量重命名',
    icon: 'Image',
    inputs: ['path'],
    outputs: ['path'],
    component: EngineVNode,
    configSchema: {
      path: { type: 'path', label: '工坊路径', required: true },
      template: { type: 'string', label: '命名模板', default: '[#{id}]{original_name}+{title}' },
      dry_run: { type: 'boolean', label: '模拟执行', default: true }
    }
  },

  // ========== 输出节点 ==========
  {
    type: 'log_output',
    category: 'output',
    label: '日志输出',
    description: '输出到日志面板',
    icon: 'Terminal',
    inputs: ['any'],
    outputs: [],
    component: OutputNode
  },
  {
    type: 'terminal',
    category: 'output',
    label: '终端',
    description: '实时显示后端终端输出',
    icon: 'Terminal',
    inputs: ['any'],
    outputs: [],
    component: TerminalNode
  }
];

// ========== 辅助函数 ==========

/** 获取节点定义（不含组件） */
export const NODE_DEFINITIONS: NodeDefinition[] = NODE_REGISTRY.map(({ component, ...def }) => def);

/** 获取 SvelteFlow 的 nodeTypes 映射 */
export function getNodeTypes(): Record<string, ComponentType> {
  const types: Record<string, ComponentType> = {};
  for (const entry of NODE_REGISTRY) {
    types[entry.type] = entry.component;
  }
  return types;
}

/** 根据类型获取节点定义 */
export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return NODE_DEFINITIONS.find(d => d.type === type);
}

/** 根据分类获取节点列表 */
export function getNodesByCategory(category: string): NodeDefinition[] {
  return NODE_DEFINITIONS.filter(d => d.category === category);
}

/** 获取节点组件 */
export function getNodeComponent(type: string): ComponentType | undefined {
  return NODE_REGISTRY.find(e => e.type === type)?.component;
}
