/**
 * 节点注册表 - 统一管理节点定义和组件映射
 * 
 * 添加新节点只需要在 NODE_REGISTRY 中添加一条记录
 */
import type { ComponentType } from 'svelte';
import type { NodeDefinition } from '$lib/types';

// 导出类型供其他模块使用
export type { NodeDefinition } from '$lib/types';

// 导入所有节点组件
import { InputNode } from '$lib/components/nodes/input';
import { OutputNode } from '$lib/components/nodes/output';
import { TerminalNode } from '$lib/components/nodes/terminal';
import { RepackuNode } from '$lib/components/nodes/repacku';
import { RawfilterNode } from '$lib/components/nodes/rawfilter';
import { CrashuNode } from '$lib/components/nodes/crashu';
import { TrenameNode } from '$lib/components/nodes/trename';
import { EngineVNode } from '$lib/components/nodes/enginev';
import { MigrateFNode } from '$lib/components/nodes/migratefnode';
import { FormatVNode } from '$lib/components/nodes/formatv';
import { FindzNode } from '$lib/components/nodes/findz';
import { BandiaNode } from '$lib/components/nodes/bandia';
import { DissolvefNode } from '$lib/components/nodes/dissolvef';
import { SleeptNode } from '$lib/components/nodes/sleept';
import { OwithuNode } from '$lib/components/nodes/owithu';
import { LinkuNode } from '$lib/components/nodes/linku';
import { ScoolpNode } from '$lib/components/nodes/scoolp';
import { ReinstallpNode } from '$lib/components/nodes/reinstallp';
import { RecycleuNode } from '$lib/components/nodes/recycleu';

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
  {
    type: 'migratef',
    category: 'tool',
    label: 'migratef',
    description: '文件迁移：保持目录结构迁移文件和文件夹',
    icon: 'FolderInput',
    inputs: ['path'],
    outputs: ['path'],
    component: MigrateFNode,
    configSchema: {
      path: { type: 'path', label: '源路径', required: true },
      target_path: { type: 'path', label: '目标路径', required: true },
      mode: { type: 'select', label: '迁移模式', default: 'preserve' },
      action: { type: 'select', label: '操作类型', default: 'move' }
    }
  },
  {
    type: 'formatv',
    category: 'tool',
    label: 'formatv',
    description: '视频格式过滤：添加/移除 .nov 后缀，检查重复项',
    icon: 'Video',
    inputs: ['path'],
    outputs: ['path'],
    component: FormatVNode,
    configSchema: {
      path: { type: 'path', label: '目标路径', required: true },
      action: { type: 'select', label: '操作类型', default: 'scan' },
      prefix_name: { type: 'string', label: '前缀名称', default: 'hb' }
    }
  },
  {
    type: 'findz',
    category: 'tool',
    label: 'findz',
    description: '文件搜索：使用 SQL-like WHERE 语法搜索文件（支持压缩包内部）',
    icon: 'Search',
    inputs: ['path'],
    outputs: ['path'],
    component: FindzNode,
    configSchema: {
      path: { type: 'path', label: '搜索路径', required: true },
      where: { type: 'string', label: 'WHERE 过滤', default: '1' },
      action: { type: 'select', label: '操作类型', default: 'search' }
    }
  },
  {
    type: 'bandia',
    category: 'tool',
    label: 'bandia',
    description: '批量解压：使用 Bandizip 批量解压压缩包',
    icon: 'FileArchive',
    inputs: ['path'],
    outputs: ['path'],
    component: BandiaNode,
    configSchema: {
      paths: { type: 'string', label: '压缩包路径', required: false },
      delete_after: { type: 'boolean', label: '解压后删除', default: true },
      use_trash: { type: 'boolean', label: '使用回收站', default: true }
    }
  },
  {
    type: 'dissolvef',
    category: 'tool',
    label: 'dissolvef',
    description: '文件夹解散：解散嵌套/单媒体/单压缩包文件夹',
    icon: 'FolderInput',
    inputs: ['path'],
    outputs: ['path'],
    component: DissolvefNode,
    configSchema: {
      path: { type: 'path', label: '路径', required: true },
      nested: { type: 'boolean', label: '嵌套文件夹', default: true },
      media: { type: 'boolean', label: '单媒体文件夹', default: true },
      archive: { type: 'boolean', label: '单压缩包文件夹', default: true },
      direct: { type: 'boolean', label: '直接解散', default: false },
      preview: { type: 'boolean', label: '预览模式', default: false }
    }
  },
  {
    type: 'sleept',
    category: 'tool',
    label: 'sleept',
    description: '系统定时器：倒计时/指定时间/网速监控/CPU监控触发休眠关机',
    icon: 'Clock',
    inputs: ['any'],
    outputs: ['any'],
    component: SleeptNode,
    configSchema: {
      timer_mode: { type: 'select', label: '计时模式', default: 'countdown' },
      power_mode: { type: 'select', label: '电源操作', default: 'sleep' },
      hours: { type: 'number', label: '小时', default: 0 },
      minutes: { type: 'number', label: '分钟', default: 30 },
      dryrun: { type: 'boolean', label: '演练模式', default: true }
    }
  },
  {
    type: 'owithu',
    category: 'tool',
    label: 'owithu',
    description: 'Windows 右键菜单注册：从 TOML 配置注册/注销上下文菜单项',
    icon: 'MousePointer',
    inputs: ['path'],
    outputs: ['path'],
    component: OwithuNode,
    configSchema: {
      path: { type: 'path', label: 'TOML 配置路径', required: true },
      action: { type: 'select', label: '操作', default: 'preview' },
      hive: { type: 'string', label: '注册表位置', default: '' }
    }
  },
  {
    type: 'linku',
    category: 'tool',
    label: 'linku',
    description: '软链接管理：创建、移动、恢复软链接',
    icon: 'Link',
    inputs: ['path'],
    outputs: ['path'],
    component: LinkuNode,
    configSchema: {
      path: { type: 'path', label: '源路径', required: true },
      target: { type: 'path', label: '目标路径', required: false },
      action: { type: 'select', label: '操作', default: 'info' }
    }
  },
  {
    type: 'scoolp',
    category: 'tool',
    label: 'scoolp',
    description: 'Scoop 包管理：安装包、清理缓存、同步 buckets',
    icon: 'Package',
    inputs: ['any'],
    outputs: ['any'],
    component: ScoolpNode,
    configSchema: {
      action: { type: 'select', label: '操作', default: 'status' },
      packages: { type: 'array', label: '包列表', default: [] },
      buckets: { type: 'array', label: 'Buckets', default: [] }
    }
  },
  {
    type: 'reinstallp',
    category: 'tool',
    label: 'reinstallp',
    description: 'Python 包重装：扫描并重新安装 pyproject.toml 项目',
    icon: 'Download',
    inputs: ['path'],
    outputs: ['path'],
    component: ReinstallpNode,
    configSchema: {
      path: { type: 'path', label: '扫描路径', required: true },
      use_system: { type: 'boolean', label: '系统安装', default: true }
    }
  },
  {
    type: 'recycleu',
    category: 'tool',
    label: 'recycleu',
    description: '回收站清理：定时自动清空 Windows 回收站',
    icon: 'Trash2',
    inputs: ['any'],
    outputs: ['any'],
    component: RecycleuNode,
    configSchema: {
      interval: { type: 'number', label: '清理间隔(秒)', default: 10 },
      auto_start: { type: 'boolean', label: '自动启动', default: false }
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
