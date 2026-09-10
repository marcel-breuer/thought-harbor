<script lang="ts">
  import { onMount } from 'svelte';
  import {
    ArrowRight,
    CircleAlert,
    CircleCheck,
    FileClock,
    FileText,
    HelpCircle,
    Lightbulb,
    ListTodo,
    LoaderCircle,
    RefreshCw,
    Sparkles
  } from '@lucide/svelte';

  import { ApiClientError } from '$lib/api/errors';
  import { getDashboard, type Dashboard } from '$lib/api/services/dashboard';

  let dashboard = $state<Dashboard | null>(null);
  let loading = $state(true);
  let refreshing = $state(false);
  let signedIn = $state(true);
  let error = $state('');

  onMount(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(true), 30_000);
    return () => window.clearInterval(timer);
  });

  async function refresh(silent = false) {
    if (silent) refreshing = true;
    else loading = true;
    try {
      dashboard = await getDashboard();
      signedIn = true;
      error = '';
    } catch (reason) {
      if (reason instanceof ApiClientError && reason.status === 401) signedIn = false;
      else error = reason instanceof ApiClientError ? reason.message : 'The dashboard service is unavailable.';
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  function formatDate(value: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
  }

  function statusLabel(value: string): string {
    return value.replaceAll('_', ' ');
  }
</script>

<svelte:head>
  <title>Dashboard · ThoughtHarbor</title>
  <meta name="description" content="Your private knowledge, attention items, and recent activity." />
</svelte:head>

<main class="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
  <header class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Your knowledge cockpit</p>
      <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Good morning, Marcel.</h1>
      <p class="mt-3 max-w-2xl text-slate-600">A calm view of what changed, what needs your input, and what to move forward next.</p>
    </div>
    <button class="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm hover:border-slate-300 hover:text-ink sm:self-auto" disabled={refreshing} onclick={() => void refresh()}><RefreshCw size={16} class={refreshing ? 'animate-spin' : ''} /> Refresh</button>
  </header>

  {#if !signedIn}
    <section class="mt-8 rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-950"><h2 class="text-lg font-semibold">Sign in to see your dashboard</h2><p class="mt-2 text-sm">Your knowledge stays private to your local account.</p><a class="mt-5 inline-flex rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white" href="/login">Open local sign-in</a></section>
  {:else if loading}
    <div class="mt-12 flex items-center gap-3 text-sm text-slate-500"><LoaderCircle class="animate-spin text-harbor" size={20} /> Loading your knowledge overview…</div>
  {:else if error}
    <section class="mt-8 rounded-3xl border border-red-200 bg-red-50 p-6 text-red-800" role="alert"><h2 class="font-semibold">Dashboard unavailable</h2><p class="mt-2 text-sm">{error}</p><button class="mt-4 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white" onclick={() => void refresh()}>Try again</button></section>
  {:else if dashboard}
    <section class="mt-8 grid gap-4 sm:grid-cols-3" aria-label="Attention summary">
      <a class="rounded-3xl border border-amber-200 bg-amber-50 p-5 transition hover:-translate-y-0.5 hover:shadow-md" href="/clarifications"><p class="text-sm font-medium text-amber-800">Needs your input</p><p class="mt-2 text-3xl font-semibold text-amber-950">{dashboard.pending_clarifications.length}</p><p class="mt-1 text-xs text-amber-700">pending clarification{dashboard.pending_clarifications.length === 1 ? '' : 's'}</p></a>
      <a class="rounded-3xl border border-sky-200 bg-sky-50 p-5 transition hover:-translate-y-0.5 hover:shadow-md" href="/tasks"><p class="text-sm font-medium text-sky-800">Open actions</p><p class="mt-2 text-3xl font-semibold text-sky-950">{dashboard.open_tasks.length + dashboard.open_questions.length}</p><p class="mt-1 text-xs text-sky-700">tasks and questions to move forward</p></a>
      <a class="rounded-3xl border border-emerald-200 bg-emerald-50 p-5 transition hover:-translate-y-0.5 hover:shadow-md" href="/knowledge"><p class="text-sm font-medium text-emerald-800">Recent decisions</p><p class="mt-2 text-3xl font-semibold text-emerald-950">{dashboard.recent_decisions.length}</p><p class="mt-1 text-xs text-emerald-700">decisions in your knowledge base</p></a>
    </section>

    <div class="mt-8 grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
      <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="recent-sources-heading">
        <div class="flex items-start justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.16em] text-harbor">Activity</p><h2 id="recent-sources-heading" class="mt-2 text-xl font-semibold text-ink">Recent sources</h2></div><a class="inline-flex items-center gap-1 text-sm font-semibold text-harbor hover:text-sky-700" href="/inbox">Open inbox <ArrowRight size={15} /></a></div>
        {#if dashboard.recent_sources.length}<div class="mt-5 divide-y divide-slate-100">{#each dashboard.recent_sources as source}<a class="flex items-center gap-3 py-4 first:pt-0 last:pb-0" href={source.document_id ? `/knowledge/documents/${source.document_id}` : source.meeting_id ? `/knowledge/meetings/${source.meeting_id}` : '/inbox'}><span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">{#if source.ingestion_status === 'ready'}<CircleCheck size={19} />{:else if source.ingestion_status === 'failed'}<CircleAlert size={19} />{:else}<FileClock size={19} />{/if}</span><span class="min-w-0 flex-1"><span class="block truncate text-sm font-semibold text-ink">{source.title}</span><span class="mt-1 block text-xs capitalize text-slate-500">{source.source_type} · {statusLabel(source.ingestion_status)} · {formatDate(source.created_at)}</span></span><ArrowRight class="shrink-0 text-slate-300" size={16} /></a>{/each}</div>{:else}<div class="mt-6 rounded-2xl bg-slate-50 p-6 text-center"><FileText class="mx-auto text-slate-300" size={28} /><p class="mt-3 text-sm text-slate-500">Your recent sources will appear here.</p><a class="mt-4 inline-flex rounded-xl bg-harbor px-4 py-2.5 text-sm font-semibold text-white" href="/inbox">Add knowledge</a></div>{/if}
      </section>

      <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="topics-heading"><div class="flex items-start justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.16em] text-harbor">Context</p><h2 id="topics-heading" class="mt-2 text-xl font-semibold text-ink">Active topics & projects</h2></div><a class="text-sm font-semibold text-harbor hover:text-sky-700" href="/knowledge">View all</a></div>{#if dashboard.active_topics.length}<div class="mt-5 flex flex-wrap gap-2">{#each dashboard.active_topics as topic}<a class="rounded-full border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-sky-300 hover:text-harbor" href="/knowledge">{topic.title}<span class="ml-1 text-xs capitalize text-slate-400">{topic.kind}</span></a>{/each}</div>{:else}<p class="mt-6 text-sm text-slate-500">Topics and projects will become visible as your sources are processed.</p>{/if}</section>
    </div>

    <div class="mt-5 grid gap-5 lg:grid-cols-3">
      <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="input-heading"><div class="flex items-center gap-2 text-amber-700"><HelpCircle size={18} /><h2 id="input-heading" class="text-sm font-semibold uppercase tracking-wide">Pending input</h2></div>{#if dashboard.pending_clarifications.length}<div class="mt-5 space-y-3">{#each dashboard.pending_clarifications as item}<a class="block rounded-2xl bg-amber-50 p-4 hover:bg-amber-100" href="/clarifications"><p class="text-sm font-semibold text-amber-950">{item.question}</p><p class="mt-2 text-xs text-amber-800">{item.label} · {Math.round(item.confidence * 100)}% confidence</p></a>{/each}</div>{:else}<p class="mt-5 text-sm text-slate-500">Nothing is waiting for clarification.</p>{/if}</section>
      <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="actions-heading"><div class="flex items-center gap-2 text-sky-700"><ListTodo size={18} /><h2 id="actions-heading" class="text-sm font-semibold uppercase tracking-wide">Next actions</h2></div>{#if dashboard.open_tasks.length || dashboard.open_questions.length}<div class="mt-5 space-y-3">{#each [...dashboard.open_tasks, ...dashboard.open_questions].slice(0, 4) as item}<a class="block rounded-2xl bg-sky-50 p-4 hover:bg-sky-100" href="/tasks"><p class="text-sm font-semibold text-sky-950">{item.title || item.content}</p><p class="mt-2 text-xs capitalize text-sky-800">{item.type.replace('_', ' ')} · {statusLabel(item.status)}</p></a>{/each}</div>{:else}<p class="mt-5 text-sm text-slate-500">No open tasks or questions.</p>{/if}</section>
      <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="processing-heading"><div class="flex items-center gap-2 text-violet-700"><Sparkles size={18} /><h2 id="processing-heading" class="text-sm font-semibold uppercase tracking-wide">Processing attention</h2></div>{#if dashboard.processing_attention.length}<div class="mt-5 space-y-3">{#each dashboard.processing_attention.slice(0, 4) as job}<a class="block rounded-2xl bg-violet-50 p-4 hover:bg-violet-100" href="/inbox"><p class="text-sm font-semibold text-violet-950">{job.job_type.replace('_', ' ')}</p><p class="mt-2 text-xs capitalize text-violet-800">{statusLabel(job.status)} · job #{job.id}</p></a>{/each}</div>{:else}<p class="mt-5 text-sm text-slate-500">All processing queues are quiet.</p>{/if}</section>
    </div>

    <section class="mt-5 rounded-3xl border border-dashed border-violet-200 bg-violet-50/60 p-5 sm:p-6" aria-labelledby="insights-heading"><div class="flex items-start gap-3"><span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-violet-600"><Lightbulb size={19} /></span><div><h2 id="insights-heading" class="font-semibold text-violet-950">Proactive insights</h2><p class="mt-1 text-sm text-violet-800">AI-derived suggestions are opt-in and generated asynchronously, so opening the dashboard never starts a model run.</p>{#if dashboard.insights.length}<div class="mt-4 grid gap-3 sm:grid-cols-2">{#each dashboard.insights as insight}<article class="rounded-2xl bg-white p-4"><p class="text-xs font-semibold uppercase tracking-wide text-violet-600">AI-derived suggestion</p><h3 class="mt-2 font-semibold text-ink">{insight.title}</h3><p class="mt-2 text-sm leading-6 text-slate-600">{insight.content}</p></article>{/each}</div>{:else}<p class="mt-3 text-sm text-violet-700">No proactive suggestions are enabled yet.</p>{/if}</div></div></section>
  {/if}
</main>
