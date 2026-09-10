<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowLeft, LoaderCircle, Mic2 } from '@lucide/svelte';
  import { page } from '$app/state';
  import { getMeeting, type MeetingDetail } from '$lib/api/services/knowledge';

  let meeting = $state<MeetingDetail | null>(null);
  let loading = $state(true);
  let error = $state('');
  const meetingId = $derived(Number(page.params.meeting_id));

  onMount(() => {
    void load();
  });

  async function load() {
    try {
      meeting = await getMeeting(meetingId);
    } catch {
      error = 'This meeting is unavailable.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>{meeting?.title ?? 'Meeting'} · ThoughtHarbor</title></svelte:head>

<main class="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
  <a class="inline-flex items-center gap-2 text-sm font-medium text-harbor hover:text-sky-700" href="/"><ArrowLeft size={16} /> Back to dashboard</a>
  {#if loading}<LoaderCircle class="mt-10 animate-spin text-harbor" size={24} />{:else if error}<p class="mt-8 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>{:else if meeting}<header class="mt-8"><p class="text-sm font-semibold uppercase tracking-[0.2em] text-harbor">Source meeting</p><h1 class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">{meeting.title}</h1><p class="mt-3 text-sm text-slate-500">{meeting.segments.length} transcript segment{meeting.segments.length === 1 ? '' : 's'}</p></header><section class="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div class="flex items-center gap-2 text-sm font-semibold text-slate-500"><Mic2 size={17} /> Transcript</div>{#if meeting.segments.length}<ol class="mt-5 space-y-5">{#each meeting.segments as segment}<li class="border-l-2 border-sky-100 pl-4"><p class="text-xs font-semibold text-harbor">{segment.speaker_name || segment.speaker_label || `Speaker ${segment.sequence + 1}`}</p><p class="mt-1 text-sm leading-7 text-slate-700">{segment.text}</p></li>{/each}</ol>{:else}<p class="mt-5 text-sm text-slate-500">No transcript is available yet.</p>{/if}</section>{/if}
</main>
