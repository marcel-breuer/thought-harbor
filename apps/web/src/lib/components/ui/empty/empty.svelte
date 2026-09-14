<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils.js';

	let { class: className, children, ...restProps }: HTMLAttributes<HTMLDivElement> & { children?: Snippet } = $props();
</script>

<div class={cn('flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-muted/40 p-8 text-center', className)} {...restProps}>
	{@render children?.()}
</div>
