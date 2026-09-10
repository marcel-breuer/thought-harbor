<script lang="ts">
  import { PageHeader, StatePanel, MetadataRow, SourceProvenance, AiDerivedCard } from '$lib/components';
</script>

<svelte:head><title>Component patterns · ThoughtHarbor</title></svelte:head>

<main class="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
  <PageHeader eyebrow="Component gallery" title="Shared content patterns" description="Presentational building blocks for responsive, source-grounded ThoughtHarbor views." />
  <div class="mt-10 grid gap-6 lg:grid-cols-2">
    <section class="space-y-3"><h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">States</h2><StatePanel empty emptyTitle="An empty state" emptyDescription="Explain what the user can do next." /></section>
    <section><h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Metadata</h2><dl class="mt-3 rounded-2xl border border-slate-200 bg-white px-4"><MetadataRow label="Source type" value="Document" /><MetadataRow label="Evidence" value="Page 4" /></dl></section>
    <section><h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Original source</h2><div class="mt-3"><SourceProvenance title="Planning notes" sourceType="document" text="The original excerpt remains visibly distinct from derived knowledge." location="document · page 4" /></div></section>
    <section><h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Derived knowledge</h2><div class="mt-3"><AiDerivedCard title="Potential next step" content="Review the open decision before the next planning session." /></div></section>
  </div>
</main>
