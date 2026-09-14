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
  import { Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Separator } from '$lib/components/ui';

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
    <Button href="/" variant="ghost" size="sm" class="text-harbor"><ArrowLeft size={16} /> Dashboard</Button>
  </header>

  {#if !signedIn}
    <Card class="mt-8 border-amber-400/40 bg-amber-950/20 p-6"><h2 class="font-semibold text-amber-100">Sign in to search</h2><Button class="mt-4" href="/login">Open local sign-in</Button></Card>
  {:else}
    <Card class="mt-8">
      <CardContent class="p-4 sm:p-6">
        <form class="flex flex-col gap-3 sm:flex-row" onsubmit={(event) => { event.preventDefault(); void runSearch(); }}>
          <label class="flex min-w-0 flex-1 items-center gap-3 rounded-md border border-input px-3"><SearchIcon class="shrink-0 text-muted-foreground" size={19} /><span class="sr-only">Search query</span><Input bind:value={query} class="min-w-0 border-0 bg-transparent shadow-none focus-visible:ring-0" placeholder="Search decisions, people, projects…" /></label>
          <Button type="submit" disabled={loading || !query.trim()}>{loading ? 'Searching…' : 'Search'}</Button>
        </form>
        {#if query.trim()}
          <Separator class="my-4" />
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center"><label class="min-w-0 flex-1"><span class="sr-only">Saved search name</span><Input bind:value={savedName} placeholder="Name this search for daily review" /></label><Button variant="outline" disabled={!savedName.trim() || saving} onclick={() => void saveSearch()}><Bookmark size={16} /> Save search</Button></div>
          {#if savedMessage}<p class="mt-2 text-sm text-muted-foreground" role="status">{savedMessage}</p>{/if}
        {/if}
      </CardContent>
    </Card>

    {#if error}<Alert class="mt-6 border-red-400/40 bg-red-950/30 text-red-200" role="alert"><AlertTitle>Search unavailable</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>{/if}
    {#if loading}<div class="mt-8 flex items-center gap-3 text-sm text-muted-foreground" role="status"><LoaderCircle class="animate-spin text-harbor" size={19} /> Searching indexed sources…</div>{:else if query.trim() && !results.length && !error}<Card class="mt-8 border-dashed p-8 text-center text-sm text-muted-foreground">No matching evidence was found.</Card>{:else if results.length}<section class="mt-8 space-y-3" aria-label="Search results"><div class="flex items-center gap-2"><p class="text-sm font-semibold text-muted-foreground">{results.length} matching source{results.length === 1 ? '' : 's'}</p><Badge variant="secondary">private</Badge></div>{#each results as result}<Card class="transition hover:border-primary/50"><a class="block p-5" href={sourceHref(result)}><div class="flex items-start justify-between gap-4"><div class="min-w-0"><p class="text-xs font-semibold uppercase tracking-wide text-harbor">{result.source_type} · {result.source_title ?? `Source #${result.source_file_id}`}</p><p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{result.text}</p></div><span class="shrink-0 text-xs text-muted-foreground">{Math.round(result.score * 100)}%</span></div><p class="mt-3 text-xs text-muted-foreground">Open source evidence →</p></a></Card>{/each}</section>{/if}

    <Card class="mt-10" aria-labelledby="saved-searches-heading"><CardHeader><div class="flex items-center justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.16em] text-harbor">Daily review</p><CardTitle id="saved-searches-heading" class="mt-2">Saved searches</CardTitle></div><Badge variant="outline">{savedSearches.length}</Badge></div></CardHeader><CardContent>{#if savedSearches.length}<div class="grid gap-3 sm:grid-cols-2">{#each savedSearches as saved}{#if editingId === saved.id}<div class="space-y-3 rounded-xl border border-primary/30 bg-primary/10 p-4"><Input bind:value={editingName} aria-label={`Name for ${saved.name}`} /><Input bind:value={editingQuery} aria-label={`Query for ${saved.name}`} /><div class="flex gap-2"><Button size="sm" disabled={!editingName.trim() || !editingQuery.trim()} onclick={() => void updateSearch(saved)}>Save</Button><Button size="sm" variant="outline" onclick={cancelEditing}>Cancel</Button></div></div>{:else}<div class="flex items-start gap-3 rounded-xl border border-border bg-muted/40 p-4"><a class="min-w-0 flex-1 hover:text-harbor" href={`/search?q=${encodeURIComponent(saved.query)}`}><p class="font-semibold text-foreground">{saved.name}</p><p class="mt-1 truncate text-sm text-muted-foreground">{saved.query}</p></a><div class="flex shrink-0 gap-2"><Button size="sm" variant="ghost" aria-label={`Edit ${saved.name}`} onclick={() => beginEditing(saved)}>Edit</Button><Button size="sm" variant="ghost" class="text-muted-foreground hover:text-destructive" aria-label={`Remove ${saved.name}`} onclick={() => void removeSavedSearch(saved)}>Remove</Button></div></div>{/if}{/each}</div>{:else}<p class="text-sm text-muted-foreground">Save a search above to bring it into your daily review.</p>{/if}</CardContent></Card>
  {/if}
</main>
