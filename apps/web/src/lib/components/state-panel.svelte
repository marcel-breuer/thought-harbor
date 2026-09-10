<script lang="ts">
  import { AlertCircle, Inbox, LoaderCircle } from '@lucide/svelte';

  let { loading = false, error = '', empty = false, emptyTitle = 'Nothing here yet.', emptyDescription, children } = $props<{
    loading?: boolean;
    error?: string;
    empty?: boolean;
    emptyTitle?: string;
    emptyDescription?: string;
    children?: import('svelte').Snippet;
  }>();
</script>

{#if loading}
  <div class="flex items-center gap-3 py-10 text-sm text-slate-500"><LoaderCircle class="animate-spin text-harbor" size={20} /> Loading…</div>
{:else if error}
  <div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700" role="alert"><div class="flex items-start gap-3"><AlertCircle class="mt-0.5 shrink-0" size={18} /><span>{error}</span></div></div>
{:else if empty}
  <div class="rounded-2xl border border-slate-200 bg-slate-50 p-8 text-center"><Inbox class="mx-auto text-slate-300" size={30} /><p class="mt-3 font-medium text-ink">{emptyTitle}</p>{#if emptyDescription}<p class="mt-1 text-sm text-slate-500">{emptyDescription}</p>{/if}</div>
{:else if children}
  {@render children()}
{/if}
