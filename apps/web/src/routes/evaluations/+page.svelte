<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowLeft, CheckCircle2, CircleAlert, LoaderCircle, ThumbsDown, ThumbsUp } from '@lucide/svelte';
  import { ApiClientError } from '$lib/api/errors';
  import { getEvaluations } from '$lib/api/services/review';
  import type { components } from '$lib/generated/api';

  type Evaluation = components['schemas']['AnswerEvaluationResponse'];
  let items = $state<Evaluation[]>([]);
  let summary = $state<components['schemas']['EvaluationSummaryResponse'] | null>(null);
  let loading = $state(true);
  let signedIn = $state(true);
  let error = $state('');

  onMount(() => { void load(); });

  async function load() {
    try {
      const response = await getEvaluations();
      items = response.items;
      summary = response.summary;
    } catch (reason) {
      if (reason instanceof ApiClientError && reason.status === 401) signedIn = false;
      else error = reason instanceof ApiClientError ? reason.message : 'Evaluation data is unavailable.';
    } finally {
      loading = false;
    }
  }

  function label(rating: string): string { return rating === 'supported' ? 'Supported' : rating === 'incomplete' ? 'Incomplete' : 'Incorrect'; }
</script>

<svelte:head>
  <title>Answer review · ThoughtHarbor</title>
  <meta name="description" content="Review feedback on grounded ThoughtHarbor answers." />
</svelte:head>

<main class="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
  <header class="flex items-start justify-between gap-4"><div><p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Improve the loop</p><h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Answer review.</h1><p class="mt-3 max-w-2xl text-slate-600">Your feedback makes grounded retrieval measurable without sending source data anywhere else.</p></div><a class="inline-flex items-center gap-2 text-sm font-medium text-harbor hover:text-sky-700" href="/"><ArrowLeft size={16} /> Dashboard</a></header>
  {#if !signedIn}<section class="mt-8 rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-950"><h2 class="font-semibold">Sign in to review answers</h2><a class="mt-4 inline-flex rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white" href="/login">Open local sign-in</a></section>{:else if loading}<div class="mt-12 flex items-center gap-3 text-sm text-slate-500" role="status"><LoaderCircle class="animate-spin text-harbor" size={19} /> Loading evaluation history…</div>{:else if error}<p class="mt-8 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{:else if summary}<section class="mt-8 grid gap-4 sm:grid-cols-4" aria-label="Evaluation summary"><div class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><p class="text-sm text-slate-500">Reviewed</p><p class="mt-2 text-3xl font-semibold text-ink">{summary.total}</p></div><div class="rounded-3xl border border-emerald-200 bg-emerald-50 p-5"><p class="text-sm text-emerald-800">Supported</p><p class="mt-2 text-3xl font-semibold text-emerald-950">{summary.supported}</p></div><div class="rounded-3xl border border-amber-200 bg-amber-50 p-5"><p class="text-sm text-amber-800">Incomplete</p><p class="mt-2 text-3xl font-semibold text-amber-950">{summary.incomplete}</p></div><div class="rounded-3xl border border-red-200 bg-red-50 p-5"><p class="text-sm text-red-800">Incorrect</p><p class="mt-2 text-3xl font-semibold text-red-950">{summary.incorrect}</p></div></section><section class="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="history-heading"><h2 id="history-heading" class="text-xl font-semibold text-ink">Recent feedback</h2>{#if items.length}<div class="mt-5 divide-y divide-slate-100">{#each items as item}<article class="flex items-start gap-4 py-4 first:pt-0 last:pb-0"><span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl {item.rating === 'supported' ? 'bg-emerald-50 text-emerald-700' : item.rating === 'incomplete' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}">{#if item.rating === 'supported'}<CheckCircle2 size={18} />{:else if item.rating === 'incomplete'}<CircleAlert size={18} />{:else}<ThumbsDown size={18} />{/if}</span><div class="min-w-0"><p class="font-semibold text-ink">{label(item.rating)} answer</p><p class="mt-1 text-sm text-slate-500">Conversation #{item.conversation_id} · message #{item.message_id}</p>{#if item.notes}<p class="mt-2 text-sm text-slate-700">{item.notes}</p>{/if}</div><time class="ml-auto shrink-0 text-xs text-slate-400">{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(item.created_at))}</time></article>{/each}</div>{:else}<div class="mt-5 rounded-2xl bg-slate-50 p-6 text-center"><ThumbsUp class="mx-auto text-slate-300" size={28} /><p class="mt-3 text-sm text-slate-500">Feedback from grounded chat will appear here.</p></div>{/if}</section>{/if}
</main>
