# Local meeting transcription

Audio uploads are processed asynchronously by the Celery worker. The API
stores the original audio in the local filesystem volume and returns without
loading a speech model or waiting for a long recording to finish.

The worker normalizes the stored audio with FFmpeg to mono, 16 kHz WAV and
transcribes it with the local `faster-whisper` adapter. The default runtime is
CPU-only:

```dotenv
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL_CACHE=/data/models/whisper
```

Compose persists the model cache in the application-data volume. A GPU is
optional and can be enabled for the worker by selecting a compatible CUDA
image/runtime and setting `WHISPER_DEVICE=cuda` plus an appropriate
`WHISPER_COMPUTE_TYPE`; no cloud provider is required.

Successful processing creates a meeting, a transcript, and ordered segments
with millisecond timestamps and detected language. Provider, model, model
version, and segment count are retained as metadata. The source audio is never
replaced, so future diarization and other derived artifacts can retain their
link to the original content.

Processing status and progress are available through the inbox API and the
`ProcessingJob`/`ProcessingAttempt` records. FFmpeg, missing model/runtime,
unreadable storage, corrupt audio, and audio without detectable speech are
reported as actionable failed processing attempts. Retrying the inbox item
creates another attempt; an existing transcript prevents duplicate records.

The worker is the only runtime that invokes FFmpeg or loads faster-whisper.
FastAPI and MCP use the same application services but do not perform blocking
transcription work themselves.
