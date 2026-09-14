<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowLeft, CheckCircle2, CircleAlert, LoaderCircle, ThumbsDown, ThumbsUp } from '@lucide/svelte';
  import { ApiClientError } from '$lib/api/errors';
  import { getEvaluations } from '$lib/api/services/review';
  import type { components } from '$lib/generated/api';
  import { Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '$lib/components/ui';

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
  <header class="flex items-start justify-between gap-4"><div><p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Improve the loop</p><h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Answer review.</h1><p class="mt-3 max-w-2xl text-slate-600">Your feedback makes grounded retrieval measurable without sending source data anywhere else.</p></div><Button href="/" variant="ghost" size="sm" class="text-harbor"><ArrowLeft size={16} /> Dashboard</Button></header>
  {#if !signedIn}<Card class="mt-8 border-amber-400/40 bg-amber-950/20 p-6"><h2 class="font-semibold text-amber-100">Sign in to review answers</h2><Button class="mt-4" href="/login">Open local sign-in</Button></Card>{:else if loading}<div class="mt-12 flex items-center gap-3 text-sm text-muted-foreground" role="status"><Skeleton class="h-5 w-5 rounded-full" /><LoaderCircle class="animate-spin text-harbor" size={19} /> Loading evaluation history…</div>{:else if error}<Alert class="mt-8 border-red-400/40 bg-red-950/30 text-red-200" role="alert"><AlertTitle>Review unavailable</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>{:else if summary}<section class="mt-8 grid gap-4 sm:grid-cols-4" aria-label="Evaluation summary"><Card><CardContent class="p-5"><p class="text-sm text-muted-foreground">Reviewed</p><p class="mt-2 text-3xl font-semibold text-foreground">{summary.total}</p></CardContent></Card><Card class="border-emerald-400/30 bg-emerald-950/20"><CardContent class="p-5"><p class="text-sm text-emerald-200">Supported</p><p class="mt-2 text-3xl font-semibold text-emerald-100">{summary.supported}</p></CardContent></Card><Card class="border-amber-400/30 bg-amber-950/20"><CardContent class="p-5"><p class="text-sm text-amber-200">Incomplete</p><p class="mt-2 text-3xl font-semibold text-amber-100">{summary.incomplete}</p></CardContent></Card><Card class="border-red-400/30 bg-red-950/20"><CardContent class="p-5"><p class="text-sm text-red-200">Incorrect</p><p class="mt-2 text-3xl font-semibold text-red-100">{summary.incorrect}</p></CardContent></Card></section><Card class="mt-8" aria-labelledby="history-heading"><CardHeader><div class="flex items-center justify-between gap-4"><CardTitle id="history-heading">Recent feedback</CardTitle><Badge variant="outline">{items.length} entries</Badge></div></CardHeader><CardContent>{#if items.length}<div class="divide-y divide-border">{#each items as item}<article class="flex items-start gap-4 py-4 first:pt-0 last:pb-0"><span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl {item.rating === 'supported' ? 'bg-emerald-950 text-emerald-200' : item.rating === 'incomplete' ? 'bg-amber-950 text-amber-200' : 'bg-red-950 text-red-200'}">{#if item.rating === 'supported'}<CheckCircle2 size={18} />{:else if item.rating === 'incomplete'}<CircleAlert size={18} />{:else}<ThumbsDown size={18} />{/if}</span><div class="min-w-0"><p class="font-semibold text-foreground">{label(item.rating)} answer</p><p class="mt-1 text-sm text-muted-foreground">Conversation #{item.conversation_id} · message #{item.message_id}</p>{#if item.notes}<p class="mt-2 text-sm text-foreground">{item.notes}</p>{/if}</div><time class="ml-auto shrink-0 text-xs text-muted-foreground">{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(item.created_at))}</time></article>{/each}</div>{:else}<div class="rounded-xl bg-muted/40 p-6 text-center"><ThumbsUp class="mx-auto text-muted-foreground" size={28} /><p class="mt-3 text-sm text-muted-foreground">Feedback from grounded chat will appear here.</p></div>{/if}</CardContent></Card>{/if}
</main>
