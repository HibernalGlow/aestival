<script lang="ts">
	/**
	 * Globe 组件 - 基于 cobe 的 3D 地球动画
	 * 参考: https://animation-svelte.vercel.app/magic/globe
	 */
	import { onMount, onDestroy } from 'svelte';
	import createGlobe from 'cobe';

	interface Props {
		class?: string;
		width?: number;
		height?: number;
	}

	let { class: className = '', width = 400, height = 400 }: Props = $props();

	let canvasRef: HTMLCanvasElement;
	let phi = 0;
	let globe: ReturnType<typeof createGlobe> | null = null;

	onMount(() => {
		globe = createGlobe(canvasRef, {
			devicePixelRatio: 2,
			width: width * 2,
			height: height * 2,
			phi: 0,
			theta: 0.3,
			dark: 1,
			diffuse: 1.2,
			mapSamples: 16000,
			mapBrightness: 6,
			baseColor: [0.3, 0.3, 0.3],
			markerColor: [0.1, 0.8, 1],
			glowColor: [0.1, 0.1, 0.1],
			markers: [
				// 一些示例标记点
				{ location: [37.7595, -122.4367], size: 0.03 }, // San Francisco
				{ location: [40.7128, -74.006], size: 0.03 }, // New York
				{ location: [51.5074, -0.1278], size: 0.03 }, // London
				{ location: [35.6762, 139.6503], size: 0.03 }, // Tokyo
				{ location: [31.2304, 121.4737], size: 0.03 }, // Shanghai
				{ location: [39.9042, 116.4074], size: 0.03 } // Beijing
			],
			onRender: (state) => {
				// 自动旋转
				state.phi = phi;
				phi += 0.005;
			}
		});
	});

	onDestroy(() => {
		if (globe) {
			globe.destroy();
		}
	});
</script>

<div class="flex items-center justify-center {className}">
	<canvas
		bind:this={canvasRef}
		style="width: {width}px; height: {height}px; aspect-ratio: 1;"
		class="opacity-90"
	></canvas>
</div>
