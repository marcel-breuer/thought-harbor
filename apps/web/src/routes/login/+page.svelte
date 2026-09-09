<script lang="ts">
  import { onMount } from 'svelte';

  import { ApiClientError } from '$lib/api/errors';
  import {
    bootstrap,
    getAuthStatus,
    getCurrentUser,
    login,
    logout,
    type AuthUser
  } from '$lib/api/services/auth';

  type Mode = 'login' | 'bootstrap';

  let mode = $state<Mode>('login');
  let setupRequired = $state(false);
  let loading = $state(true);
  let submitting = $state(false);
  let errorMessage = $state('');
  let user = $state<AuthUser | null>(null);
  let identifier = $state('');
  let email = $state('');
  let username = $state('');
  let displayName = $state('');
  let password = $state('');

  onMount(async () => {
    try {
      const status = await getAuthStatus();
      setupRequired = status.setup_required;
      mode = setupRequired ? 'bootstrap' : 'login';
      if (!setupRequired) {
        try {
          user = await getCurrentUser();
        } catch {
          // An unauthenticated first visit is expected.
        }
      }
    } catch (error) {
      errorMessage = getErrorMessage(error);
    } finally {
      loading = false;
    }
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    submitting = true;
    errorMessage = '';
    try {
      const session =
        mode === 'bootstrap'
          ? await bootstrap({
              email: email || null,
              username: username || null,
              display_name: displayName || null,
              password
            })
          : await login({ identifier, password });
      user = session.user;
      password = '';
      setupRequired = false;
      mode = 'login';
    } catch (error) {
      errorMessage = getErrorMessage(error);
    } finally {
      submitting = false;
    }
  }

  async function signOut() {
    submitting = true;
    errorMessage = '';
    try {
      await logout();
      user = null;
      identifier = '';
    } catch (error) {
      errorMessage = getErrorMessage(error);
    } finally {
      submitting = false;
    }
  }

  function getErrorMessage(error: unknown): string {
    if (error instanceof ApiClientError) return error.message;
    return 'The authentication service is unavailable.';
  }
</script>

<svelte:head>
  <title>{user ? 'Account · ThoughtHarbor' : 'Sign in · ThoughtHarbor'}</title>
  <meta name="description" content="Secure local access to your ThoughtHarbor knowledge base." />
</svelte:head>

<main class="mx-auto flex min-h-screen max-w-lg items-center px-6 py-12">
  <section class="w-full rounded-3xl border border-slate-200 bg-white p-7 shadow-sm sm:p-10">
    <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">ThoughtHarbor</p>

    {#if loading}
      <p class="mt-8 text-slate-600">Checking local setup…</p>
    {:else if user}
      <div class="mt-8 space-y-5">
        <div>
          <h1 class="text-3xl font-semibold tracking-tight text-ink">Welcome back.</h1>
          <p class="mt-2 text-slate-600">Signed in as {user.email ?? user.username}.</p>
        </div>
        <button
          class="w-full rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-60"
          disabled={submitting}
          onclick={signOut}
        >
          {submitting ? 'Signing out…' : 'Sign out'}
        </button>
      </div>
    {:else}
      <div class="mt-8">
        <h1 class="text-3xl font-semibold tracking-tight text-ink">
          {mode === 'bootstrap' ? 'Create your local account.' : 'Welcome back.'}
        </h1>
        <p class="mt-2 text-slate-600">
          {mode === 'bootstrap'
            ? 'The first account becomes the local administrator. Public registration stays disabled.'
            : 'Sign in to your private knowledge base.'}
        </p>

        <form class="mt-8 space-y-4" onsubmit={submit}>
          {#if mode === 'bootstrap'}
            <label class="block text-sm font-medium text-slate-700">
              Email <span class="font-normal text-slate-400">(optional with username)</span>
              <input
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none ring-harbor focus:ring-2"
                type="email"
                bind:value={email}
                autocomplete="email"
              />
            </label>
            <label class="block text-sm font-medium text-slate-700">
              Username <span class="font-normal text-slate-400">(optional with email)</span>
              <input
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none ring-harbor focus:ring-2"
                type="text"
                minlength="3"
                maxlength="64"
                bind:value={username}
                autocomplete="username"
              />
            </label>
            <label class="block text-sm font-medium text-slate-700">
              Display name
              <input
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none ring-harbor focus:ring-2"
                type="text"
                bind:value={displayName}
                autocomplete="name"
              />
            </label>
          {:else}
            <label class="block text-sm font-medium text-slate-700">
              Email or username
              <input
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none ring-harbor focus:ring-2"
                type="text"
                required
                bind:value={identifier}
                autocomplete="username"
              />
            </label>
          {/if}

          <label class="block text-sm font-medium text-slate-700">
            Password
            <input
              class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none ring-harbor focus:ring-2"
              type="password"
              required
              minlength={mode === 'bootstrap' ? 12 : 1}
              bind:value={password}
              autocomplete={mode === 'bootstrap' ? 'new-password' : 'current-password'}
            />
          </label>

          {#if errorMessage}
            <p class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {errorMessage}
            </p>
          {/if}

          <button
            class="w-full rounded-xl bg-harbor px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:opacity-60"
            type="submit"
            disabled={submitting}
          >
            {submitting ? 'Working…' : mode === 'bootstrap' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        {#if !setupRequired}
          <button
            class="mt-5 text-sm font-medium text-slate-500 underline decoration-slate-300 underline-offset-4 hover:text-ink"
            onclick={() => {
              mode = mode === 'login' ? 'bootstrap' : 'login';
              errorMessage = '';
            }}
          >
            {mode === 'login' ? 'First run? Check bootstrap status' : 'Back to sign in'}
          </button>
        {/if}
      </div>
    {/if}
  </section>
</main>
