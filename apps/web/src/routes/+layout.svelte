<script lang="ts">
  import '../app.css';
  import AppShell from '$lib/components/app-shell.svelte';

  let { children } = $props();
</script>

<AppShell>
  {#snippet children()}
    {@render children()}
  {/snippet}
</AppShell>
