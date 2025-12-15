<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { cn, type WithElementRef } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		columns = 4,
		gap = "1rem",
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		columns?: number;
		gap?: string;
	} = $props();
</script>

<div
	bind:this={ref}
	data-slot="bento-grid"
	class={cn(
		"grid w-full",
		className
	)}
	style="grid-template-columns: repeat({columns}, minmax(0, 1fr)); gap: {gap};"
	{...restProps}
>
	{@render children?.()}
</div>
