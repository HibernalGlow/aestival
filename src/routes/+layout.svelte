<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import ThemeImportDialog from '$lib/components/layout/ThemeImportDialog.svelte';
	import SettingsOverlay from '$lib/components/settings/SettingsOverlay.svelte';
	import { initBackend, listenBackendReady } from '$lib/stores/backend';
	
	let { children } = $props();
	
	// 初始化后端连接
	onMount(() => {
		initBackend();
		listenBackendReady();
	});
</script>

<div class="h-screen flex flex-col overflow-hidden">
	<div class="flex-1 overflow-hidden">
		{@render children()}
	</div>
</div>

<ThemeImportDialog />
<SettingsOverlay />
