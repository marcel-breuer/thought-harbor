<script lang="ts">
  import { Sparkles } from '@lucide/svelte';

  let { title, content, kind = 'AI-derived knowledge', children } = $props<{
    title: string;
    content: string;
    kind?: string;
    children?: import('svelte').Snippet;
  }>();
</script>

<article class="rounded-2xl border border-violet-200 bg-violet-50/70 p-4"><div class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-700"><Sparkles size={15} /> {kind}</div><h3 class="mt-2 font-semibold text-ink">{title}</h3><p class="mt-2 text-sm leading-6 text-slate-700">{content}</p>{#if children}<div class="mt-3">{@render children()}</div>{/if}</article>
