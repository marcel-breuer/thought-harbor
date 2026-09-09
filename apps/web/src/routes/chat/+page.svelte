<script lang="ts">
  import { ArrowUp, BookOpen, LoaderCircle } from '@lucide/svelte';
  import { askKnowledge, type ChatResponse } from '$lib/api/services/chat';

  let question = $state('');
  let answer = $state<ChatResponse | null>(null);
  let loading = $state(false);
  let error = $state('');

  async function submit() {
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    loading = true;
    error = '';
    try {
      answer = await askKnowledge({ question: trimmed, conversation_id: answer?.conversation_id });
      question = '';
    } catch {
      error = 'The local knowledge assistant is unavailable right now.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Chat · ThoughtHarbor</title>
  <meta name="description" content="Ask questions grounded in your private ThoughtHarbor sources." />
</svelte:head>

<main class="mx-auto min-h-screen max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
  <header class="flex items-start justify-between gap-4">
    <div>
      <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">ThoughtHarbor</p>
      <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Ask your knowledge.</h1>
      <p class="mt-3 max-w-xl text-slate-600">Answers stay grounded in indexed sources and keep their exact supporting context.</p>
    </div>
    <a class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink" href="/">Inbox</a>
  </header>

  <section class="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
    {#if !answer}
      <div class="rounded-2xl bg-sky-50 p-5 text-sky-950"><BookOpen size={22} /><p class="mt-3 font-medium">Ask a question about your meetings, documents, or email.</p><p class="mt-1 text-sm text-sky-800">If the sources do not contain enough evidence, ThoughtHarbor will say so.</p></div>
    {:else}
      <div class="rounded-2xl bg-slate-50 p-5"><p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Answer</p><p class="mt-3 whitespace-pre-wrap leading-7 text-ink">{answer.answer}</p></div>
      {#if answer.citations.length}
        <div class="mt-6"><p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Sources</p><div class="mt-3 grid gap-3">{#each answer.citations as citation}<details class="rounded-2xl border border-slate-200 p-4"><summary class="cursor-pointer list-none"><div class="flex items-center justify-between gap-3"><span class="font-semibold text-harbor">{citation.marker} · {citation.source_title ?? `Source #${citation.source_file_id}`}</span><span class="text-xs capitalize text-slate-500">{citation.source_type} · chunk {citation.chunk_id}</span></div></summary><p class="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">{citation.excerpt}</p><p class="mt-3 text-xs text-slate-500">{citation.source_start_ms !== null ? `${citation.source_start_ms}–${citation.source_end_ms} ms` : `Characters ${citation.source_offset_start ?? 0}–${citation.source_offset_end ?? 0}`}</p></details>{/each}</div></div>
      {:else}
        <p class="mt-5 rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">There was not enough evidence for a reliable answer.</p>
      {/if}
    {/if}

    {#if error}<p class="mt-5 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{/if}
    <form class="mt-8 flex items-end gap-3" onsubmit={(event) => { event.preventDefault(); void submit(); }}>
      <label class="min-w-0 flex-1"><span class="sr-only">Question</span><textarea bind:value={question} rows="2" maxlength="10000" placeholder="What did we decide about…?" class="w-full resize-none rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink outline-none transition focus:border-harbor focus:ring-2 focus:ring-sky-100" disabled={loading}></textarea></label>
      <button class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-harbor text-white transition hover:bg-sky-600 disabled:cursor-wait disabled:opacity-60" type="submit" aria-label="Ask question" disabled={loading || !question.trim()}>{#if loading}<LoaderCircle class="animate-spin" size={20} />{:else}<ArrowUp size={20} />{/if}</button>
    </form>
  </section>
</main>
