<script lang="ts">
  let { title, sourceType, text, location = 'Source context' } = $props<{
    title: string;
    sourceType: string;
    text: string;
    location?: string;
  }>();
</script>

<article class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div class="flex flex-wrap items-center justify-between gap-2"><p class="text-sm font-semibold text-ink">{title}</p><span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-500">{sourceType}</span></div><p class="mt-3 border-l-2 border-sky-200 pl-3 text-sm leading-6 text-slate-600">{text}</p><p class="mt-3 text-xs text-slate-400">{location}</p></article>
