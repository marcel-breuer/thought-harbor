<script lang="ts">
  import { onMount } from 'svelte';

  import { ApiClientError } from '$lib/api/errors';
  import { getDiagnostics, type ReadinessResponse } from '$lib/api/services/system';
  import { createApiToken, listApiTokens, revokeApiToken, type ApiToken } from '$lib/api/services/tokens';

  let diagnostics = $state<ReadinessResponse | null>(null);
  let loading = $state(true);
  let errorMessage = $state('');
  let tokens = $state<ApiToken[]>([]);
  let tokenName = $state('');
  let tokenScopes = $state<string[]>(['knowledge:read']);
  let newToken = $state('');

  const scopeOptions = [
    ['knowledge:read', 'Read knowledge'],
    ['knowledge:write', 'Resolve clarifications'],
    ['tasks:write', 'Update tasks'],
    ['uploads:write', 'Create uploads'],
  ] as const;

  onMount(() => {
    void loadDiagnostics();
    void loadTokens();
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

  async function loadTokens() {
    try { tokens = await listApiTokens(); } catch { /* diagnostics handles unauthenticated state */ }
  }

  async function createToken() {
    if (!tokenName.trim()) return;
    try {
      const created = await createApiToken({ name: tokenName.trim(), scopes: tokenScopes, expires_at: null });
      newToken = created.token ?? '';
      tokenName = '';
      tokenScopes = ['knowledge:read'];
      await loadTokens();
    } catch (error) {
      errorMessage = error instanceof ApiClientError ? error.message : 'Token creation failed.';
    }
  }

  async function revokeToken(id: number) {
    try { await revokeApiToken(id); await loadTokens(); } catch { errorMessage = 'Token revocation failed.'; }
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
  <section class="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7" aria-labelledby="tokens-heading"><h2 id="tokens-heading" class="text-lg font-semibold text-ink">Integration tokens</h2><p class="mt-1 text-sm text-slate-500">Create a scoped token for a local assistant. Plaintext is shown once and stored hashed.</p><form class="mt-5" onsubmit={(event) => { event.preventDefault(); void createToken(); }}><div class="flex flex-col gap-2 sm:flex-row"><label class="sr-only" for="token-name">Token name</label><input id="token-name" bind:value={tokenName} class="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="e.g. Local assistant" /><button class="rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50" disabled={!tokenName.trim() || tokenScopes.length === 0}>Create token</button></div><fieldset class="mt-4"><legend class="text-xs font-semibold uppercase tracking-wide text-slate-500">Permissions</legend><div class="mt-2 grid gap-2 sm:grid-cols-2">{#each scopeOptions as [scope, label]}<label class="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" value={scope} bind:group={tokenScopes} />{label}</label>{/each}</div></fieldset></form>{#if newToken}<div class="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900"><p class="font-semibold">Copy this token now; it will not be shown again.</p><code class="mt-2 block break-all text-xs">{newToken}</code><button class="mt-2 text-xs font-semibold underline" onclick={() => (newToken = '')}>Dismiss</button></div>{/if}{#if tokens.length}<ul class="mt-5 divide-y divide-slate-100">{#each tokens as token}<li class="flex items-center justify-between gap-4 py-3"><span><span class="block text-sm font-medium text-ink">{token.name}</span><span class="text-xs text-slate-500">{token.token_prefix} · {token.scopes.join(', ')}</span></span><button class="text-xs font-semibold text-red-600 hover:text-red-800" onclick={() => void revokeToken(token.id)}>Revoke</button></li>{/each}</ul>{:else}<p class="mt-5 text-sm text-slate-500">No integration tokens created.</p>{/if}</section>
</main>
