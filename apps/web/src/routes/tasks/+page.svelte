<script lang="ts">
  import {
    ArrowLeft,
    CalendarDays,
    Check,
    CircleHelp,
    ClipboardCheck,
    FileText,
    Filter,
    ListChecks,
    LoaderCircle,
    Search,
    X
  } from '@lucide/svelte';

  import { ApiClientError } from '$lib/api/errors';
  import { listKnowledge, type KnowledgeObject } from '$lib/api/services/knowledge';
  import {
    listActionItems,
    updateActionItemStatus,
    type ActionItem,
    type ActionItemType,
    type ActionSourceType
  } from '$lib/api/services/action-items';

  type FilterValue = '' | ActionItemType;
  type StatusOption = { value: string; label: string };

  const typeOptions: Array<{ value: FilterValue; label: string }> = [
    { value: '', label: 'All types' },
    { value: 'task', label: 'Tasks' },
    { value: 'decision', label: 'Decisions' },
    { value: 'open_question', label: 'Open questions' }
  ];
  const sourceOptions: Array<{ value: '' | ActionSourceType; label: string }> = [
    { value: '', label: 'All sources' },
    { value: 'document', label: 'Documents' },
    { value: 'email', label: 'Email' },
    { value: 'transcript', label: 'Transcripts' },
    { value: 'audio', label: 'Meetings' }
  ];
  const taskStatuses: StatusOption[] = [
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In progress' },
    { value: 'done', label: 'Done' },
    { value: 'dismissed', label: 'Dismissed' }
  ];
  const decisionStatuses: StatusOption[] = [
    { value: 'active', label: 'Active' },
    { value: 'superseded', label: 'Superseded' },
    { value: 'retracted', label: 'Retracted' }
  ];
  const questionStatuses: StatusOption[] = [
    { value: 'open', label: 'Open' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'dismissed', label: 'Dismissed' }
  ];

  let items = $state<ActionItem[]>([]);
  let topics = $state<KnowledgeObject[]>([]);
  let summary = $state({ open_tasks: 0, recent_decisions: 0, open_questions: 0 });
  let selected = $state<ActionItem | null>(null);
  let typeFilter = $state<FilterValue>('');
  let statusFilter = $state('');
  let topicFilter = $state('');
  let sourceFilter = $state<'' | ActionSourceType>('');
  let assigneeFilter = $state('');
  let dateFilter = $state('');
  let loading = $state(true);
  let updating = $state(false);
  let signedIn = $state(true);
  let errorMessage = $state('');

  $effect(() => {
    void load();
  });

  async function load() {
    loading = true;
    try {
      const [actionResult, knowledgeResult] = await Promise.all([
        listActionItems({
          type: typeFilter || undefined,
          status: statusFilter || undefined,
          topic_id: topicFilter ? Number(topicFilter) : undefined,
          source_type: sourceFilter || undefined,
          assignee_user_id: assigneeFilter ? Number(assigneeFilter) : undefined,
          date_from: dateFilter || undefined,
          date_to: dateFilter || undefined
        }),
        listKnowledge()
      ]);
      items = actionResult.items;
      summary = actionResult.summary;
      topics = knowledgeResult.items.filter((item) => item.kind === 'topic' || item.kind === 'project');
      selected = selected ? items.find((item) => item.id === selected?.id) ?? null : null;
      signedIn = true;
      errorMessage = '';
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) signedIn = false;
      else errorMessage = error instanceof ApiClientError ? error.message : 'Action knowledge is unavailable.';
    } finally {
      loading = false;
    }
  }

  async function changeStatus(item: ActionItem, status: string) {
    if (updating || status === item.status) return;
    updating = true;
    errorMessage = '';
    try {
      const updated = await updateActionItemStatus(item.id, status);
      items = items.map((entry) => (entry.id === updated.id ? updated : entry));
      if (selected?.id === updated.id) selected = updated;
      await load();
    } catch (error) {
      errorMessage = error instanceof ApiClientError ? error.message : 'The status could not be updated.';
    } finally {
      updating = false;
    }
  }

  function statusesFor(item: ActionItem): StatusOption[] {
    if (item.type === 'task') return taskStatuses;
    if (item.type === 'decision') return decisionStatuses;
    return questionStatuses;
  }

  function typeLabel(type: ActionItemType): string {
    return type === 'open_question' ? 'Question' : type[0].toUpperCase() + type.slice(1);
  }

  function statusLabel(status: string): string {
    return status.replaceAll('_', ' ');
  }

  function availableAssignees(): Array<{ id: number; label: string }> {
    const seen = new Set<number>();
    return items.flatMap((item) => {
      if (!item.assignee || seen.has(item.assignee.id)) return [];
      seen.add(item.assignee.id);
      return [{
        id: item.assignee.id,
        label: item.assignee.display_name ?? item.assignee.username ?? `User #${item.assignee.id}`
      }];
    });
  }

  function formatDate(value: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
  }
</script>

<svelte:head>
  <title>Tasks · ThoughtHarbor</title>
  <meta name="description" content="Review tasks, decisions, and open questions across your private knowledge base." />
</svelte:head>

<div class="min-h-screen bg-white text-ink">
  <div class="mx-auto flex min-h-screen max-w-[1440px]">
    <aside class="hidden w-56 shrink-0 border-r border-slate-200 px-5 py-7 lg:block">
      <a class="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink" href="/">
        <span class="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50 text-harbor"><ListChecks size={18} /></span>
        ThoughtHarbor
      </a>
      <nav class="mt-12 space-y-2" aria-label="Primary navigation">
        {#each [['Dashboard', '/'], ['Inbox', '/'], ['Knowledge', '/knowledge'], ['Meetings', '/'], ['Documents', '/'], ['Chat / Search', '/chat'], ['Tasks', '/tasks'], ['Settings', '/settings']] as entry}
          <a class:!bg-sky-50={entry[0] === 'Tasks'} class:!text-harbor={entry[0] === 'Tasks'} class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-ink" href={entry[1]}>
            {#if entry[0] === 'Tasks'}<ClipboardCheck size={17} />{:else}<span class="h-[17px] w-[17px] rounded border border-slate-300"></span>{/if}
            {entry[0]}
          </a>
        {/each}
      </nav>
      <div class="mt-auto hidden rounded-2xl border border-slate-200 p-3 text-xs text-slate-500 lg:block">Private workspace<br /><span class="font-medium text-ink">Local data only</span></div>
    </aside>

    <main class="min-w-0 flex-1 px-5 py-6 sm:px-8 sm:py-9">
      <header class="flex items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div class="flex items-center gap-3 lg:hidden"><a class="rounded-lg p-2 text-slate-500 hover:bg-slate-50" href="/" aria-label="Back to inbox"><ArrowLeft size={18} /></a><span class="font-semibold text-ink">ThoughtHarbor</span></div>
        <label class="hidden min-w-0 max-w-md flex-1 items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-400 sm:flex"><Search size={16} /><span class="truncate">Search anything…</span><kbd class="ml-auto hidden rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 md:inline">⌘ K</kbd></label>
        <a class="ml-auto rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink" href="/">Inbox</a>
      </header>

      <section class="mx-auto max-w-6xl pt-8">
        <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h1 class="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Action knowledge</h1><p class="mt-2 text-slate-600">Tasks, decisions, and open questions from your meetings and documents.</p></div><a class="inline-flex items-center gap-2 text-sm font-medium text-harbor hover:text-sky-700" href="/knowledge"><ArrowLeft size={15} /> Knowledge overview</a></div>

        {#if !signedIn}
          <section class="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-900"><h2 class="font-semibold">Sign in to review action knowledge</h2><p class="mt-1 text-sm">Your tasks and decisions are protected by your local account.</p><a class="mt-4 inline-flex rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white" href="/login">Open local sign-in</a></section>
        {:else}
          <div class="mt-8 grid gap-3 sm:grid-cols-3">
            <div class="flex items-center gap-4 rounded-2xl border border-slate-200 p-4"><span class="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-50 text-harbor"><Check size={22} /></span><div><p class="text-2xl font-semibold text-ink">{summary.open_tasks}</p><p class="text-sm text-slate-500">Open tasks</p></div></div>
            <div class="flex items-center gap-4 rounded-2xl border border-slate-200 p-4"><span class="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-600"><FileText size={21} /></span><div><p class="text-2xl font-semibold text-ink">{summary.recent_decisions}</p><p class="text-sm text-slate-500">Recent decisions</p></div></div>
            <div class="flex items-center gap-4 rounded-2xl border border-slate-200 p-4"><span class="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700"><CircleHelp size={22} /></span><div><p class="text-2xl font-semibold text-ink">{summary.open_questions}</p><p class="text-sm text-slate-500">Open questions</p></div></div>
          </div>

          <div class="mt-8 flex items-center gap-2 text-sm font-semibold text-slate-600"><Filter size={16} /> Filter action knowledge</div>
          <div class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
            <label><span class="sr-only">Type</span><select class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" bind:value={typeFilter} onchange={() => void load()}>{#each typeOptions as option}<option value={option.value}>{option.label}</option>{/each}</select></label>
            <label><span class="sr-only">Status</span><select class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" bind:value={statusFilter} onchange={() => void load()}><option value="">All statuses</option>{#each [...taskStatuses, ...decisionStatuses, ...questionStatuses].filter((option, index, options) => options.findIndex((entry) => entry.value === option.value) === index) as option}<option value={option.value}>{option.label}</option>{/each}</select></label>
            <label><span class="sr-only">Topic or project</span><select class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" bind:value={topicFilter} onchange={() => void load()}><option value="">All topics</option>{#each topics as topic}<option value={topic.id}>{topic.title} · {topic.kind}</option>{/each}</select></label>
            <label><span class="sr-only">Source</span><select class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" bind:value={sourceFilter} onchange={() => void load()}>{#each sourceOptions as option}<option value={option.value}>{option.label}</option>{/each}</select></label>
            <label><span class="sr-only">Assignee</span><select class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" bind:value={assigneeFilter} onchange={() => void load()}><option value="">All assignees</option>{#each availableAssignees() as assignee}<option value={assignee.id}>{assignee.label}</option>{/each}</select></label>
            <label class="relative"><span class="sr-only">Date</span><CalendarDays class="pointer-events-none absolute left-3 top-3 text-slate-400" size={16} /><input class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" type="date" bind:value={dateFilter} onchange={() => void load()} /></label>
          </div>

          {#if errorMessage}<p class="mt-5 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{errorMessage}</p>{/if}
          {#if loading}<div class="mt-10 flex items-center gap-2 text-sm text-slate-500"><LoaderCircle class="animate-spin" size={18} /> Loading action knowledge…</div>{:else if !items.length}<div class="mt-8 rounded-2xl border border-slate-200 p-10 text-center"><ListChecks class="mx-auto text-slate-300" size={32} /><p class="mt-3 font-medium text-ink">Nothing matches these filters.</p><p class="mt-1 text-sm text-slate-500">Try another status or add more sources in your inbox.</p></div>{:else}
            <div class="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div class="hidden grid-cols-[minmax(150px,1.5fr)_minmax(130px,1fr)_110px_130px_138px] gap-4 border-b border-slate-200 bg-slate-50/70 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 md:grid"><span>Type</span><span>Title / content</span><span>Source</span><span>Date</span><span>Status</span></div>
              {#each items as item}
                <button class:selected-row={selected?.id === item.id} class="grid w-full gap-3 border-b border-slate-100 px-4 py-4 text-left transition last:border-0 hover:bg-sky-50/50 md:grid-cols-[minmax(150px,1.5fr)_minmax(130px,1fr)_110px_130px_138px] md:items-center md:gap-4" onclick={() => (selected = item)}>
                  <div class="flex items-center gap-2"><span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sky-50 text-harbor">{#if item.type === 'task'}<Check size={16} />{:else if item.type === 'decision'}<FileText size={16} />{:else}<CircleHelp size={16} />{/if}</span><span class="text-xs font-semibold text-slate-500">{typeLabel(item.type)}</span></div>
                  <div class="min-w-0"><p class="truncate font-semibold text-ink">{item.title ?? item.content}</p><p class="mt-1 line-clamp-1 text-xs text-slate-500">{item.title ? item.content : 'Source-grounded action item'}</p></div>
                  <div class="min-w-0 text-xs text-slate-600"><p class="truncate">{item.sources[0]?.title ?? 'Unknown source'}</p><p class="mt-1 text-slate-400">{item.sources.length} context{item.sources.length === 1 ? '' : 's'}</p></div>
                  <p class="text-xs text-slate-500">{formatDate(item.created_at)}</p>
                  <select aria-label={`Status for ${item.title ?? item.content}`} class="w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs font-semibold capitalize text-slate-700 outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" value={item.status} onchange={(event) => { event.stopPropagation(); void changeStatus(item, (event.currentTarget as HTMLSelectElement).value); }} onclick={(event) => event.stopPropagation()}>{#each statusesFor(item) as option}<option value={option.value}>{option.label}</option>{/each}</select>
                </button>
              {/each}
            </div>
          {/if}
        {/if}
      </section>
    </main>
  </div>
</div>

{#if selected}
  <div class="fixed inset-0 z-20 bg-ink/30 p-3 sm:p-6" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) selected = null; }}>
    <aside class="ml-auto h-full max-w-lg overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8" aria-label="Action item detail">
      <div class="flex items-start justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.15em] text-harbor">{typeLabel(selected.type)}</p><h2 class="mt-2 text-2xl font-semibold leading-tight text-ink">{selected.title ?? selected.content}</h2></div><button class="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-ink" aria-label="Close detail" onclick={() => (selected = null)}><X size={20} /></button></div>
      {#if selected.title}<p class="mt-4 leading-7 text-slate-600">{selected.content}</p>{/if}
      <label class="mt-7 block text-sm font-medium text-slate-600">Status<select class="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm capitalize text-ink outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100" value={selected.status} disabled={updating} onchange={(event) => void changeStatus(selected!, (event.currentTarget as HTMLSelectElement).value)}>{#each statusesFor(selected) as option}<option value={option.value}>{option.label}</option>{/each}</select></label>
      <dl class="mt-7 grid grid-cols-2 gap-5 text-sm"><div><dt class="text-slate-500">Assignee</dt><dd class="mt-1 font-medium text-ink">{selected.assignee?.display_name ?? selected.assignee?.username ?? 'Unassigned'}</dd></div><div><dt class="text-slate-500">Created</dt><dd class="mt-1 font-medium text-ink">{formatDate(selected.created_at)}</dd></div>{#if selected.due_at}<div><dt class="text-slate-500">Due date</dt><dd class="mt-1 font-medium text-ink">{formatDate(selected.due_at)}</dd></div>{/if}</dl>
      <h3 class="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Topic / project</h3><div class="mt-3 flex flex-wrap gap-2">{#if selected.topics.length}{#each selected.topics as topic}<span class="rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-medium text-slate-700">{topic.title}</span>{/each}{:else}<p class="text-sm text-slate-500">No topic or project assigned.</p>{/if}</div>
      <h3 class="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Source context</h3>
      {#if selected.sources.length}<div class="mt-3 space-y-3">{#each selected.sources as source}<details class="rounded-2xl border border-slate-200 p-4" open><summary class="cursor-pointer list-none"><div class="flex items-center gap-2 text-sm font-semibold text-harbor"><FileText size={16} />{source.title}</div><p class="mt-1 text-xs capitalize text-slate-500">{source.source_type} · chunk {source.chunk_id}</p></summary><p class="mt-3 border-l-2 border-sky-200 pl-3 text-sm leading-6 text-slate-600">{source.text}</p>{#if source.source_start_ms !== null}<p class="mt-2 text-xs text-slate-400">{source.source_start_ms}–{source.source_end_ms} ms</p>{:else}<p class="mt-2 text-xs text-slate-400">Characters {source.source_offset_start ?? 0}–{source.source_offset_end ?? 0}</p>{/if}</details>{/each}</div>{:else}<p class="mt-3 text-sm text-slate-500">No source context is available.</p>{/if}
      {#if selected.status_history.length}<h3 class="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Status history</h3><ol class="mt-3 space-y-3 border-l border-slate-200 pl-4">{#each selected.status_history as history}<li><p class="text-sm font-medium capitalize text-ink">{statusLabel(history.status)}</p><p class="mt-0.5 text-xs text-slate-500">{formatDate(history.changed_at)}{history.previous_status ? ` · from ${statusLabel(history.previous_status)}` : ''}</p></li>{/each}</ol>{/if}
      <p class="mt-8 text-xs leading-5 text-slate-400">This action item is AI-derived. Its original source remains unchanged.</p>
    </aside>
  </div>
{/if}

<style>
  .selected-row { background-color: rgb(239 246 255 / 0.75); }
</style>
