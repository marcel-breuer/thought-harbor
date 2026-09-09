<svelte:head>
  <title>ThoughtHarbor</title>
  <meta
    name="description"
    content="A self-hosted, mobile-first second brain for your knowledge."
  />
</svelte:head>

<main class="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-6 py-16">
  <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">ThoughtHarbor</p>
  <h1 class="max-w-2xl text-4xl font-semibold tracking-tight text-ink sm:text-6xl">
    Your knowledge, privately yours.
  </h1>
  <p class="max-w-xl text-lg leading-8 text-slate-600">
    The SvelteKit workspace is ready for the self-hosted knowledge experience.
  </p>
  <div class="flex flex-wrap gap-3 text-sm text-slate-600">
    <span class="rounded-full border border-slate-200 bg-white px-3 py-1.5">SvelteKit</span>
    <span class="rounded-full border border-slate-200 bg-white px-3 py-1.5">TypeScript</span>
    <span class="rounded-full border border-slate-200 bg-white px-3 py-1.5">Tailwind CSS</span>
  </div>
  <a
    class="w-fit rounded-xl bg-harbor px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600"
    href="/login"
  >
    Open local sign-in
  </a>
</main>
