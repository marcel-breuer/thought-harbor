<script lang="ts">
  import { ArrowLeft, Brain, LoaderCircle } from '@lucide/svelte';
  import { AiDerivedCard, PageHeader } from '$lib/components';
  import { getKnowledgeObject, listKnowledge, type KnowledgeObject, type KnowledgeObjectDetail } from '$lib/api/services/knowledge';

  let items = $state<KnowledgeObject[]>([]);
  let selected = $state<KnowledgeObjectDetail | null>(null);
  let loading = $state(true);
  let error = $state('');

  $effect(() => { void load(); });

  async function load() {
    try { items = (await listKnowledge()).items; } catch { error = 'Knowledge views are unavailable.'; } finally { loading = false; }
  }

  async function choose(item: KnowledgeObject) {
    try { selected = await getKnowledgeObject(item.id); } catch { error = 'This knowledge object is unavailable.'; }
  }
</script>

<svelte:head><title>Knowledge · ThoughtHarbor</title><meta name="description" content="Explore your private, source-grounded knowledge." /></svelte:head>

<main class="mx-auto min-h-screen max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="inline-flex items-center gap-2 text-sm font-medium text-harbor hover:text-sky-700" href="/"><ArrowLeft size={16} /> Back to inbox</a>
  <div class="mt-8"><PageHeader eyebrow="Knowledge" title="Knowledge, connected." description="Browse structured topics and projects without losing the original evidence behind them." /></div>
  {#if error}<p class="mt-6 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{/if}
  {#if loading}<LoaderCircle class="mt-10 animate-spin text-harbor" size={24} />{:else if !items.length}<section class="mt-10 rounded-3xl border border-slate-200 bg-white p-8 text-center"><Brain class="mx-auto text-slate-300" size={32} /><p class="mt-3 text-sm text-slate-500">No knowledge objects yet.</p></section>{:else}
    <div class="mt-10 grid gap-3 sm:grid-cols-2">{#each items as item}<button class="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-sky-200 hover:shadow-md" onclick={() => void choose(item)}><span class="text-xs font-semibold uppercase tracking-wide text-harbor">{item.kind}</span><h2 class="mt-2 text-lg font-semibold text-ink">{item.title}</h2>{#if item.description}<p class="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">{item.description}</p>{/if}</button>{/each}</div>
  {/if}
  {#if selected}<section class="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8"><div class="flex items-start justify-between gap-4"><div><span class="text-xs font-semibold uppercase tracking-wide text-harbor">{selected.item.kind}</span><h2 class="mt-2 text-2xl font-semibold text-ink">{selected.item.title}</h2></div><button class="text-sm font-medium text-slate-500 hover:text-ink" onclick={() => (selected = null)}>Close</button></div>{#if selected.item.description}<p class="mt-4 text-slate-600">{selected.item.description}</p>{/if}<h3 class="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Derived knowledge</h3>{#if selected.artifacts.length}<div class="mt-3 grid gap-3">{#each selected.artifacts as artifact}<AiDerivedCard title={artifact.title ?? 'Untitled insight'} content={artifact.content} kind={`AI-derived · ${artifact.kind}`}><span class="text-xs text-slate-500">{artifact.sources.length} source context{artifact.sources.length === 1 ? '' : 's'}</span></AiDerivedCard>{/each}</div>{:else}<p class="mt-3 text-sm text-slate-500">No derived knowledge is linked yet.</p>{/if}</section>{/if}
</main>
