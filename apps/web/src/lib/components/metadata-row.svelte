<script lang="ts">
  let { label, value } = $props<{ label: string; value: string }>();
</script>

<div class="flex items-baseline justify-between gap-4 border-b border-slate-100 py-3 last:border-0"><dt class="text-sm text-slate-500">{label}</dt><dd class="text-right text-sm font-medium text-ink">{value}</dd></div>
