<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowLeft, FileText, LoaderCircle } from '@lucide/svelte';
  import { page } from '$app/state';
  import { getDocument, type DocumentDetail } from '$lib/api/services/knowledge';

  let document = $state<DocumentDetail | null>(null);
  let loading = $state(true);
  let error = $state('');
  const documentId = $derived(Number(page.params.document_id));

  onMount(() => {
    void load();
  });

  async function load() {
    try {
      document = await getDocument(documentId);
    } catch {
      error = 'This document is unavailable.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>{document?.title ?? 'Document'} · ThoughtHarbor</title></svelte:head>

<main class="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="inline-flex items-center gap-2 text-sm font-medium text-harbor hover:text-sky-700" href="/"><ArrowLeft size={16} /> Back to dashboard</a>
  {#if loading}<LoaderCircle class="mt-10 animate-spin text-harbor" size={24} />{:else if error}<p class="mt-8 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{:else if document}<header class="mt-8"><p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Source document</p><h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">{document.title}</h1><p class="mt-3 text-sm text-slate-500">{document.original_name} · {document.chunks.length} evidence chunk{document.chunks.length === 1 ? '' : 's'}</p></header><article class="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div class="flex items-center gap-2 text-sm font-semibold text-slate-500"><FileText size={17} /> Original content</div><p class="mt-5 whitespace-pre-wrap text-sm leading-7 text-slate-700">{document.extracted_text || 'No extracted text is available yet.'}</p></article>{/if}
</main>
