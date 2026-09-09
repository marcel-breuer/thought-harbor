# Local speaker diarization

Speaker diarization is an optional second step after local transcription. It
never sends audio to a hosted diarization API by default and it never changes
the original audio or transcript timestamps.

The first adapter is `pyannote.audio` with the local
`pyannote/speaker-diarization-community-1` pipeline. It is deliberately
disabled in the default CPU deployment:

```dotenv
DIARIZATION_ENABLED=true
DIARIZATION_PROVIDER=pyannote
DIARIZATION_MODEL=pyannote/speaker-diarization-community-1
DIARIZATION_DEVICE=cpu
DIARIZATION_MODEL_CACHE=/data/models/diarization
HUGGINGFACE_TOKEN=your-token-for-initial-model-download
```

Install the optional adapter in the backend environment according to the
current pyannote installation instructions. Before the first model download,
accept the model's Hugging Face conditions and review its model card and
license terms. The selected model is released under CC-BY-4.0; the software
package and the model are separate licensing subjects. See the [official model
card](https://huggingface.co/pyannote/speaker-diarization-community-1) and
[pyannote.audio repository](https://github.com/pyannote/pyannote-audio). After
download, keep the model cache on the persistent application volume; audio
processing then stays local.

The adapter returns speaker time intervals. The application assigns each
timestamped transcript segment to the interval with the greatest overlap,
creates anonymous per-meeting entities (`Speaker 1`, `Speaker 2`, …), and
stores provider/model/quality metadata. Segments without a meaningful overlap
remain unassigned. Confidence is retained where the provider supplies it.

Users can inspect and rename speakers through:

```text
GET   /api/v1/meetings/{meeting_id}/speakers
PATCH /api/v1/meetings/{meeting_id}/speakers/{speaker_id}
```

Renaming changes only `display_name`; the anonymous label and source
timestamps remain available for provenance. ThoughtHarbor never claims a
real-world identity unless the user explicitly provides one.

If the adapter is unavailable, lacks its token/model, or returns uncertain
output, the transcript remains `ready` and the meeting/source metadata records
the diarization status and actionable error. A later retry or reprocessing can
run diarization after the local setup is corrected.
