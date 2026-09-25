<script lang="ts">
  import { onMount } from 'svelte';
  import { ApiClientError } from '$lib/api/errors';
  import { getOpenRouterModels, type OpenRouterModelList } from '$lib/api/services/ai';
  import {
    getCurrentUser,
    updatePreferredAIModel,
    type AuthUser,
  } from '$lib/api/services/auth';
  import { PageHeader } from '$lib/components';

  let profile = $state<AuthUser | null>(null);
  let catalogue = $state<OpenRouterModelList | null>(null);
  let selectedModel = $state('');
  let search = $state('');
  let loading = $state(true);
  let saving = $state(false);
  let errorMessage = $state('');
  let successMessage = $state('');

  let filteredModels = $derived(
    (catalogue?.models ?? [])
      .filter((model) => `${model.name} ${model.id}`.toLowerCase().includes(search.trim().toLowerCase()))
      .sort((left, right) => left.name.localeCompare(right.name)),
  );
  let preferredModel = $derived(profile?.preferred_ai_model);
  let selectedModelDetails = $derived(
    catalogue?.models.find((model) => model.id === selectedModel),
  );
  let currentModelAvailable = $derived(
    Boolean(preferredModel && catalogue?.models.some((model) => model.id === preferredModel)),
  );
  let effectiveModel = $derived(
    currentModelAvailable ? profile?.preferred_ai_model ?? '' : catalogue?.default_model ?? '',
  );

  onMount(() => {
    void loadProfileAndModels();
  });

  async function loadProfileAndModels() {
    loading = true;
    errorMessage = '';
    successMessage = '';
    const [profileResult, catalogueResult] = await Promise.allSettled([
      getCurrentUser(),
      getOpenRouterModels(),
    ]);
    if (profileResult.status === 'fulfilled') {
      profile = profileResult.value;
    } else {
      errorMessage = message(profileResult.reason, 'Your profile could not be loaded.');
    }
    if (catalogueResult.status === 'fulfilled') {
      catalogue = catalogueResult.value;
      const saved = profileResult.status === 'fulfilled' ? profileResult.value.preferred_ai_model : null;
      selectedModel = catalogueResult.value.models.some((model) => model.id === saved)
        ? saved ?? catalogueResult.value.default_model
        : catalogueResult.value.default_model;
    } else if (!errorMessage) {
      errorMessage = message(
        catalogueResult.reason,
        'OpenRouter models are unavailable. Check the deployment settings and try again.',
      );
    }
    loading = false;
  }

  async function saveModel(model: string | null) {
    if (saving) return;
    saving = true;
    errorMessage = '';
    successMessage = '';
    try {
      profile = await updatePreferredAIModel(model);
      selectedModel = model ?? catalogue?.default_model ?? '';
      successMessage = model
        ? 'Your preferred model has been saved.'
        : 'Your profile now uses the deployment default model.';
    } catch (error) {
      errorMessage = message(error, 'Your model preference could not be saved.');
    } finally {
      saving = false;
    }
  }

  function message(error: unknown, fallback: string): string {
    return error instanceof ApiClientError ? error.message : fallback;
  }

  function pricePerMillion(value: number | null): string {
    if (value === null) return 'Pricing unavailable';
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'USD',
      maximumSignificantDigits: 4,
    }).format(value * 1_000_000);
  }
</script>

<svelte:head>
  <title>Profile · ThoughtHarbor</title>
  <meta name="description" content="Choose the AI model used for your ThoughtHarbor conversations and knowledge extraction." />
</svelte:head>

<main class="mx-auto min-h-screen max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="text-sm font-medium text-harbor hover:text-sky-700" href="/">← Back to inbox</a>
  <div class="mt-8">
    <PageHeader eyebrow="Personal profile" title="Choose your AI model." description="Your selection is used for chat and structured knowledge generation across your account." />
  </div>

  <section class="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950" aria-label="AI data handling">
    <h2 class="font-semibold">Your sources are processed by an external model provider</h2>
    <p class="mt-1">Prompts and selected source content are sent to OpenRouter and handled by the provider behind your chosen model. Your deployment operator supplies the OpenRouter API key; it is never stored in your profile or sent to your browser.</p>
  </section>

  {#if loading}
    <p class="mt-8 text-sm text-slate-500" role="status">Loading your profile and supported models…</p>
  {:else}
    {#if errorMessage}
      <section class="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert">{errorMessage}</section>
    {/if}
    {#if successMessage}
      <p class="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800" role="status">{successMessage}</p>
    {/if}

    {#if catalogue && profile}
      <section class="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7" aria-labelledby="model-heading">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 id="model-heading" class="text-lg font-semibold text-ink">Generation model</h2>
            <p class="mt-1 text-sm leading-6 text-slate-500">Choose a model for chat and extraction. The embedding model is shared by search and is managed by the deployment operator.</p>
          </div>
          <span class="shrink-0 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">OpenRouter</span>
        </div>

        {#if profile.preferred_ai_model && !currentModelAvailable}
          <p class="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
            Your saved model ({profile.preferred_ai_model}) is no longer available. New requests use the deployment default until you choose an available model.
          </p>
        {/if}

        <div class="mt-6 rounded-2xl bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Currently used</p>
          <p class="mt-1 break-all font-medium text-ink">{effectiveModel || 'Unavailable'}</p>
          <p class="mt-1 text-xs text-slate-500">{profile.preferred_ai_model && currentModelAvailable ? 'Saved in your profile' : 'Deployment default'}</p>
        </div>

        <label class="mt-6 block text-sm font-semibold text-ink" for="model-search">Find a model</label>
        <input
          id="model-search"
          type="search"
          bind:value={search}
          placeholder="Search by model name or ID"
          class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100"
          autocomplete="off"
        />

        <label class="mt-4 block text-sm font-semibold text-ink" for="model-select">Available models</label>
        {#if filteredModels.length}
          <select
            id="model-select"
            bind:value={selectedModel}
            size="8"
            class="mt-2 w-full rounded-xl border border-slate-200 bg-white text-sm outline-none focus:border-harbor focus:ring-2 focus:ring-sky-100"
          >
            {#each filteredModels as model (model.id)}
              <option value={model.id} class="px-3 py-2.5">{model.name} · {model.id}</option>
            {/each}
          </select>
          <p class="mt-2 text-xs text-slate-500">{filteredModels.length} models support chat and structured output.</p>
        {:else}
          <p class="mt-2 rounded-xl border border-slate-200 p-4 text-sm text-slate-500" role="status">No supported models match that search.</p>
        {/if}

        {#if selectedModelDetails}
          <dl class="mt-4 grid gap-3 rounded-2xl border border-slate-100 p-4 text-sm sm:grid-cols-3">
            <div><dt class="text-xs font-semibold uppercase tracking-wide text-slate-500">Context</dt><dd class="mt-1 text-ink">{selectedModelDetails.context_length ? `${selectedModelDetails.context_length.toLocaleString()} tokens` : 'Not reported'}</dd></div>
            <div><dt class="text-xs font-semibold uppercase tracking-wide text-slate-500">Input price</dt><dd class="mt-1 text-ink">{pricePerMillion(selectedModelDetails.prompt_price)} / 1M tokens</dd></div>
            <div><dt class="text-xs font-semibold uppercase tracking-wide text-slate-500">Output price</dt><dd class="mt-1 text-ink">{pricePerMillion(selectedModelDetails.completion_price)} / 1M tokens</dd></div>
          </dl>
        {/if}

        <div class="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            class="rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={saving || !selectedModel || !catalogue.models.some((model) => model.id === selectedModel) || selectedModel === profile.preferred_ai_model}
            onclick={() => void saveModel(selectedModel)}
          >
            {saving ? 'Saving…' : 'Save model preference'}
          </button>
          <button
            type="button"
            class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={saving || !profile.preferred_ai_model}
            onclick={() => void saveModel(null)}
          >
            Use deployment default
          </button>
        </div>
      </section>
    {/if}
  {/if}
</main>
