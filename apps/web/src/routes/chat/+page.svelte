<script lang="ts">
  import { ArrowUp, BookOpen, LoaderCircle, MessageCircle, Plus, UserRound } from '@lucide/svelte';
  import { askKnowledge, type ChatResponse } from '$lib/api/services/chat';

  type ChatEntry = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: ChatResponse['citations'];
    evidenceSufficient?: boolean;
  };

  let question = $state('');
  let messages = $state<ChatEntry[]>([]);
  let conversationId = $state<number | null>(null);
  let loading = $state(false);
  let error = $state('');

  function startNewConversation() {
    if (loading) return;
    messages = [];
    conversationId = null;
    question = '';
    error = '';
  }

  function handleComposerKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      void submit();
    }
  }

  async function submit() {
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    messages = [...messages, { id: `user-${Date.now()}`, role: 'user', content: trimmed }];
    question = '';
    loading = true;
    error = '';
    try {
      const response = await askKnowledge({ question: trimmed, conversation_id: conversationId });
      conversationId = response.conversation_id;
      messages = [
        ...messages,
        {
          id: `assistant-${response.message_id}`,
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          evidenceSufficient: response.evidence_sufficient
        }
      ];
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
    <button class="inline-flex shrink-0 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink disabled:opacity-50" type="button" onclick={startNewConversation} disabled={loading || !messages.length}>
      <Plus size={16} /> New conversation
    </button>
  </header>

  <section class="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
    {#if !messages.length}
      <div class="rounded-2xl bg-sky-50 p-5 text-sky-950">
        <MessageCircle size={22} />
        <p class="mt-3 font-medium">Ask a question about your meetings, documents, or email.</p>
        <p class="mt-1 text-sm text-sky-800">Follow up naturally; ThoughtHarbor keeps the conversation context and cites the exact supporting sources.</p>
      </div>
    {:else}
      <div class="space-y-6" aria-live="polite" aria-label="Chat conversation">
        {#each messages as message}
          <article class:flex-row-reverse={message.role === 'user'} class="flex items-start gap-3">
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full {message.role === 'user' ? 'bg-ink text-white' : 'bg-sky-50 text-harbor'}" aria-hidden="true">
              {#if message.role === 'user'}<UserRound size={17} />{:else}<BookOpen size={17} />{/if}
            </span>
            <div class="min-w-0 max-w-[min(90%,42rem)] {message.role === 'user' ? 'items-end' : 'items-start'}">
              <p class="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{message.role === 'user' ? 'You' : 'ThoughtHarbor'}</p>
              <div class="rounded-2xl {message.role === 'user' ? 'rounded-tr-md bg-ink text-white' : 'rounded-tl-md bg-slate-50 text-ink'} px-4 py-3">
                <p class="whitespace-pre-wrap leading-7">{message.content}</p>
              </div>
              {#if message.role === 'assistant' && message.citations?.length}
                <div class="mt-3 w-full">
                  <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</p>
                  <div class="mt-2 grid gap-2">
                    {#each message.citations as citation}
                      <details class="rounded-xl border border-slate-200 p-3">
                        <summary class="cursor-pointer list-none"><div class="flex items-center justify-between gap-3"><span class="font-semibold text-harbor">{citation.marker} · {citation.source_title ?? `Source #${citation.source_file_id}`}</span><span class="text-xs capitalize text-slate-500">{citation.source_type} · chunk {citation.chunk_id}</span></div></summary>
                        <p class="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">{citation.excerpt}</p>
                        <p class="mt-2 text-xs text-slate-500">{citation.source_start_ms !== null ? `${citation.source_start_ms}–${citation.source_end_ms} ms` : `Characters ${citation.source_offset_start ?? 0}–${citation.source_offset_end ?? 0}`}</p>
                      </details>
                    {/each}
                  </div>
                </div>
              {:else if message.role === 'assistant' && message.evidenceSufficient === false}
                <p class="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">There was not enough evidence for a reliable answer.</p>
              {/if}
            </div>
          </article>
        {/each}
        {#if loading}
          <div class="flex items-start gap-3" role="status"><span class="flex h-9 w-9 items-center justify-center rounded-full bg-sky-50 text-harbor" aria-hidden="true"><BookOpen size={17} /></span><div><p class="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">ThoughtHarbor</p><div class="flex items-center gap-2 rounded-2xl rounded-tl-md bg-slate-50 px-4 py-3 text-sm text-slate-500"><LoaderCircle class="animate-spin" size={16} /> Thinking…</div></div></div>
        {/if}
      </div>
    {/if}

    {#if error}<p class="mt-5 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{/if}

    <div class="sticky bottom-4 mt-8 rounded-2xl border border-slate-200 bg-white p-2 shadow-lg shadow-slate-200/60">
      <form class="flex items-end gap-3" onsubmit={(event) => { event.preventDefault(); void submit(); }}>
        <label class="min-w-0 flex-1"><span class="sr-only">Question</span><textarea bind:value={question} onkeydown={handleComposerKeydown} rows="2" maxlength="10000" placeholder="What did we decide about…?" class="w-full resize-none rounded-xl border-0 px-3 py-2 text-sm text-ink outline-none focus:ring-2 focus:ring-sky-100" disabled={loading}></textarea></label>
        <button class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-harbor text-white transition hover:bg-sky-600 disabled:cursor-wait disabled:opacity-60" type="submit" aria-label="Ask question" disabled={loading || !question.trim()}>{#if loading}<LoaderCircle class="animate-spin" size={20} />{:else}<ArrowUp size={20} />{/if}</button>
      </form>
      <p class="px-3 pb-1 text-xs text-slate-400">Enter to send · Shift+Enter for a new line</p>
    </div>
  </section>
</main>
