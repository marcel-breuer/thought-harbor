"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="ThoughtHarbor API",
    description="HTTP API for the self-hosted ThoughtHarbor second brain.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report that the API process is available."""

    return {"status": "ok"}
