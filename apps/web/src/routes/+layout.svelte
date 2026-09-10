<script lang="ts">
  import '../app.css';
  import AppShell from '$lib/components/app-shell.svelte';

  let { children } = $props();
</script>

<AppShell>
  {@render children()}
</AppShell>
