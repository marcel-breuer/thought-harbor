<script lang="ts">
  import { AlertCircle, Inbox, LoaderCircle } from '@lucide/svelte';
  import { Alert, AlertDescription, AlertTitle, Empty, EmptyDescription, EmptyHeader, EmptyTitle, Skeleton } from '$lib/components/ui';

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
  <div class="flex items-center gap-3 py-10 text-sm text-muted-foreground" role="status"><Skeleton class="h-5 w-5 rounded-full" /><LoaderCircle class="animate-spin text-harbor" size={20} /> Loading…</div>
{:else if error}
  <Alert class="border-red-400/40 bg-red-950/30 text-red-200" role="alert"><div class="flex items-start gap-3"><AlertCircle class="mt-0.5 shrink-0" size={18} /><div><AlertTitle>Something went wrong</AlertTitle><AlertDescription>{error}</AlertDescription></div></div></Alert>
{:else if empty}
  <Empty><EmptyHeader><Inbox class="text-muted-foreground" size={30} /><EmptyTitle>{emptyTitle}</EmptyTitle>{#if emptyDescription}<EmptyDescription>{emptyDescription}</EmptyDescription>{/if}</EmptyHeader></Empty>
{:else if children}
  {@render children()}
{/if}
