/**
 * 尺寸工具模块 - Container Query 版本
 * 
 * 迁移说明：
 * - 旧版使用 JS 传递 SizeMode 参数控制样式
 * - 新版使用 CSS Container Queries 自动响应
 * - 此文件保留类型定义和兼容函数，便于渐进式迁移
 * 
 * 使用方式：
 * 1. 容器添加 class="node-container" 声明 container context
 * 2. 子元素使用 cq-* 类名，如 cq-input, cq-button, cq-text
 * 3. 条件显示使用 cq-compact-only / cq-wide-only
 */

/** 尺寸模式类型（保留用于渐进式迁移） */
export type SizeMode = 'compact' | 'normal';

/**
 * Container Query 类名映射
 * 替代原来的 SIZE_CLASSES 对象
 */
export const CQ_CLASSES = {
  // 输入框
  input: 'cq-input',
  // 按钮
  button: 'cq-button',
  buttonIcon: 'cq-button-icon',
  buttonSm: 'cq-button-sm',
  // 图标
  icon: 'cq-icon',
  iconSm: 'cq-icon-sm',
  iconLg: 'cq-icon-lg',
  // 间距
  gap: 'cq-gap',
  gapSm: 'cq-gap-sm',
  gapLg: 'cq-gap-lg',
  space: 'cq-space-y',
  mb: 'cq-mb',
  // 文字
  text: 'cq-text',
  textSm: 'cq-text-sm',
  textLg: 'cq-text-lg',
  // 内边距
  padding: 'cq-padding',
  paddingSm: 'cq-padding-sm',
  px: 'cq-px',
  py: 'cq-py',
  // 圆角
  rounded: 'cq-rounded',
  roundedLg: 'cq-rounded-lg',
  // 高度限制
  maxHeight: 'cq-max-h',
  maxHeightSm: 'cq-max-h-sm',
  // 统计卡片
  statCard: 'cq-stat-card',
  statValue: 'cq-stat-value',
  statLabel: 'cq-stat-label',
  // Grid
  gridStats: 'cq-grid-stats',
} as const;

/** CQ 类名类型 */
export type CQClasses = typeof CQ_CLASSES;

/**
 * 获取 CQ 类名对象
 * 替代原来的 getSizeClasses(size)
 */
export function getCQClasses(): CQClasses {
  return CQ_CLASSES;
}

// ========== 兼容层（渐进式迁移用） ==========

/** 旧版样式类映射（保留用于兼容） */
export const SIZE_CLASSES = {
  compact: {
    input: 'h-7 text-xs',
    select: 'h-6 text-xs',
    button: 'h-7 text-xs',
    buttonIcon: 'h-7 w-7',
    buttonSm: 'h-6 text-xs',
    icon: 'h-3 w-3',
    iconSm: 'h-2.5 w-2.5',
    iconLg: 'h-4 w-4',
    gap: 'gap-1',
    gapSm: 'gap-0.5',
    gapLg: 'gap-2',
    space: 'space-y-2',
    spaceSm: 'space-y-1',
    spaceLg: 'space-y-3',
    mb: 'mb-2',
    mbSm: 'mb-1',
    text: 'text-xs',
    textSm: 'text-[10px]',
    textLg: 'text-sm',
    padding: 'p-1.5',
    paddingSm: 'p-1',
    paddingLg: 'p-2',
    px: 'px-2',
    py: 'py-1',
    rounded: 'rounded',
    roundedLg: 'rounded-lg',
    maxHeight: 'max-h-40',
    maxHeightSm: 'max-h-16',
    gridCols: 'grid-cols-2',
  },
  normal: {
    input: 'h-10',
    select: 'h-9 text-sm',
    button: 'h-12',
    buttonIcon: 'h-10 w-10',
    buttonSm: 'h-8',
    icon: 'h-4 w-4',
    iconSm: 'h-3 w-3',
    iconLg: 'h-5 w-5',
    gap: 'gap-2',
    gapSm: 'gap-1',
    gapLg: 'gap-3',
    space: 'space-y-3',
    spaceSm: 'space-y-2',
    spaceLg: 'space-y-4',
    mb: 'mb-4',
    mbSm: 'mb-2',
    text: 'text-sm',
    textSm: 'text-xs',
    textLg: 'text-base',
    padding: 'p-2',
    paddingSm: 'p-1.5',
    paddingLg: 'p-3',
    px: 'px-3',
    py: 'py-2',
    rounded: 'rounded-lg',
    roundedLg: 'rounded-xl',
    maxHeight: 'max-h-80',
    maxHeightSm: 'max-h-40',
    gridCols: 'grid-cols-3',
  }
} as const;

export type SizeClasses = typeof SIZE_CLASSES[SizeMode];

/** 
 * 获取指定模式的样式类（兼容旧代码）
 * @deprecated 请使用 getCQClasses() 配合 node-container 类
 */
export function getSizeClasses(size: SizeMode): SizeClasses {
  return SIZE_CLASSES[size];
}

/** 
 * 根据 isFullscreen 获取对应的 SizeMode（兼容旧代码）
 * @deprecated Container Query 自动响应，无需手动判断
 */
export function getSizeMode(isFullscreen: boolean): SizeMode {
  return isFullscreen ? 'normal' : 'compact';
}

/** 
 * 快捷辅助：根据 isFullscreen 直接获取样式类（兼容旧代码）
 * @deprecated 请使用 getCQClasses() 配合 node-container 类
 */
export function getClasses(isFullscreen: boolean): SizeClasses {
  return SIZE_CLASSES[getSizeMode(isFullscreen)];
}
