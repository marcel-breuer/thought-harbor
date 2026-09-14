<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils.js';

	let { class: className, children, ...restProps }: HTMLAttributes<HTMLHeadingElement> & { children?: Snippet } = $props();
</script>

<h5 class={cn('mb-1 font-medium leading-none tracking-tight', className)} {...restProps}>{@render children?.()}</h5>
