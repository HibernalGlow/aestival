<script lang="ts">
	import '../app.css';
	import TitleBar from '$lib/components/layout/TitleBar.svelte';
	import ThemeImportDialog from '$lib/components/layout/ThemeImportDialog.svelte';
	
	let { children } = $props();
</script>

<div class="h-screen flex flex-col overflow-hidden">
	<TitleBar />
	<div class="flex-1 overflow-hidden">
		{@render children()}
	</div>
</div>

<ThemeImportDialog />
