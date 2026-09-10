<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import {
    Brain,
    CalendarDays,
    ClipboardCheck,
    FileText,
    House,
    Inbox,
    LoaderCircle,
    ListChecks,
    LogOut,
    Menu,
    Search,
    Settings,
    X
  } from '@lucide/svelte';
  import { ApiClientError } from '$lib/api/errors';
  import { getCurrentUser, logout, type AuthUser } from '$lib/api/services/auth';

  let { children } = $props();

  const navigation = [
    { label: 'Dashboard', href: '/', icon: House },
    { label: 'Inbox', href: '/inbox', icon: Inbox },
    { label: 'Knowledge', href: '/knowledge', icon: Brain },
    { label: 'Meetings', href: '/meetings', icon: CalendarDays },
    { label: 'Documents', href: '/documents', icon: FileText },
    { label: 'Chat', href: '/chat', icon: Search },
    { label: 'Tasks', href: '/tasks', icon: ListChecks },
    { label: 'Settings', href: '/settings', icon: Settings }
  ];

  let commandOpen = $state(false);
  let mobileMenuOpen = $state(false);
  let commandQuery = $state('');
  let commandInput = $state<HTMLInputElement>();
  let currentUser = $state<AuthUser | null>(null);
  let accountLoading = $state(true);
  let signingOut = $state(false);
  let accountError = $state('');
  let activePath = $derived(page.url.pathname);
  let filteredNavigation = $derived(
    navigation.filter((item) => item.label.toLowerCase().includes(commandQuery.trim().toLowerCase()))
  );

  onMount(() => {
    void loadCurrentUser();
    const handleKeydown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        openCommandPalette();
      }
      if (event.key === 'Escape') {
        commandOpen = false;
        mobileMenuOpen = false;
      }
    };
    const handleOpen = () => openCommandPalette();
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('thought-harbor:open-command', handleOpen);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('thought-harbor:open-command', handleOpen);
    };
  });

  async function loadCurrentUser() {
    try {
      currentUser = await getCurrentUser();
    } catch (error) {
      accountError = error instanceof ApiClientError ? error.message : 'Account unavailable.';
    } finally {
      accountLoading = false;
    }
  }

  async function signOut() {
    if (signingOut) return;
    signingOut = true;
    accountError = '';
    try {
      await logout();
      currentUser = null;
      await goto('/login');
    } catch (error) {
      accountError = error instanceof ApiClientError ? error.message : 'Sign out failed.';
    } finally {
      signingOut = false;
    }
  }

  function userName(user: AuthUser): string {
    return user.display_name ?? user.username ?? user.email ?? 'Local user';
  }

  function userInitial(user: AuthUser): string {
    return userName(user).slice(0, 1).toUpperCase();
  }

  $effect(() => {
    if (commandOpen) commandInput?.focus();
  });

  function openCommandPalette() {
    commandOpen = true;
    commandQuery = '';
  }

  async function navigate(href: string) {
    commandOpen = false;
    mobileMenuOpen = false;
    await goto(href);
  }

  function isActive(href: string, label: string): boolean {
    if (label === 'Dashboard') return activePath === '/';
    return activePath === href || activePath.startsWith(`${href}/`);
  }
</script>

<div class="min-h-screen bg-[#0b1020] text-ink">
  <aside class="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-[#0f1728] px-5 py-7 lg:flex lg:flex-col">
    <a class="flex items-center gap-2 px-2 text-lg font-semibold tracking-tight text-ink" href="/">
      <span class="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50 p-1"><img src="/brand/thought-harbor-mark.png" alt="" class="h-full w-full object-contain" /></span>
      ThoughtHarbor
    </a>

    <nav class="mt-12 space-y-1.5" aria-label="Primary navigation">
      {#each navigation as item}
        <a
          class:bg-sky-50={isActive(item.href, item.label)}
          class:text-harbor={isActive(item.href, item.label)}
          class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-ink"
          href={item.href}
        >
          <item.icon size={17} strokeWidth={1.8} />
          {item.label}
        </a>
      {/each}
    </nav>

    <div class="mt-auto rounded-2xl border border-slate-200 p-3">
      {#if accountLoading}
        <div class="flex items-center gap-2 text-xs text-slate-500" role="status"><LoaderCircle class="animate-spin" size={15} /> Loading account…</div>
      {:else if currentUser}
        <div class="flex items-center gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sm font-semibold text-harbor" aria-hidden="true">{userInitial(currentUser)}</span>
          <div class="min-w-0"><p class="truncate text-sm font-semibold text-ink">{userName(currentUser)}</p><p class="truncate text-xs text-slate-500">Private workspace</p></div>
        </div>
        <button class="mt-3 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs font-semibold text-slate-500 transition hover:bg-slate-50 hover:text-ink disabled:opacity-60" type="button" onclick={() => void signOut()} disabled={signingOut} aria-label="Log out">{#if signingOut}<LoaderCircle class="animate-spin" size={15} />{:else}<LogOut size={15} />{/if}{signingOut ? 'Signing out…' : 'Log out'}</button>
      {:else}
        <a class="text-xs font-semibold text-harbor hover:text-sky-700" href="/login">Sign in</a>
      {/if}
      {#if accountError}<p class="mt-2 text-xs text-red-600" role="alert">{accountError}</p>{/if}
    </div>
  </aside>

  <div class="lg:pl-64">
    <header class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-100 bg-white/95 px-5 backdrop-blur sm:px-8">
      <div class="flex items-center gap-3 lg:hidden">
        <button class="rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label="Open navigation" onclick={() => (mobileMenuOpen = true)}><Menu size={20} /></button>
        <a class="flex items-center gap-2 font-semibold tracking-tight text-ink" href="/"><span class="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-50 p-1"><img src="/brand/thought-harbor-mark.png" alt="" class="h-full w-full object-contain" /></span>ThoughtHarbor</a>
      </div>
      <button class="hidden max-w-md flex-1 items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-left text-sm text-slate-400 transition hover:border-slate-300 hover:text-slate-600 sm:flex lg:max-w-lg" onclick={openCommandPalette} aria-label="Open command palette">
        <Search size={16} /><span class="truncate">Search anything…</span><kbd class="ml-auto hidden rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 md:inline">⌘ K</kbd>
      </button>
      <button class="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-ink sm:hidden" onclick={openCommandPalette} aria-label="Open search"><Search size={17} /><span>Search</span></button>
      <a class="hidden rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink sm:block" href="/login">Account</a>
    </header>

    {@render children()}
  </div>
</div>

{#if mobileMenuOpen}
  <div class="fixed inset-0 z-40 bg-ink/30 lg:hidden" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) mobileMenuOpen = false; }}>
    <aside class="h-full w-[min(86vw,21rem)] overflow-y-auto bg-white p-5 shadow-2xl" aria-label="Mobile navigation">
      <div class="flex items-center justify-between"><a class="flex items-center gap-2 font-semibold tracking-tight text-ink" href="/"><span class="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50 p-1"><img src="/brand/thought-harbor-mark.png" alt="" class="h-full w-full object-contain" /></span>ThoughtHarbor</a><button class="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Close navigation" onclick={() => (mobileMenuOpen = false)}><X size={20} /></button></div>
      <nav class="mt-8 space-y-1.5" aria-label="Mobile primary navigation">
        {#each navigation as item}
          <a class:bg-sky-50={isActive(item.href, item.label)} class:text-harbor={isActive(item.href, item.label)} class="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-ink" href={item.href} onclick={() => (mobileMenuOpen = false)}><item.icon size={18} strokeWidth={1.8} />{item.label}</a>
        {/each}
      </nav>
      <div class="mt-8 border-t border-slate-100 pt-6">
        {#if accountLoading}
          <div class="flex items-center gap-2 text-xs text-slate-500" role="status"><LoaderCircle class="animate-spin" size={15} /> Loading account…</div>
        {:else if currentUser}
          <div class="flex items-center gap-3"><span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sm font-semibold text-harbor" aria-hidden="true">{userInitial(currentUser)}</span><div class="min-w-0"><p class="truncate text-sm font-semibold text-ink">{userName(currentUser)}</p><p class="truncate text-xs text-slate-500">Private workspace</p></div></div>
          <button class="mt-3 flex w-full items-center gap-3 rounded-xl border border-slate-200 px-3 py-3 text-left text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink disabled:opacity-60" type="button" onclick={() => void signOut()} disabled={signingOut} aria-label="Log out">{#if signingOut}<LoaderCircle class="animate-spin" size={18} />{:else}<LogOut size={18} />{/if}{signingOut ? 'Signing out…' : 'Log out'}</button>
        {:else}
          <a class="text-sm font-semibold text-harbor hover:text-sky-700" href="/login">Sign in</a>
        {/if}
        {#if accountError}<p class="mt-2 text-xs text-red-600" role="alert">{accountError}</p>{/if}
      </div>
      <button class="mt-8 flex w-full items-center gap-3 rounded-xl border border-slate-200 px-3 py-3 text-left text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-ink" onclick={openCommandPalette}><Search size={18} />Open command palette</button>
    </aside>
  </div>
{/if}

{#if commandOpen}
  <div class="fixed inset-0 z-50 flex items-start justify-center bg-ink/30 p-4 pt-[12vh]" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) commandOpen = false; }}>
    <dialog open class="w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" aria-modal="true" aria-label="Command palette">
      <div class="flex items-center gap-3 border-b border-slate-200 px-4"><Search class="text-slate-400" size={19} /><input bind:this={commandInput} bind:value={commandQuery} class="min-w-0 flex-1 border-0 py-4 text-base text-ink outline-none placeholder:text-slate-400" placeholder="Jump to a view or search…" aria-label="Command search" /><kbd class="rounded bg-slate-100 px-2 py-1 text-xs text-slate-500">Esc</kbd></div>
      <div class="max-h-[min(60vh,24rem)] overflow-y-auto p-2">
        {#if filteredNavigation.length}
          <p class="px-3 pb-2 pt-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Navigate</p>
          {#each filteredNavigation as item}
            <button class="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-medium text-slate-700 transition hover:bg-sky-50 hover:text-harbor" onclick={() => void navigate(item.href)}><item.icon size={18} strokeWidth={1.8} /><span>{item.label}</span><span class="ml-auto text-xs text-slate-400">Open</span></button>
          {/each}
        {:else}
          <button class="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-medium text-slate-700 hover:bg-sky-50 hover:text-harbor" onclick={() => void navigate('/chat')}><Search size={18} /><span>Search your knowledge</span><span class="ml-auto text-xs text-slate-400">Chat / Search</span></button>
        {/if}
      </div>
      <div class="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-400"><span>Use ↑ ↓ to navigate</span><span>Enter to open</span></div>
    </dialog>
  </div>
{/if}
