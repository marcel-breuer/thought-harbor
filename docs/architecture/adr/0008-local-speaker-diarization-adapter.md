# ADR-0008: Optional local pyannote speaker diarization adapter

- Status: Accepted
- Date: 2026-09-09

## Context

Meeting transcripts are useful without speaker labels, so diarization must not
make transcription fail. When enabled, the MVP needs a local adapter with
reasonable multi-speaker accuracy, a replaceable interface, and an explicit
deployment/licensing story. A mandatory diarization dependency would make the
CPU-first image much larger and would introduce model-download requirements for
installations that do not need speaker attribution.

## Decision

Define a provider-neutral `SpeakerDiarizer` port and interval-to-transcript
mapping service. The first adapter is `pyannote.audio` using the local
`pyannote/speaker-diarization-community-1` pipeline. It is opt-in through
`DIARIZATION_ENABLED=true`; the model and its dependencies are not mandatory
for the default CPU deployment. Model files are cached on the local Docker
application-data volume.

The adapter emits anonymous labels only. The application maps them to stable
per-meeting labels such as `Speaker 1` and persists a `Speaker` entity linked
to that meeting. Users may rename the display label; the original anonymous
label and source timestamps remain intact. No real-world identity is inferred.

The model repository requires acceptance of its Hugging Face conditions and a
Hugging Face token for the initial download. Operators must review the model
card and terms before enabling it. The `pyannote.audio` software is MIT
licensed, while the selected model is released under CC-BY-4.0 and has
separate access conditions. After download, the pipeline can run from the
local cache without sending meeting audio to a hosted diarization API. See
the [official model card](https://huggingface.co/pyannote/speaker-diarization-community-1)
and [pyannote.audio repository](https://github.com/pyannote/pyannote-audio)
before deployment.

## Consequences

- Transcript creation remains successful when diarization is disabled,
  missing, misconfigured, or uncertain.
- An alternative local or future provider can implement the same port without
  changing transcription or domain mapping logic.
- The default image stays CPU-first and avoids a mandatory heavyweight ML
  dependency.
- Operators must explicitly manage optional model downloads, tokens, licenses,
  and GPU/CPU resource expectations.
