<script lang="ts">
  /**
   * AnalysisPanel - 文件分组分析面板
   * 支持按压缩包/扩展名/目录分组，提供多维度过滤和排序
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Popover from '$lib/components/ui/popover';
  import { getSizeClasses, type SizeMode } from '$lib/utils/sizeUtils';
  import {
    Package, File, Folder, BarChart3, ArrowUp, ArrowDown,
    Copy, Check, Filter, X, SlidersHorizontal
  } from '@lucide/svelte';

  /** 文件数据接口 */
  interface FileData {
    name: string;
    path: string;
    size: number;
    size_formatted: string;
    date: string;
    time: string;
    type: string;
    ext: string;
    archive: string;
    container: string;
  }

  /** 分组分析数据 */
  interface GroupAnalysis {
    key: string;
    name: string;
    fileCount: number;
    totalSize: number;
    avgSize: number;
    avgSizeFormatted: string;
    totalSizeFormatted: string;
    subStats: Record<string, number>;
  }

  /** 过滤条件 */
  interface AnalysisFilter {
    countMin: number | null;
    countMax: number | null;
    avgSizeMin: number | null;  // 字节
    avgSizeMax: number | null;
    totalSizeMin: number | null;
    totalSizeMax: number | null;
  }

  interface Props {
    files: FileData[];
    size?: SizeMode;
  }

  let { files, size = 'normal' }: Props = $props();

  // 分组和排序状态
  type GroupByField = 'archive' | 'ext' | 'dir';
  type SortField = 'name' | 'count' | 'totalSize' | 'avgSize';
  type SortOrder = 'asc' | 'desc';

  let groupBy = $state<GroupByField>('archive');
  let sortField = $state<SortField>('avgSize');
  let sortOrder = $state<SortOrder>('desc');

  // 过滤状态
  let filter = $state<AnalysisFilter>({
    countMin: 1,
    countMax: null,
    avgSizeMin: null,
    avgSizeMax: null,
    totalSizeMin: null,
    totalSizeMax: null,
  });

  // 过滤器输入（用于 UI 显示，支持带单位输入）
  let filterInputs = $state({
    countMin: '1',
    countMax: '',
    avgSizeMin: '',
    avgSizeMax: '',
    totalSizeMin: '',
    totalSizeMax: '',
  });

  // 复制状态
  let copiedGroupKey = $state<string | null>(null);

  /** 分组配置 */
  const groupByOptions: { field: GroupByField; label: string; icon: typeof Package }[] = [
    { field: 'archive', label: '压缩包', icon: Package },
    { field: 'ext', label: '扩展名', icon: File },
    { field: 'dir', label: '目录', icon: Folder },
  ];

  /** 格式化文件大小 */
  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  /** 解析大小字符串为字节数 (支持 KB, MB, GB) */
  function parseSize(str: string): number | null {
    if (!str.trim()) return null;
    const match = str.trim().match(/^([\d.]+)\s*(B|KB|MB|GB)?$/i);
    if (!match) return null;
    const num = parseFloat(match[1]);
    if (isNaN(num)) return null;
    const unit = (match[2] || 'B').toUpperCase();
    const multipliers: Record<string, number> = { B: 1, KB: 1024, MB: 1024 * 1024, GB: 1024 * 1024 * 1024 };
    return num * (multipliers[unit] || 1);
  }

  /** 解析数字输入 */
  function parseNumber(str: string): number | null {
    if (!str.trim()) return null;
    const num = parseInt(str, 10);
    return isNaN(num) ? null : num;
  }

  /** 更新过滤器 */
  function updateFilter() {
    filter = {
      countMin: parseNumber(filterInputs.countMin),
      countMax: parseNumber(filterInputs.countMax),
      avgSizeMin: parseSize(filterInputs.avgSizeMin),
      avgSizeMax: parseSize(filterInputs.avgSizeMax),
      totalSizeMin: parseSize(filterInputs.totalSizeMin),
      totalSizeMax: parseSize(filterInputs.totalSizeMax),
    };
  }

  /** 重置过滤器 */
  function resetFilter() {
    filterInputs = {
      countMin: '1',
      countMax: '',
      avgSizeMin: '',
      avgSizeMax: '',
      totalSizeMin: '',
      totalSizeMax: '',
    };
    updateFilter();
  }

  /** 检查是否有活跃的过滤条件 */
  let hasActiveFilter = $derived(
    (filter.countMin !== null && filter.countMin > 1) ||
    filter.countMax !== null ||
    filter.avgSizeMin !== null ||
    filter.avgSizeMax !== null ||
    filter.totalSizeMin !== null ||
    filter.totalSizeMax !== null
  );

  /** 获取文件的分组键 */
  function getGroupKey(file: FileData): string | null {
    switch (groupBy) {
      case 'archive':
        return file.archive || file.container || null;
      case 'ext':
        return file.ext || '(无扩展名)';
      case 'dir': {
        const fullPath = file.container ? `${file.container}//${file.path}` : file.path;
        const parts = fullPath.split(/[/\\]|\/\//);
        return parts.length > 1 ? parts.slice(0, -1).join('/') : '(根目录)';
      }
    }
  }

  /** 获取分组显示名称 */
  function getGroupName(key: string): string {
    switch (groupBy) {
      case 'archive':
        return key.split(/[/\\]/).pop() || key;
      case 'ext':
        return key.startsWith('(') ? key : `.${key}`;
      case 'dir':
        return key.split(/[/\\]|\/\//).pop() || key;
    }
  }

  /** 分组分析 */
  function analyzeByGroup(): GroupAnalysis[] {
    const groupMap = new Map<string, { files: FileData[], totalSize: number }>();

    for (const file of files) {
      const key = getGroupKey(file);
      if (key === null) continue;

      if (!groupMap.has(key)) {
        groupMap.set(key, { files: [], totalSize: 0 });
      }
      const data = groupMap.get(key)!;
      data.files.push(file);
      data.totalSize += file.size;
    }

    const results: GroupAnalysis[] = [];
    for (const [key, data] of groupMap) {
      const avgSize = data.files.length > 0 ? data.totalSize / data.files.length : 0;

      // 子统计
      const subStats: Record<string, number> = {};
      if (groupBy === 'archive' || groupBy === 'dir') {
        for (const f of data.files) {
          const ext = f.ext || '无';
          subStats[ext] = (subStats[ext] || 0) + 1;
        }
      } else if (groupBy === 'ext') {
        for (const f of data.files) {
          const container = f.archive || f.container || '文件系统';
          const name = container === '文件系统' ? container : container.split(/[/\\]/).pop() || container;
          subStats[name] = (subStats[name] || 0) + 1;
        }
      }

      results.push({
        key,
        name: getGroupName(key),
        fileCount: data.files.length,
        totalSize: data.totalSize,
        avgSize,
        avgSizeFormatted: formatSize(avgSize),
        totalSizeFormatted: formatSize(data.totalSize),
        subStats,
      });
    }

    // 应用过滤
    return results
      .filter(a => {
        if (filter.countMin !== null && a.fileCount < filter.countMin) return false;
        if (filter.countMax !== null && a.fileCount > filter.countMax) return false;
        if (filter.avgSizeMin !== null && a.avgSize < filter.avgSizeMin) return false;
        if (filter.avgSizeMax !== null && a.avgSize > filter.avgSizeMax) return false;
        if (filter.totalSizeMin !== null && a.totalSize < filter.totalSizeMin) return false;
        if (filter.totalSizeMax !== null && a.totalSize > filter.totalSizeMax) return false;
        return true;
      })
      .sort((a, b) => {
        let cmp = 0;
        switch (sortField) {
          case 'name': cmp = a.name.localeCompare(b.name); break;
          case 'count': cmp = a.fileCount - b.fileCount; break;
          case 'totalSize': cmp = a.totalSize - b.totalSize; break;
          case 'avgSize': cmp = a.avgSize - b.avgSize; break;
        }
        return sortOrder === 'desc' ? -cmp : cmp;
      });
  }

  /** 切换排序 */
  function toggleSort(field: SortField) {
    if (sortField === field) {
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      sortField = field;
      sortOrder = 'desc';
    }
  }

  /** 获取分组内的所有文件 */
  function getFilesInGroup(groupKey: string): FileData[] {
    return files.filter(f => getGroupKey(f) === groupKey);
  }

  /** 复制分组内文件路径 */
  async function copyGroupPaths(groupKey: string) {
    try {
      const groupFiles = getFilesInGroup(groupKey);
      const paths = groupFiles.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n');
      await navigator.clipboard.writeText(paths);
      copiedGroupKey = groupKey;
      setTimeout(() => { copiedGroupKey = null; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  // 派生数据
  let analysisData = $derived(analyzeByGroup());
  let currentGroupOption = $derived(groupByOptions.find(o => o.field === groupBy)!);
  let c = $derived(getSizeClasses(size));
</script>


{#if size === 'normal'}
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 标题栏：分组选择 + 过滤器 -->
    <div class="flex items-center justify-between p-2 border-b bg-muted/30 shrink-0">
      <div class="flex items-center gap-1">
        {#each groupByOptions as opt}
          <button
            class="px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors {groupBy === opt.field ? 'bg-primary/20 text-primary' : 'hover:bg-muted text-muted-foreground'}"
            onclick={() => groupBy = opt.field}
          >
            <svelte:component this={opt.icon} class="w-3 h-3" />
            {opt.label}
          </button>
        {/each}
      </div>

      <!-- 过滤器弹出框 -->
      <Popover.Root>
        <Popover.Trigger>
          <Button variant="ghost" size="sm" class="h-7 px-2 gap-1 {hasActiveFilter ? 'text-primary' : ''}">
            <SlidersHorizontal class="w-3 h-3" />
            <span class="text-xs">过滤</span>
            {#if hasActiveFilter}
              <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
            {/if}
          </Button>
        </Popover.Trigger>
        <Popover.Content class="w-72 p-3 z-[200]" align="end">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium">过滤条件</span>
              <Button variant="ghost" size="sm" class="h-6 px-2 text-xs" onclick={resetFilter}>
                重置
              </Button>
            </div>

            <!-- 文件数量范围 -->
            <div class="space-y-1">
              <label class="text-xs text-muted-foreground">文件数量</label>
              <div class="flex items-center gap-2">
                <Input
                  type="number"
                  placeholder="最小"
                  bind:value={filterInputs.countMin}
                  onchange={updateFilter}
                  class="h-7 text-xs"
                />
                <span class="text-muted-foreground">-</span>
                <Input
                  type="number"
                  placeholder="最大"
                  bind:value={filterInputs.countMax}
                  onchange={updateFilter}
                  class="h-7 text-xs"
                />
              </div>
            </div>

            <!-- 平均大小范围 -->
            <div class="space-y-1">
              <label class="text-xs text-muted-foreground">平均大小 (支持 KB/MB/GB)</label>
              <div class="flex items-center gap-2">
                <Input
                  placeholder="如 100KB"
                  bind:value={filterInputs.avgSizeMin}
                  onchange={updateFilter}
                  class="h-7 text-xs"
                />
                <span class="text-muted-foreground">-</span>
                <Input
                  placeholder="如 5MB"
                  bind:value={filterInputs.avgSizeMax}
                  onchange={updateFilter}
                  class="h-7 text-xs"
                />
              </div>
            </div>

            <!-- 总大小范围 -->
            <div class="space-y-1">
              <label class="text-xs text-muted-foreground">总大小 (支持 KB/MB/GB)</label>
              <div class="flex items-center gap-2">
                <Input
                  placeholder="如 1MB"
                  bind:value={filterInputs.totalSizeMin}
                  onchange={updateFilter}
                  class="h-7 text-xs"
                />
                <span class="text-muted-foreground">-</span>
                <Input
                  placeholder="如 1GB"
                  bind:value={filterInputs.totalSizeMax}
                  onchange={updateFilter}
                  class="h-7 text-xs"
                />
              </div>
            </div>

            <!-- 快捷过滤 -->
            <div class="pt-2 border-t">
              <div class="text-xs text-muted-foreground mb-2">快捷过滤</div>
              <div class="flex flex-wrap gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  class="h-6 px-2 text-xs"
                  onclick={() => { filterInputs.avgSizeMax = '100KB'; updateFilter(); }}
                >
                  平均&lt;100KB
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="h-6 px-2 text-xs"
                  onclick={() => { filterInputs.avgSizeMin = '1MB'; updateFilter(); }}
                >
                  平均&gt;1MB
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="h-6 px-2 text-xs"
                  onclick={() => { filterInputs.countMin = '10'; updateFilter(); }}
                >
                  ≥10文件
                </Button>
              </div>
            </div>
          </div>
        </Popover.Content>
      </Popover.Root>
    </div>

    <!-- 排序按钮 -->
    <div class="flex items-center gap-1 p-2 border-b text-xs">
      <span class="text-muted-foreground mr-1">排序:</span>
      {#each [
        { field: 'name' as SortField, label: '名称' },
        { field: 'count' as SortField, label: '数量' },
        { field: 'totalSize' as SortField, label: '总大小' },
        { field: 'avgSize' as SortField, label: '平均' }
      ] as item}
        <button
          class="px-2 py-0.5 rounded flex items-center gap-0.5 transition-colors {sortField === item.field ? 'bg-primary/20 text-primary' : 'hover:bg-muted'}"
          onclick={() => toggleSort(item.field)}
        >
          {item.label}
          {#if sortField === item.field}
            {#if sortOrder === 'desc'}
              <ArrowDown class="w-3 h-3" />
            {:else}
              <ArrowUp class="w-3 h-3" />
            {/if}
          {/if}
        </button>
      {/each}
    </div>

    <!-- 分析列表 -->
    <div class="flex-1 overflow-y-auto p-2">
      {#if analysisData.length > 0}
        <div class="space-y-2">
          {#each analysisData as group}
            <div class="group/item p-2 bg-muted/30 rounded-lg border border-border/50 hover:border-primary/30 transition-colors">
              <div class="flex items-start justify-between gap-2 mb-1">
                <span class="text-sm font-medium truncate flex-1" title={group.key}>
                  {group.name}
                </span>
                <div class="flex items-center gap-1 shrink-0">
                  <button
                    class="p-1 rounded opacity-0 group-hover/item:opacity-100 hover:bg-muted transition-all"
                    onclick={() => copyGroupPaths(group.key)}
                    title="复制该分组所有文件路径"
                  >
                    {#if copiedGroupKey === group.key}
                      <Check class="w-3 h-3 text-green-500" />
                    {:else}
                      <Copy class="w-3 h-3" />
                    {/if}
                  </button>
                  <span class="text-xs px-1.5 py-0.5 bg-orange-500/20 text-orange-600 rounded">
                    平均 {group.avgSizeFormatted}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{group.fileCount} 文件</span>
                <span>总计 {group.totalSizeFormatted}</span>
              </div>
              {#if Object.keys(group.subStats).length > 0}
                <div class="flex flex-wrap gap-1 mt-1">
                  {#each Object.entries(group.subStats).sort((a, b) => b[1] - a[1]).slice(0, 4) as [label, count]}
                    <span class="text-[10px] px-1 py-0.5 bg-muted rounded">
                      {groupBy === 'ext' ? label : `.${label}`}: {count}
                    </span>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {:else if files.length > 0}
        <div class="text-center text-muted-foreground py-4">
          <svelte:component this={currentGroupOption.icon} class="w-8 h-8 mx-auto mb-2 opacity-50" />
          <div>无匹配的分组数据</div>
          {#if hasActiveFilter}
            <Button variant="link" size="sm" class="mt-2" onclick={resetFilter}>
              清除过滤条件
            </Button>
          {/if}
        </div>
      {:else}
        <div class="text-center text-muted-foreground py-4">
          <BarChart3 class="w-8 h-8 mx-auto mb-2 opacity-50" />
          <div>搜索后显示分析</div>
        </div>
      {/if}
    </div>

    <!-- 底部统计 -->
    {#if analysisData.length > 0}
      <div class="p-2 border-t bg-muted/20 text-xs text-muted-foreground shrink-0">
        共 {analysisData.length} 个{currentGroupOption.label}
      </div>
    {/if}
  </div>
{:else}
  <!-- 紧凑模式 -->
  <div class="flex items-center justify-between mb-1">
    <span class="{c.text} font-semibold flex items-center gap-1">
      <BarChart3 class="w-3 h-3 text-orange-500" />分析
    </span>
    <span class="{c.textSm} text-muted-foreground">{analysisData.length}</span>
  </div>
  <div class="{c.maxHeight} overflow-y-auto">
    {#if analysisData.length > 0}
      <div class="space-y-0.5">
        {#each analysisData.slice(0, 5) as group}
          <div class="flex items-center justify-between text-xs">
            <span class="truncate flex-1">{group.name}</span>
            <span class="text-orange-600 shrink-0">{group.avgSizeFormatted}</span>
          </div>
        {/each}
        {#if analysisData.length > 5}
          <div class="text-[10px] text-muted-foreground">+{analysisData.length - 5} 更多</div>
        {/if}
      </div>
    {:else}
      <div class="{c.text} text-muted-foreground text-center py-2">-</div>
    {/if}
  </div>
{/if}
