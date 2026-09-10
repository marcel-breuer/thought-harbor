<script lang="ts">
  import { onMount } from 'svelte';

  import { ApiClientError } from '$lib/api/errors';
  import { PageHeader } from '$lib/components';
  import { getDiagnostics, getRuntimeSettings, type ReadinessResponse, type RuntimeSettings } from '$lib/api/services/system';

  let diagnostics = $state<ReadinessResponse | null>(null);
  let loading = $state(true);
  let errorMessage = $state('');
  let runtimeSettings = $state<RuntimeSettings | null>(null);

  onMount(() => {
    void loadSettings();
  });

  async function loadSettings() {
    await Promise.all([loadDiagnostics(), loadRuntimeSettings()]);
  }

  async function loadDiagnostics() {
    loading = true;
    errorMessage = '';
    try {
      diagnostics = await getDiagnostics();
    } catch (error) {
      errorMessage = error instanceof ApiClientError ? error.message : 'Diagnostics are unavailable.';
    } finally {
      loading = false;
    }
  }

  async function loadRuntimeSettings() {
    try {
      runtimeSettings = await getRuntimeSettings();
    } catch (error) {
      if (!errorMessage) errorMessage = error instanceof ApiClientError ? error.message : 'Configuration is unavailable.';
    }
  }
</script>

<svelte:head>
  <title>Diagnostics · ThoughtHarbor</title>
  <meta name="description" content="Local ThoughtHarbor service diagnostics." />
</svelte:head>

<main class="mx-auto min-h-screen max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="text-sm font-medium text-harbor hover:text-sky-700" href="/">← Back to inbox</a>
  <div class="mt-8"><PageHeader eyebrow="System settings" title="Local configuration." description="Review the active providers, models, processing limits, and service health. Secrets stay server-side and are never returned." /></div>

  {#if loading}
    <p class="mt-10 text-sm text-slate-500">Checking local services…</p>
  {:else}
    {#if errorMessage}<section class="mt-8 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700" role="alert">{errorMessage}</section>{/if}
    {#if runtimeSettings}
      <section class="mt-8 grid gap-4 sm:grid-cols-2" aria-label="Runtime configuration">
        <article class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><h2 class="text-lg font-semibold text-ink">AI capabilities</h2><dl class="mt-4"><div class="flex justify-between gap-4 border-b border-slate-100 py-3 text-sm"><dt class="text-slate-500">Chat</dt><dd class="font-medium text-ink">{runtimeSettings.chat_provider} · {runtimeSettings.chat_model}</dd></div><div class="flex justify-between gap-4 border-b border-slate-100 py-3 text-sm"><dt class="text-slate-500">Extraction</dt><dd class="font-medium text-ink">{runtimeSettings.extraction_provider} · {runtimeSettings.extraction_model}</dd></div><div class="flex justify-between gap-4 py-3 text-sm"><dt class="text-slate-500">Embeddings</dt><dd class="font-medium text-ink">{runtimeSettings.embeddings_provider} · {runtimeSettings.embeddings_model}</dd></div></dl>{#if runtimeSettings.external_provider_enabled}<p class="mt-4 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">An external provider is enabled. Source content may leave this installation.</p>{:else}<p class="mt-4 rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">All configured AI providers are local Ollama adapters.</p>{/if}</article>
        <article class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><h2 class="text-lg font-semibold text-ink">Processing</h2><dl class="mt-4"><div class="flex justify-between gap-4 border-b border-slate-100 py-3 text-sm"><dt class="text-slate-500">Transcription</dt><dd class="font-medium capitalize text-ink">{runtimeSettings.transcription_model} · {runtimeSettings.transcription_device}</dd></div><div class="flex justify-between gap-4 border-b border-slate-100 py-3 text-sm"><dt class="text-slate-500">Compute type</dt><dd class="font-medium text-ink">{runtimeSettings.transcription_compute_type}</dd></div><div class="flex justify-between gap-4 border-b border-slate-100 py-3 text-sm"><dt class="text-slate-500">Diarization</dt><dd class="font-medium text-ink">{runtimeSettings.diarization_enabled ? `${runtimeSettings.diarization_provider} · enabled` : 'Disabled'}</dd></div><div class="flex justify-between gap-4 py-3 text-sm"><dt class="text-slate-500">Upload limit</dt><dd class="font-medium text-ink">{Math.round(runtimeSettings.max_upload_bytes / 1024 / 1024)} MB</dd></div></dl></article>
      </section>
    {/if}
  {#if diagnostics}
    <section class="mt-10 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-lg font-semibold text-ink">Service status</h2>
        <span class:!bg-emerald-50={diagnostics.status === 'ok'} class:!text-emerald-700={diagnostics.status === 'ok'} class="rounded-full bg-red-50 px-3 py-1.5 text-xs font-semibold capitalize text-red-700">{diagnostics.status}</span>
      </div>
      <div class="mt-5 grid gap-3">
        {#each diagnostics.checks as check}
          <div class="flex items-start justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
            <div><p class="font-medium capitalize text-ink">{check.name}</p><p class="mt-1 text-sm text-slate-500">{check.detail}</p></div>
            <span class:text-emerald-700={check.status === 'ok'} class:text-red-700={check.status !== 'ok'} class="text-sm font-semibold capitalize">{check.status}</span>
          </div>
        {/each}
      </div>
    </section>
  {/if}
  {/if}

  <button class="mt-5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-ink" onclick={() => void loadSettings()}>Refresh settings</button>
</main>
