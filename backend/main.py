"""FastAPI application entry point for NetCoop AI."""

from fastapi import FastAPI

app = FastAPI(
    title="NetCoop AI API",
    description="Backend API for the NetCoop AI network fault diagnosis project.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is ready."""
    return {"status": "ok"}
