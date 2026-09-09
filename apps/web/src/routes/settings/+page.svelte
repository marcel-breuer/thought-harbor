<script lang="ts">
  import { onMount } from 'svelte';

  import { ApiClientError } from '$lib/api/errors';
  import { getDiagnostics, type ReadinessResponse } from '$lib/api/services/system';

  let diagnostics = $state<ReadinessResponse | null>(null);
  let loading = $state(true);
  let errorMessage = $state('');

  onMount(() => {
    void loadDiagnostics();
  });

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
</script>

<svelte:head>
  <title>Diagnostics · ThoughtHarbor</title>
  <meta name="description" content="Local ThoughtHarbor service diagnostics." />
</svelte:head>

<main class="mx-auto min-h-screen max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="text-sm font-medium text-harbor hover:text-sky-700" href="/">← Back to inbox</a>
  <header class="mt-8">
    <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">ThoughtHarbor</p>
    <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">Local diagnostics.</h1>
    <p class="mt-3 max-w-xl text-slate-600">Check the local services used by the API and background worker. No document content or credentials are shown.</p>
  </header>

  {#if loading}
    <p class="mt-10 text-sm text-slate-500">Checking local services…</p>
  {:else if errorMessage}
    <section class="mt-10 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700" role="alert">{errorMessage}</section>
  {:else if diagnostics}
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

  <button class="mt-5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-ink" onclick={() => void loadDiagnostics()}>Refresh checks</button>
</main>
