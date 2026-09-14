<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowLeft, Bookmark, LoaderCircle, Search as SearchIcon } from '@lucide/svelte';
  import { page } from '$app/state';
  import { ApiClientError } from '$lib/api/errors';
  import { searchKnowledge, type SearchResult } from '$lib/api/services/search';
  import {
    createSavedSearch,
    deleteSavedSearch,
    listSavedSearches,
    updateSavedSearch,
    type SavedSearch
  } from '$lib/api/services/review';

  let query = $state(page.url.searchParams.get('q') ?? '');
  let results = $state<SearchResult[]>([]);
  let savedSearches = $state<SavedSearch[]>([]);
  let loading = $state(false);
  let saving = $state(false);
  let signedIn = $state(true);
  let error = $state('');
  let savedMessage = $state('');
  let savedName = $state('');
  let editingId = $state<number | null>(null);
  let editingName = $state('');
  let editingQuery = $state('');

  onMount(() => {
    void loadSavedSearches();
    if (query.trim()) void runSearch();
  });

  async function loadSavedSearches() {
    try {
      savedSearches = await listSavedSearches();
    } catch (reason) {
      if (reason instanceof ApiClientError && reason.status === 401) signedIn = false;
    }
  }

  async function runSearch() {
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    loading = true;
    error = '';
    try {
      const response = await searchKnowledge({ q: trimmed, page: 1, page_size: 25 });
      results = response.items;
    } catch (reason) {
      error = reason instanceof ApiClientError ? reason.message : 'Search is unavailable right now.';
    } finally {
      loading = false;
    }
  }

  async function saveSearch() {
    if (!savedName.trim() || !query.trim() || saving) return;
    saving = true;
    savedMessage = '';
    try {
      const item = await createSavedSearch({ name: savedName.trim(), query: query.trim(), filters: {}, enabled: true });
      savedSearches = [...savedSearches, item].sort((left, right) => left.name.localeCompare(right.name));
      savedName = '';
      savedMessage = 'Saved for your daily review.';
    } catch (reason) {
      savedMessage = reason instanceof ApiClientError ? reason.message : 'Could not save this search.';
    } finally {
      saving = false;
    }
  }

  async function removeSavedSearch(item: SavedSearch) {
    try {
      await deleteSavedSearch(item.id);
      savedSearches = savedSearches.filter((saved) => saved.id !== item.id);
    } catch (reason) {
      savedMessage = reason instanceof ApiClientError ? reason.message : 'Could not remove this search.';
    }
  }

  function beginEditing(item: SavedSearch) {
    editingId = item.id;
    editingName = item.name;
    editingQuery = item.query;
    savedMessage = '';
  }

  function cancelEditing() {
    editingId = null;
    editingName = '';
    editingQuery = '';
  }

  async function updateSearch(item: SavedSearch) {
    if (!editingName.trim() || !editingQuery.trim()) return;
    try {
      const updated = await updateSavedSearch(item.id, {
        name: editingName.trim(),
        query: editingQuery.trim()
      });
      savedSearches = savedSearches
        .map((saved) => (saved.id === updated.id ? updated : saved))
        .sort((left, right) => left.name.localeCompare(right.name));
      savedMessage = 'Saved search updated.';
      cancelEditing();
    } catch (reason) {
      savedMessage = reason instanceof ApiClientError ? reason.message : 'Could not update this search.';
    }
  }

  function sourceHref(result: SearchResult): string {
    if (result.document_id) return `/knowledge/documents/${result.document_id}`;
    if (result.meeting_id) return `/knowledge/meetings/${result.meeting_id}`;
    return '/inbox';
  }
</script>

<svelte:head>
  <title>Search · ThoughtHarbor</title>
  <meta name="description" content="Search private ThoughtHarbor knowledge with exact source context." />
</svelte:head>

<main class="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
  <header class="flex items-start justify-between gap-4">
    <div>
      <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Find the thread</p>
      <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Search your knowledge.</h1>
      <p class="mt-3 max-w-2xl text-slate-600">Hybrid search keeps the answer close to the exact document or meeting evidence.</p>
    </div>
    <a class="inline-flex items-center gap-2 text-sm font-medium text-harbor hover:text-sky-700" href="/"><ArrowLeft size={16} /> Dashboard</a>
  </header>

  {#if !signedIn}
    <section class="mt-8 rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-950"><h2 class="font-semibold">Sign in to search</h2><a class="mt-4 inline-flex rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white" href="/login">Open local sign-in</a></section>
  {:else}
    <section class="mt-8 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
      <form class="flex flex-col gap-3 sm:flex-row" onsubmit={(event) => { event.preventDefault(); void runSearch(); }}>
        <label class="flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-slate-200 px-3"><SearchIcon class="shrink-0 text-slate-400" size={19} /><span class="sr-only">Search query</span><input bind:value={query} class="min-w-0 flex-1 border-0 py-3 text-sm text-ink outline-none" placeholder="Search decisions, people, projects…" /></label>
        <button class="rounded-xl bg-harbor px-5 py-3 text-sm font-semibold text-white hover:bg-sky-600 disabled:opacity-60" disabled={loading || !query.trim()}>{loading ? 'Searching…' : 'Search'}</button>
      </form>
      {#if query.trim()}
        <div class="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center"><label class="min-w-0 flex-1"><span class="sr-only">Saved search name</span><input bind:value={savedName} class="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="Name this search for daily review" /></label><button class="inline-flex items-center justify-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm font-semibold text-sky-800 disabled:opacity-50" disabled={!savedName.trim() || saving} onclick={() => void saveSearch()}><Bookmark size={16} /> Save search</button></div>
        {#if savedMessage}<p class="mt-2 text-sm text-slate-500" role="status">{savedMessage}</p>{/if}
      {/if}
    </section>

    {#if error}<p class="mt-6 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{/if}
    {#if loading}<div class="mt-8 flex items-center gap-3 text-sm text-slate-500" role="status"><LoaderCircle class="animate-spin text-harbor" size={19} /> Searching indexed sources…</div>{:else if query.trim() && !results.length && !error}<div class="mt-8 rounded-3xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No matching evidence was found.</div>{:else if results.length}<section class="mt-8 space-y-3" aria-label="Search results"><p class="text-sm font-semibold text-slate-500">{results.length} matching source{results.length === 1 ? '' : 's'}</p>{#each results as result}<a class="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-200 hover:shadow-md" href={sourceHref(result)}><div class="flex items-start justify-between gap-4"><div class="min-w-0"><p class="text-xs font-semibold uppercase tracking-wide text-harbor">{result.source_type} · {result.source_title ?? `Source #${result.source_file_id}`}</p><p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{result.text}</p></div><span class="shrink-0 text-xs text-slate-400">{Math.round(result.score * 100)}%</span></div><p class="mt-3 text-xs text-slate-500">Open source evidence →</p></a>{/each}</section>{/if}

    <section class="mt-10 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="saved-searches-heading"><div class="flex items-center justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.16em] text-harbor">Daily review</p><h2 id="saved-searches-heading" class="mt-2 text-xl font-semibold text-ink">Saved searches</h2></div><span class="text-sm text-slate-500">{savedSearches.length}</span></div>{#if savedSearches.length}<div class="mt-5 grid gap-3 sm:grid-cols-2">{#each savedSearches as saved}{#if editingId === saved.id}<div class="space-y-3 rounded-2xl border border-sky-100 bg-sky-50 p-4"><input bind:value={editingName} aria-label={`Name for ${saved.name}`} class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input bind:value={editingQuery} aria-label={`Query for ${saved.name}`} class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><div class="flex gap-2"><button class="rounded-lg bg-harbor px-3 py-2 text-xs font-semibold text-white disabled:opacity-50" disabled={!editingName.trim() || !editingQuery.trim()} onclick={() => void updateSearch(saved)}>Save</button><button class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600" onclick={cancelEditing}>Cancel</button></div></div>{:else}<div class="flex items-start gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4"><a class="min-w-0 flex-1 hover:text-harbor" href={`/search?q=${encodeURIComponent(saved.query)}`}><p class="font-semibold text-ink">{saved.name}</p><p class="mt-1 truncate text-sm text-slate-500">{saved.query}</p></a><div class="flex shrink-0 gap-3"><button class="text-xs font-semibold text-slate-400 hover:text-harbor" aria-label={`Edit ${saved.name}`} onclick={() => beginEditing(saved)}>Edit</button><button class="text-xs font-semibold text-slate-400 hover:text-red-600" aria-label={`Remove ${saved.name}`} onclick={() => void removeSavedSearch(saved)}>Remove</button></div></div>{/if}{/each}</div>{:else}<p class="mt-5 text-sm text-slate-500">Save a search above to bring it into your daily review.</p>{/if}</section>
  {/if}
</main>
