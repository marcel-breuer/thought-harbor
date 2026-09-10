<script lang="ts">
  let { eyebrow, title, description, children } = $props<{
    eyebrow: string;
    title: string;
    description?: string;
    children?: import('svelte').Snippet;
  }>();
</script>

<header class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
  <div>
    <p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">{eyebrow}</p>
    <h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">{title}</h1>
    {#if description}<p class="mt-3 max-w-2xl text-slate-600">{description}</p>{/if}
  </div>
  {#if children}<div class="shrink-0">{@render children()}</div>{/if}
</header>
