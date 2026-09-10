<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowRight, CalendarDays, FileText, LoaderCircle, SearchX } from '@lucide/svelte';

  import { listInbox, type InboxItem } from '$lib/api/services/inbox';
  import { ApiClientError } from '$lib/api/errors';

  type SourceOverviewType = 'document' | 'meeting';

  let { sourceType }: { sourceType: SourceOverviewType } = $props();
  let items = $state<InboxItem[]>([]);
  let loading = $state(true);
  let error = $state('');

  const title = $derived(sourceType === 'document' ? 'Your documents.' : 'Your meetings.');
  const description = $derived(
    sourceType === 'document'
      ? 'Browse uploaded documents and open their source-grounded knowledge views.'
      : 'Browse meetings with transcripts and open their source-grounded knowledge views.'
  );
  const filteredItems = $derived(
    sourceType === 'document'
      ? items.filter((item) => item.source_type === 'document')
      : items.filter((item) => item.meeting_id !== null)
  );

  onMount(() => {
    void load();
  });

  async function load() {
    loading = true;
    error = '';
    try {
      const result = await listInbox(sourceType === 'document' ? { source_type: 'document' } : {});
      items = result.items;
    } catch (reason) {
      error = reason instanceof ApiClientError ? reason.message : 'The source list is unavailable.';
    } finally {
      loading = false;
    }
  }

  function detailHref(item: InboxItem): string | null {
    if (sourceType === 'document' && item.document_id !== null) {
      return `/knowledge/documents/${item.document_id}`;
    }
    if (sourceType === 'meeting' && item.meeting_id !== null) {
      return `/knowledge/meetings/${item.meeting_id}`;
    }
    return null;
  }

  function statusLabel(item: InboxItem): string {
    return item.ingestion_status.replace('_', ' ');
  }
</script>

<svelte:head>
  <title>{sourceType === 'document' ? 'Documents' : 'Meetings'} · ThoughtHarbor</title>
  <meta name="description" content={description} />
</svelte:head>

<main class="mx-auto min-h-screen max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
  <header>
    <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Sources</p>
    <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">{title}</h1>
    <p class="mt-3 max-w-2xl text-slate-600">{description}</p>
  </header>

  {#if error}
    <div class="mt-8 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</div>
  {/if}

  {#if loading}
    <div class="mt-10 flex items-center gap-3 text-sm text-slate-500" role="status">
      <LoaderCircle class="animate-spin text-harbor" size={20} /> Loading sources…
    </div>
  {:else if !filteredItems.length}
    <section class="mt-10 rounded-3xl border border-slate-200 bg-white p-10 text-center shadow-sm">
      <SearchX class="mx-auto text-slate-300" size={34} />
      <h2 class="mt-4 text-lg font-semibold text-ink">No {sourceType === 'document' ? 'documents' : 'meetings'} yet.</h2>
      <p class="mt-2 text-sm text-slate-500">Add a source in the Inbox to see it here.</p>
      <a class="mt-5 inline-flex items-center gap-2 rounded-xl bg-harbor px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-600" href="/inbox">
        Open Inbox <ArrowRight size={16} />
      </a>
    </section>
  {:else}
    <section class="mt-10" aria-labelledby="source-list-heading">
      <div class="flex items-center justify-between gap-4">
        <h2 id="source-list-heading" class="text-xl font-semibold text-ink">{filteredItems.length} {sourceType === 'document' ? 'documents' : 'meetings'}</h2>
        <a class="text-sm font-medium text-harbor hover:text-sky-700" href="/inbox">Add source</a>
      </div>
      <div class="mt-5 grid gap-3">
        {#each filteredItems as item}
          {@const href = detailHref(item)}
          {#if href}
            <a class="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-sky-200 hover:shadow-md" href={href}>
              <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-harbor">
                {#if sourceType === 'document'}<FileText size={21} />{:else}<CalendarDays size={21} />{/if}
              </div>
              <div class="min-w-0 flex-1">
                <p class="truncate font-medium text-ink">{item.original_name}</p>
                <p class="mt-1 text-xs capitalize text-slate-500">{statusLabel(item)} · {item.media_type ?? 'Unknown type'}</p>
              </div>
              <ArrowRight class="shrink-0 text-slate-400" size={18} />
            </a>
          {:else}
            <div class="flex items-center gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white text-slate-400">
                {#if sourceType === 'document'}<FileText size={21} />{:else}<CalendarDays size={21} />{/if}
              </div>
              <div class="min-w-0 flex-1">
                <p class="truncate font-medium text-ink">{item.original_name}</p>
                <p class="mt-1 text-xs capitalize text-slate-500">{statusLabel(item)} · Detail view will be available after processing.</p>
              </div>
            </div>
          {/if}
        {/each}
      </div>
    </section>
  {/if}
</main>
