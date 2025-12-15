import type { NodeDefinition } from '$lib/types';

export const NODE_DEFINITIONS: NodeDefinition[] = [
  // 输入节点
  {
    type: 'clipboard_input',
    category: 'input',
    label: '剪贴板',
    description: '读取系统剪贴板内容',
    icon: 'Clipboard',
    inputs: [],
    outputs: ['text']
  },
  {
    type: 'folder_input',
    category: 'input',
    label: '文件夹',
    description: '选择文件夹路径',
    icon: 'Folder',
    inputs: [],
    outputs: ['path'],
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
    configSchema: {
      path: { type: 'string', label: '路径', required: true }
    }
  },

  // 工具节点 - 新版（直接 import 模式）
  {
    type: 'repacku',
    category: 'tool',
    label: '文件重打包',
    description: '分析目录结构并打包为压缩文件',
    icon: 'Package',
    inputs: ['path'],
    outputs: ['path'],
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      types: { type: 'array', label: '文件类型', default: [] },
      delete_after: { type: 'boolean', label: '压缩后删除源', default: false }
    }
  },
  {
    type: 'rawfilter',
    category: 'tool',
    label: '相似文件过滤',
    description: '分析并处理相似的压缩包文件',
    icon: 'Search',
    inputs: ['path'],
    outputs: ['path'],
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
    label: '相似文件夹检测',
    description: '检测文件夹相似度并批量移动',
    icon: 'AlertTriangle',
    inputs: ['path'],
    outputs: ['path'],
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      similarity_threshold: { type: 'number', label: '相似度阈值', default: 0.6 },
      auto_move: { type: 'boolean', label: '自动移动', default: false }
    }
  },
  {
    type: 'trename',
    category: 'tool',
    label: '批量重命名',
    description: '扫描目录生成 JSON，支持批量重命名和撤销',
    icon: 'FileText',
    inputs: ['path'],
    outputs: ['path'],
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      include_root: { type: 'boolean', label: '包含根目录', default: true },
      include_hidden: { type: 'boolean', label: '包含隐藏文件', default: false },
      dry_run: { type: 'boolean', label: '模拟执行', default: false }
    }
  },
  // 工具节点 - 旧版（兼容）
  {
    type: 'tool_repacku',
    category: 'tool',
    label: 'Repacku (旧)',
    description: '文件重打包工具',
    icon: 'Package',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_samea',
    category: 'tool',
    label: 'Samea',
    description: '相似文件分析',
    icon: 'Search',
    inputs: ['path'],
    outputs: ['path', 'report'],
    configSchema: {
      threshold: { type: 'number', label: '相似度阈值', default: 0.9 },
      method: { type: 'select', label: '比较方法', options: ['hash', 'pixel'], default: 'hash' }
    }
  },
  {
    type: 'tool_crashu',
    category: 'tool',
    label: 'Crashu (旧)',
    description: '崩溃文件处理',
    icon: 'AlertTriangle',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_migratef',
    category: 'tool',
    label: 'Migratef',
    description: '文件迁移工具',
    icon: 'FolderSync',
    inputs: ['path'],
    outputs: ['path'],
    configSchema: {
      target: { type: 'path', label: '目标路径', required: true },
      mode: { type: 'select', label: '模式', options: ['copy', 'move'], default: 'move' },
      existing_dir: { type: 'select', label: '已存在处理', options: ['skip', 'merge', 'replace'], default: 'merge' }
    }
  },
  {
    type: 'tool_nameu',
    category: 'tool',
    label: 'Nameu',
    description: '文件命名工具',
    icon: 'FileText',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_formatv',
    category: 'tool',
    label: 'Formatv',
    description: '视频格式化',
    icon: 'Video',
    inputs: ['path'],
    outputs: ['path']
  },

  // 输出节点
  {
    type: 'log_output',
    category: 'output',
    label: '日志输出',
    description: '输出到日志面板',
    icon: 'Terminal',
    inputs: ['any'],
    outputs: []
  },
  {
    type: 'terminal',
    category: 'output',
    label: '终端输出',
    description: '实时显示后端终端输出',
    icon: 'Terminal',
    inputs: ['any'],
    outputs: []
  }
];

export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return NODE_DEFINITIONS.find(d => d.type === type);
}

export function getNodesByCategory(category: string): NodeDefinition[] {
  return NODE_DEFINITIONS.filter(d => d.category === category);
}
