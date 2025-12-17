<script lang="ts">
	/**
	 * BorderBeam 组件 - 动态边框光束效果
	 * 参考: https://animation-svelte.vercel.app/magic/border-beam
	 */

	interface Props {
		class?: string;
		/** 光束大小 */
		size?: number;
		/** 动画持续时间（秒） */
		duration?: number;
		/** 边框宽度 */
		borderWidth?: number;
		/** 锚点位置 */
		anchor?: number;
		/** 起始颜色 */
		colorFrom?: string;
		/** 结束颜色 */
		colorTo?: string;
		/** 动画延迟（秒） */
		delay?: number;
	}

	let {
		class: className = '',
		size = 200,
		duration = 15,
		borderWidth = 1.5,
		anchor = 90,
		colorFrom = 'hsl(var(--primary))',
		colorTo = 'hsl(var(--accent))',
		delay = 0
	}: Props = $props();
</script>

<div
	class="pointer-events-none absolute inset-0 rounded-[inherit] {className}"
	style="
		--size: {size}px;
		--duration: {duration}s;
		--anchor: {anchor}%;
		--border-width: {borderWidth}px;
		--color-from: {colorFrom};
		--color-to: {colorTo};
		--delay: -{delay}s;
	"
>
	<div
		class="absolute inset-0 rounded-[inherit]"
		style="
			border: var(--border-width) solid transparent;
			mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
			mask-composite: exclude;
			-webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
			-webkit-mask-composite: xor;
		"
	>
		<div
			class="animate-border-beam absolute inset-[-1px] rounded-[inherit]"
			style="
				background: conic-gradient(
					from calc(var(--anchor) - 60deg),
					transparent 0%,
					var(--color-from) 10%,
					var(--color-to) 20%,
					transparent 30%
				);
				animation: border-beam var(--duration) linear infinite;
				animation-delay: var(--delay);
			"
		></div>
	</div>
</div>

<style>
	@keyframes border-beam {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	.animate-border-beam {
		animation: border-beam var(--duration) linear infinite;
	}
</style>
