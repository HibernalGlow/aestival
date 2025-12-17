<script lang="ts">
	/**
	 * 设置内容组件 - 纯内容，不包含窗口外壳
	 * 可嵌入到独立窗口或覆盖层中使用
	 */
	import { Palette, Monitor, Info, LayoutGrid } from '@lucide/svelte';

	// 导入设置面板组件
	import ThemeSettingsPanel from '$lib/components/settings/ThemeSettingsPanel.svelte';
	import DataSettingsPanel from '$lib/components/settings/DataSettingsPanel.svelte';
	import BlockSettingsPanel from '$lib/components/settings/BlockSettingsPanel.svelte';
	import { Globe } from '$lib/components/ui/globe';

	const tabs = [
		{ value: 'theme', label: '外观', icon: Palette },
		{ value: 'blocks', label: '区块', icon: LayoutGrid },
		{ value: 'data', label: '数据', icon: Monitor },
		{ value: 'about', label: '关于', icon: Info }
	];

	let activeTab = $state<string>('theme');

	function switchTab(tabValue: string) {
		activeTab = tabValue;
	}
</script>

<!-- 设置内容（无固定定位，填充父容器） -->
<div class="flex h-full w-full flex-col text-foreground">
	<!-- 主内容区 -->
	<div class="flex flex-1 overflow-hidden">
		<!-- 左侧标签栏 -->
		<div class="w-48 shrink-0 space-y-1 overflow-auto border-r bg-secondary/30 p-2">
			{#each tabs as tab}
				{@const IconComponent = tab.icon}
				<button
					class="hover:bg-accent flex w-full items-center gap-3 rounded-lg px-4 py-3 transition-colors {activeTab ===
					tab.value
						? 'bg-primary text-primary-foreground'
						: ''}"
					onclick={() => switchTab(tab.value)}
					type="button"
				>
					<IconComponent class="h-5 w-5" />
					<span class="font-medium">{tab.label}</span>
				</button>
			{/each}
		</div>

		<!-- 右侧内容区 - 路由到对应的面板组件 -->
		<div class="flex-1 overflow-auto bg-background/80">
			{#if activeTab === 'theme'}
				<ThemeSettingsPanel />
			{:else if activeTab === 'blocks'}
				<BlockSettingsPanel />
			{:else if activeTab === 'data'}
				<DataSettingsPanel />
			{:else if activeTab === 'about'}
				<div class="flex h-full flex-col items-center justify-center space-y-6 p-6">
					<Globe width={300} height={300} />
					<div class="space-y-2 text-center">
						<h3 class="text-xl font-semibold">Aestivus</h3>
						<p class="text-sm text-muted-foreground">可视化工作流编辑器</p>
						<p class="text-xs text-muted-foreground">版本: 3.1.0</p>
					</div>
				</div>
			{:else}
				<div class="p-6">
					<h3 class="text-lg font-semibold">{tabs.find((t) => t.value === activeTab)?.label}</h3>
					<p class="text-muted-foreground mt-2 text-sm">此功能即将推出...</p>
				</div>
			{/if}
		</div>
	</div>
</div>
