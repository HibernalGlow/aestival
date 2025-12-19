<script lang="ts">
  /**
   * MagicCard - 魔法卡片组件
   * 特性：鼠标跟随的聚光灯效果，悬停时高亮边框
   * 使用 CSS 变量实现主题色自适应
   */
  import { cn } from "$lib/utils";
  import { onMount } from "svelte";
  import type { Snippet } from "svelte";

  interface Props {
    /** 渐变光圈大小（像素） */
    gradientSize?: number;
    /** 渐变颜色（默认使用主题 primary 色） */
    gradientColor?: string;
    /** 渐变透明度 */
    gradientOpacity?: number;
    /** 自定义类名 */
    class?: string;
    /** 内容插槽 */
    children?: Snippet;
  }

  let {
    gradientSize = 200,
    gradientColor = "hsl(var(--primary) / 0.3)",
    gradientOpacity = 0.8,
    class: className = "",
    children
  }: Props = $props();

  let cardRef: HTMLDivElement | undefined = $state();
  let mouseX = $state(-gradientSize);
  let mouseY = $state(-gradientSize);
  let isHovering = $state(false);

  // 计算渐变背景样式
  let gradientStyle = $derived(
    `radial-gradient(${gradientSize}px circle at ${mouseX}px ${mouseY}px, ${gradientColor}, transparent 100%)`
  );

  function handleMouseMove(e: MouseEvent) {
    if (!cardRef) return;
    const rect = cardRef.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
  }

  function handleMouseEnter() {
    isHovering = true;
  }

  function handleMouseLeave() {
    isHovering = false;
    mouseX = -gradientSize;
    mouseY = -gradientSize;
  }

  onMount(() => {
    mouseX = -gradientSize;
    mouseY = -gradientSize;
  });
</script>

<div
  bind:this={cardRef}
  onmousemove={handleMouseMove}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  class={cn(
    "magic-card group/magic relative flex size-full overflow-hidden rounded-xl border text-foreground justify-center",
    className
  )}
>
  <!-- 内容层 -->
  <div class="relative z-10 w-full h-full">
    {#if children}
      {@render children()}
    {:else}
      <div class="flex items-center justify-center h-full text-center">
        <p class="text-2xl">Magic Card</p>
      </div>
    {/if}
  </div>
  
  <!-- 渐变光效层 -->
  <div
    class="pointer-events-none absolute -inset-px rounded-xl transition-opacity duration-300"
    class:opacity-0={!isHovering}
    class:opacity-100={isHovering}
    style="background: {gradientStyle}; opacity: {isHovering ? gradientOpacity : 0};"
  ></div>
</div>

<style>
  .size-full {
    width: 100%;
    height: 100%;
  }
</style>
