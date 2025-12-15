<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { cn, type WithElementRef } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		colSpan = 1,
		rowSpan = 1,
		clickable = false,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		colSpan?: number;
		rowSpan?: number;
		clickable?: boolean;
	} = $props();

	const spanClass = $derived(() => {
		const col = colSpan > 1 ? `col-span-${colSpan}` : '';
		const row = rowSpan > 1 ? `row-span-${rowSpan}` : '';
		return `${col} ${row}`.trim();
	});
</script>

<div
	bind:this={ref}
	data-slot="bento-card"
	class={cn(
		"bg-card text-card-foreground flex flex-col gap-2 rounded-3xl border p-4 shadow-sm transition-all",
		clickable && "cursor-pointer hover:shadow-md hover:border-primary/50",
		className
	)}
	style="grid-column: span {colSpan}; grid-row: span {rowSpan};"
	role={clickable ? "button" : "article"}
	tabindex={clickable ? 0 : -1}
	{...restProps}
>
	{@render children?.()}
</div>
