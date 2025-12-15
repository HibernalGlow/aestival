<script lang="ts">
	import { onMount } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn, type WithElementRef } from '$lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		colSpan = 1,
		rowSpan = 1,
		clickable = false,
		resizable = false,
		gridUnit = 100, // 网格单位大小(px)
		minCols = 1,
		maxCols = 4,
		minRows = 1,
		maxRows = 6,
		onResize,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		colSpan?: number;
		rowSpan?: number;
		clickable?: boolean;
		resizable?: boolean;
		gridUnit?: number;
		minCols?: number;
		maxCols?: number;
		minRows?: number;
		maxRows?: number;
		onResize?: (cols: number, rows: number) => void;
	} = $props();

	let currentColSpan = $state(1);
	let currentRowSpan = $state(1);
	let cardElement: HTMLDivElement | null = null;
	
	// 初始化时同步 prop
	$effect(() => {
		currentColSpan = colSpan;
		currentRowSpan = rowSpan;
	});

	// 监听 resize 并 snap 到网格
	onMount(() => {
		if (!resizable || !cardElement) return;

		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect;
				// 计算应该占用的列数和行数（snap 到整数）
				const newCols = Math.max(minCols, Math.min(maxCols, Math.round(width / gridUnit)));
				const newRows = Math.max(minRows, Math.min(maxRows, Math.round(height / gridUnit)));

				if (newCols !== currentColSpan || newRows !== currentRowSpan) {
					currentColSpan = newCols;
					currentRowSpan = newRows;
					onResize?.(newCols, newRows);
				}
			}
		});

		observer.observe(cardElement);
		return () => observer.disconnect();
	});


</script>

<div
	bind:this={cardElement}
	data-slot="bento-card"
	class={cn(
		'bg-card text-card-foreground flex flex-col gap-2 rounded-3xl border p-4 shadow-sm transition-all',
		clickable && 'cursor-pointer hover:shadow-md hover:border-primary/50',
		resizable && 'resize overflow-auto',
		className
	)}
	style="grid-column: span {currentColSpan}; grid-row: span {currentRowSpan}; {resizable
		? `min-width: ${minCols * gridUnit}px; min-height: ${minRows * gridUnit}px; max-width: ${maxCols * gridUnit}px; max-height: ${maxRows * gridUnit}px;`
		: ''}"
	role={clickable ? 'button' : undefined}
	{...restProps}
>
	{@render children?.()}
	{#if resizable}
		<div
			class="absolute bottom-1 right-1 text-xs text-muted-foreground/50 pointer-events-none"
		>
			{currentColSpan}×{currentRowSpan}
		</div>
	{/if}
</div>
