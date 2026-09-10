<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import '../app.css';
  import { getCurrentUser } from '$lib/api/services/auth';
  import AppShell from '$lib/components/app-shell.svelte';

  let { children } = $props();
  let authenticated = $state(false);
  let authChecked = $state(false);
  let activeRedirect = $state(false);
  let isLoginRoute = $derived(page.url.pathname === '/login');

  function currentLocation(): string {
    return `${page.url.pathname}${page.url.search}${page.url.hash}`;
  }

  function redirectToLogin() {
    if (isLoginRoute || activeRedirect) return;
    activeRedirect = true;
    authenticated = false;
    authChecked = true;
    const redirect = encodeURIComponent(currentLocation());
    void goto(`/login?redirect=${redirect}`, { replaceState: true });
  }

  onMount(() => {
    const handleAuthExpired = () => redirectToLogin();
    window.addEventListener('thought-harbor:auth-expired', handleAuthExpired);

    if (isLoginRoute) {
      authChecked = true;
    } else {
      void getCurrentUser()
        .then(() => {
          authenticated = true;
          authChecked = true;
        })
        .catch(() => redirectToLogin());
    }

    return () => window.removeEventListener('thought-harbor:auth-expired', handleAuthExpired);
  });
</script>

{#if isLoginRoute}
  {@render children()}
{:else if authenticated && authChecked}
  <AppShell>
    {@render children()}
  </AppShell>
{:else if !authChecked}
  <main class="flex min-h-screen items-center justify-center bg-white px-6 text-sm text-slate-600">
    Checking your session…
  </main>
{/if}
