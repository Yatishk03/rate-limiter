from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Annotated
import time

from app.token_bucket   import is_allowed_token_bucket
from app.sliding_window import is_allowed_sliding_window
from app.models         import RateLimitResponse

app = FastAPI(title="Distributed Rate Limiter & API Gateway")

# Prometheus metrics — exposed at /metrics
Instrumentator().instrument(app).expose(app)


# ── Token Bucket endpoint ──────────────────────────────────────
@app.get("/api/token-bucket", response_model=RateLimitResponse)
def token_bucket_route(
    x_client_id: Annotated[str | None, Header()] = None,
    client_id:   str = Query(default="default_client"),
):
    """
    Rate limited route using Token Bucket algorithm.
    Pass client ID via header X-Client-Id or query param client_id.
    """
    cid = x_client_id or client_id
    allowed, remaining, retry_after = is_allowed_token_bucket(cid)

    if allowed:
        return RateLimitResponse(
            allowed=True,
            client_id=cid,
            algorithm="token_bucket",
            remaining=remaining,
            message=f"Request allowed. {remaining} tokens remaining.",
        )
    else:
        return JSONResponse(
            status_code=429,
            content=RateLimitResponse(
                allowed=False,
                client_id=cid,
                algorithm="token_bucket",
                remaining=0,
                retry_after=retry_after,
                message=f"Rate limit exceeded. Retry after {retry_after}s.",
            ).model_dump(),
        )


# ── Sliding Window endpoint ────────────────────────────────────
@app.get("/api/sliding-window", response_model=RateLimitResponse)
def sliding_window_route(
    x_client_id: Annotated[str | None, Header()] = None,
    client_id:   str = Query(default="default_client"),
):
    """
    Rate limited route using Sliding Window algorithm.
    Pass client ID via header X-Client-Id or query param client_id.
    """
    cid = x_client_id or client_id
    allowed, remaining, retry_after = is_allowed_sliding_window(cid)

    if allowed:
        return RateLimitResponse(
            allowed=True,
            client_id=cid,
            algorithm="sliding_window",
            remaining=remaining,
            message=f"Request allowed. {remaining} requests remaining.",
        )
    else:
        return JSONResponse(
            status_code=429,
            content=RateLimitResponse(
                allowed=False,
                client_id=cid,
                algorithm="sliding_window",
                remaining=0,
                retry_after=retry_after,
                message=f"Rate limit exceeded. Retry after {retry_after}s.",
            ).model_dump(),
        )


# ── Health check ───────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}