<script lang="ts">
  import { onMount } from 'svelte';
  import { FileAudio, FileText, Inbox as InboxIcon, Mail, RefreshCw, Upload, X } from '@lucide/svelte';

  import { ApiClientError } from '$lib/api/errors';
  import {
    listInbox,
    retryInboxItem,
    uploadInboxFile,
    type InboxItem,
    type IngestionStatus,
    type SourceType
  } from '$lib/api/services/inbox';

  const statuses: Array<{ value: IngestionStatus | ''; label: string }> = [
    { value: '', label: 'All statuses' },
    { value: 'queued', label: 'Queued' },
    { value: 'parsing', label: 'Parsing' },
    { value: 'transcribing', label: 'Transcribing' },
    { value: 'analysing', label: 'Analysing' },
    { value: 'ready', label: 'Ready' },
    { value: 'needs_input', label: 'Needs input' },
    { value: 'failed', label: 'Failed' }
  ];
  const sourceTypes: Array<{ value: SourceType | ''; label: string }> = [
    { value: '', label: 'All types' },
    { value: 'document', label: 'Documents' },
    { value: 'transcript', label: 'Transcripts' },
    { value: 'email', label: 'Email' },
    { value: 'audio', label: 'Audio' }
  ];
  const activeStatuses = new Set<IngestionStatus>([
    'queued',
    'parsing',
    'transcribing',
    'analysing'
  ]);

  let items = $state<InboxItem[]>([]);
  let selected = $state<InboxItem | null>(null);
  let statusFilter = $state<IngestionStatus | ''>('');
  let typeFilter = $state<SourceType | ''>('');
  let loading = $state(true);
  let uploading = $state(false);
  let uploadProgress = $state(0);
  let dragActive = $state(false);
  let errorMessage = $state('');
  let signedIn = $state(true);
  let fileInput = $state<HTMLInputElement>();

  onMount(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (items.some((item) => activeStatuses.has(item.ingestion_status))) void refresh(true);
    }, 3000);
    return () => window.clearInterval(timer);
  });

  async function refresh(silent = false) {
    if (!silent) loading = true;
    try {
      const result = await listInbox({
        status: statusFilter || undefined,
        source_type: typeFilter || undefined
      });
      items = result.items;
      if (selected) selected = items.find((item) => item.id === selected?.id) ?? selected;
      signedIn = true;
      errorMessage = '';
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) signedIn = false;
      else errorMessage = getErrorMessage(error);
    } finally {
      loading = false;
    }
  }

  function chooseFiles(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    if (input.files) void uploadFiles(Array.from(input.files));
    input.value = '';
  }

  function dropFiles(event: DragEvent) {
    event.preventDefault();
    dragActive = false;
    if (event.dataTransfer?.files) void uploadFiles(Array.from(event.dataTransfer.files));
  }

  async function uploadFiles(files: File[]) {
    if (!files.length) return;
    uploading = true;
    errorMessage = '';
    try {
      for (const [index, file] of files.entries()) {
        await uploadInboxFile(file, (progress) => {
          uploadProgress = Math.round(((index + progress / 100) / files.length) * 100);
        });
      }
      await refresh();
    } catch (error) {
      errorMessage = getErrorMessage(error);
    } finally {
      uploading = false;
      uploadProgress = 0;
    }
  }

  async function retry(item: InboxItem) {
    try {
      selected = await retryInboxItem(item.id);
      await refresh(true);
    } catch (error) {
      errorMessage = getErrorMessage(error);
    }
  }

  function getErrorMessage(error: unknown): string {
    if (error instanceof ApiClientError) return error.message;
    return 'The inbox service is unavailable.';
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDate(value: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
      new Date(value)
    );
  }

  function statusLabel(status: IngestionStatus): string {
    return status.replace('_', ' ');
  }
</script>

<svelte:head>
  <title>Inbox · ThoughtHarbor</title>
  <meta name="description" content="Add and monitor private ThoughtHarbor knowledge sources." />
</svelte:head>

<main class="mx-auto min-h-screen max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
  <header class="flex items-start justify-between gap-4">
    <div>
      <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">ThoughtHarbor</p>
      <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Your private inbox.</h1>
      <p class="mt-3 max-w-xl text-slate-600">Drop in a conversation, document, or recording. ThoughtHarbor keeps the source and its processing trail together.</p>
    </div>
    <a class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink" href="/login">Account</a>
  </header>

  {#if !signedIn}
    <section class="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
      <h2 class="font-semibold">Sign in to use your inbox</h2>
      <p class="mt-1 text-sm">Your uploaded sources are protected by your local account.</p>
      <a class="mt-4 inline-flex rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white" href="/login">Open local sign-in</a>
    </section>
  {:else}
    <section
      class:!border-harbor={dragActive}
      class="mt-8 rounded-3xl border-2 border-dashed border-slate-300 bg-white p-6 text-center shadow-sm transition sm:p-10"
      aria-label="Upload files"
      ondragover={(event) => { event.preventDefault(); dragActive = true; }}
      ondragleave={() => (dragActive = false)}
      ondrop={dropFiles}
    >
      <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-50 text-harbor"><Upload size={26} /></div>
      <h2 class="mt-4 text-xl font-semibold text-ink">Add knowledge</h2>
      <p class="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-600">Choose files on mobile or drag and drop them here on desktop. Documents, transcripts, email exports, and audio are supported.</p>
      <button class="mt-5 rounded-xl bg-harbor px-5 py-3 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-wait disabled:opacity-60" disabled={uploading} onclick={() => fileInput?.click()}>
        {uploading ? `Uploading ${uploadProgress}%` : 'Choose files'}
      </button>
      <input bind:this={fileInput} class="hidden" type="file" multiple accept=".pdf,.docx,.txt,.md,.json,.xml,.csv,.eml,.msg,.mp3,.wav,.m4a,.ogg,.flac,.vtt,.srt" onchange={chooseFiles} />
      {#if uploading}
        <div class="mx-auto mt-5 h-2 max-w-sm overflow-hidden rounded-full bg-slate-100" aria-label="Upload progress"><div class="h-full rounded-full bg-harbor transition-all" style={`width: ${uploadProgress}%`}></div></div>
      {/if}
    </section>

    {#if errorMessage}
      <div class="mt-5 flex items-start justify-between gap-3 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
        <span>{errorMessage}</span><button aria-label="Dismiss error" onclick={() => (errorMessage = '')}><X size={17} /></button>
      </div>
    {/if}

    <section class="mt-10">
      <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><h2 class="text-xl font-semibold text-ink">Recent sources</h2><p class="mt-1 text-sm text-slate-500">Processing updates automatically while this page is open.</p></div>
        <div class="flex gap-2">
          <select class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700" bind:value={typeFilter} onchange={() => void refresh()} aria-label="Filter by type">
            {#each sourceTypes as option}<option value={option.value}>{option.label}</option>{/each}
          </select>
          <select class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700" bind:value={statusFilter} onchange={() => void refresh()} aria-label="Filter by status">
            {#each statuses as option}<option value={option.value}>{option.label}</option>{/each}
          </select>
        </div>
      </div>

      {#if loading}
        <p class="mt-8 text-sm text-slate-500">Loading your sources…</p>
      {:else if !items.length}
        <div class="mt-5 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500"><InboxIcon class="mx-auto text-slate-300" size={30} /><p class="mt-3">Your inbox is empty. Add your first source above.</p></div>
      {:else}
        <div class="mt-5 grid gap-3">
          {#each items as item}
            <button class="flex w-full items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-sky-200 hover:shadow-md" onclick={() => (selected = item)}>
              <div class="hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500 sm:flex">
                {#if item.source_type === 'audio'}<FileAudio size={21} />{:else if item.source_type === 'email'}<Mail size={21} />{:else}<FileText size={21} />{/if}
              </div>
              <div class="min-w-0 flex-1"><p class="truncate font-medium text-ink">{item.original_name}</p><p class="mt-1 text-xs capitalize text-slate-500">{item.source_type} · {formatBytes(item.byte_size)} · {formatDate(item.created_at)}</p></div>
              <span class:bg-red-50={item.ingestion_status === 'failed'} class:text-red-700={item.ingestion_status === 'failed'} class:bg-emerald-50={item.ingestion_status === 'ready'} class:text-emerald-700={item.ingestion_status === 'ready'} class="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold capitalize text-slate-600">{statusLabel(item.ingestion_status)}</span>
            </button>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</main>

{#if selected}
  <div class="fixed inset-0 z-10 bg-ink/30 p-4" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) selected = null; }}>
    <aside class="ml-auto h-full max-w-md overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8" aria-label="Source details">
      <div class="flex items-start justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.15em] text-harbor">Source detail</p><h2 class="mt-2 break-words text-2xl font-semibold text-ink">{selected.original_name}</h2></div><button class="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-ink" aria-label="Close detail" onclick={() => (selected = null)}><X size={20} /></button></div>
      <dl class="mt-6 grid grid-cols-2 gap-4 text-sm"><div><dt class="text-slate-500">Type</dt><dd class="mt-1 font-medium capitalize text-ink">{selected.source_type}</dd></div><div><dt class="text-slate-500">Size</dt><dd class="mt-1 font-medium text-ink">{formatBytes(selected.byte_size)}</dd></div><div class="col-span-2"><dt class="text-slate-500">Current status</dt><dd class="mt-1 font-medium capitalize text-ink">{statusLabel(selected.ingestion_status)}</dd></div></dl>
      <h3 class="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Processing timeline</h3>
      <ol class="mt-4 space-y-4 border-l border-slate-200 pl-5">{#each selected.status_timeline as event}<li class="relative"><span class="absolute -left-[25px] top-1.5 h-2.5 w-2.5 rounded-full bg-harbor"></span><p class="text-sm font-medium capitalize text-ink">{statusLabel(event.status)}</p><p class="mt-0.5 text-xs text-slate-500">{formatDate(event.at)}</p></li>{/each}</ol>
      {#if selected.ingestion_status === 'failed'}<button class="mt-8 inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white hover:bg-slate-700" onclick={() => retry(selected!)}><RefreshCw size={17} /> Retry processing</button>{/if}
      {#if selected.document_id || selected.meeting_id}<p class="mt-6 text-sm text-slate-600">Result linked to {selected.document_id ? `document #${selected.document_id}` : `meeting #${selected.meeting_id}`}.</p>{/if}
    </aside>
  </div>
{/if}
