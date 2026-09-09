<script lang="ts">
  import { onMount } from 'svelte';

  import { ApiClientError } from '$lib/api/errors';
  import {
    listClarifications,
    resolveClarification,
    type Clarification,
    type ClarificationResolutionRequest
  } from '$lib/api/services/clarifications';

  let items = $state<Clarification[]>([]);
  let loading = $state(true);
  let errorMessage = $state('');
  let selected = $state<Record<number, number[]>>({});
  let newTopic = $state<Record<number, string>>({});
  let resolving = $state<number | null>(null);

  onMount(() => {
    void refresh();
  });

  async function refresh() {
    loading = true;
    errorMessage = '';
    try {
      items = (await listClarifications()).items;
    } catch (error) {
      errorMessage = error instanceof ApiClientError ? error.message : 'Clarifications are unavailable.';
    } finally {
      loading = false;
    }
  }

  function toggle(itemId: number, optionId: number) {
    const current = selected[itemId] ?? [];
    selected[itemId] = current.includes(optionId)
      ? current.filter((id) => id !== optionId)
      : [...current, optionId];
  }

  async function resolve(item: Clarification, action: ClarificationResolutionRequest['action']) {
    resolving = item.id;
    errorMessage = '';
    try {
      await resolveClarification(item.id, {
        action,
        selected_knowledge_object_ids: selected[item.id] ?? [],
        new_topic_title: newTopic[item.id]?.trim() || null
      });
      items = items.filter((current) => current.id !== item.id);
    } catch (error) {
      errorMessage = error instanceof ApiClientError ? error.message : 'The resolution could not be saved.';
    } finally {
      resolving = null;
    }
  }
</script>

<svelte:head>
  <title>Clarifications · ThoughtHarbor</title>
  <meta name="description" content="Resolve uncertain ThoughtHarbor knowledge assignments." />
</svelte:head>

<main class="mx-auto min-h-screen max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="text-sm font-medium text-harbor hover:text-sky-700" href="/">← Back to inbox</a>
  <header class="mt-8">
    <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">ThoughtHarbor</p>
    <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">A human check.</h1>
    <p class="mt-3 max-w-xl text-slate-600">Review uncertain topic and project suggestions while keeping the original source evidence intact.</p>
  </header>

  {#if loading}
    <p class="mt-10 text-sm text-slate-500">Loading clarifications…</p>
  {:else if errorMessage}
    <section class="mt-10 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700" role="alert">{errorMessage}</section>
  {:else if !items.length}
    <section class="mt-10 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-ink">Nothing needs your input.</h2>
      <p class="mt-2 text-sm text-slate-600">Confident classifications are applied automatically; uncertain ones will appear here.</p>
    </section>
  {:else}
    <div class="mt-10 space-y-5">
      {#each items as item}
        <article class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Needs your input</p>
              <h2 class="mt-2 text-lg font-semibold text-ink">{item.question}</h2>
            </div>
            <span class="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">{Math.round(item.confidence * 100)}%</span>
          </div>
          <blockquote class="mt-5 rounded-2xl border-l-4 border-sky-200 bg-sky-50 px-4 py-3 text-sm leading-6 text-slate-700">“{item.source_text}”</blockquote>
          <p class="mt-2 text-xs text-slate-500">Source location: {JSON.stringify(item.source_location)}</p>
          <fieldset class="mt-5 space-y-2">
            <legend class="text-sm font-semibold text-ink">Assign to topic or project</legend>
            {#each item.options as option}
              <label class="flex min-h-11 items-center gap-3 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700">
                <input type="checkbox" checked={(selected[item.id] ?? []).includes(option.id)} onchange={() => toggle(item.id, option.id)} />
                <span>{option.title}</span><span class="ml-auto text-xs capitalize text-slate-400">{option.kind}</span>
              </label>
            {/each}
          </fieldset>
          <label class="mt-4 block text-sm font-medium text-slate-700">Or create a new topic
            <input class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none ring-harbor focus:ring-2" value={newTopic[item.id] ?? ''} oninput={(event) => (newTopic[item.id] = (event.currentTarget as HTMLInputElement).value)} placeholder="e.g. Project Aurora" />
          </label>
          <div class="mt-5 flex flex-wrap gap-2">
            <button class="rounded-xl border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm font-semibold text-sky-800 disabled:opacity-60" disabled={resolving === item.id} onclick={() => void resolve(item, 'accept')}>Accept selection</button>
            <button class="rounded-xl bg-harbor px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60" disabled={resolving === item.id} onclick={() => void resolve(item, 'assign')}>Assign selection</button>
            <button class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-60" disabled={resolving === item.id} onclick={() => void resolve(item, 'reject')}>Reject</button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</main>
