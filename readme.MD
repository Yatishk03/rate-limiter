# Distributed Rate Limiter & API Gateway

A multi-tenant distributed rate limiter supporting **Token Bucket** and **Sliding Window**
algorithms with Redis-backed shared state. Validated across **113,759 requests** at
**291 RPS** with **2ms minimum latency** and zero server errors under Locust load testing.

## Architecture

```
Client (with client_id)
  │
  ▼
FastAPI API Gateway
  │
  ├── Token Bucket  ──→ Redis HASH  { tokens, last_refill }
  │                     Allow if tokens ≥ 1, else 429
  │
  └── Sliding Window ──→ Redis ZSET { request timestamps }
                         Allow if count < limit, else 429
  │
Prometheus ──→ /metrics (error rates, latency, RPS per endpoint)
```

## Algorithms Implemented

### Token Bucket
- Each client gets a bucket of **10 tokens** (max burst)
- Tokens refill at **5 tokens/second**
- Each request consumes 1 token
- Empty bucket → `429 Too Many Requests` with `retry_after` seconds
- Stored in Redis HASH — O(1) read and write

### Sliding Window
- Tracks all request timestamps in a **60-second window**
- Uses Redis ZSET — timestamps as scores, unique IDs as members
- Removes expired timestamps on every request (pipeline — single round trip)
- Limit: **100 requests per 60 seconds** per client
- More accurate than fixed window — no boundary burst problem

## Key Design Decisions

| Decision | Reason |
|---|---|
| Redis HASH for Token Bucket | O(1) atomic read/write per client |
| Redis ZSET for Sliding Window | Efficient range removal of expired timestamps |
| Redis pipeline for Sliding Window | Two operations in single round trip — reduces latency |
| Per-client isolation | Each client_id has independent state — true multi-tenancy |
| retry_after in 429 response | Client knows exactly when to retry — no guessing |

## Benchmark Results

Load tested using **Locust** with 300 concurrent users across 20 simulated clients.

| Metric | Value |
|---|---|
| Total requests | 113,759 |
| Peak RPS | 291 |
| Minimum latency | 2ms |
| Concurrent users | 300 |
| Server errors (5xx) | 0 |
| 429 responses | Expected — rate limiting working correctly |

> Note: 429 responses are correct behaviour, not failures.
> Zero 5xx errors confirms the system handled all load without crashing.

## API Endpoints

```
GET /api/token-bucket?client_id={id}    → Allow (200) or Block (429)
GET /api/sliding-window?client_id={id}  → Allow (200) or Block (429)
GET /health                             → { status: "ok" }
GET /metrics                            → Prometheus metrics
```

**Response format:**
```json
{
  "allowed": true,
  "client_id": "yatish",
  "algorithm": "token_bucket",
  "remaining": 9,
  "retry_after": null,
  "message": "Request allowed. 9 tokens remaining."
}
```

**Rate limited response (429):**
```json
{
  "allowed": false,
  "client_id": "yatish",
  "algorithm": "token_bucket",
  "remaining": 0,
  "retry_after": 0.2,
  "message": "Rate limit exceeded. Retry after 0.2s."
}
```

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Rate limit state | Redis 7.2 |
| Metrics | Prometheus + prometheus-fastapi-instrumentator |
| Containers | Docker + Docker Compose |
| Load Testing | Locust |

## Run Locally

**Prerequisites:** Docker Desktop running

```bash
# Clone the repo
git clone https://github.com/Yatishk03/rate-limiter.git
cd rate-limiter

# Start all services (app + Redis + Prometheus)
docker compose up --build

# API live at        http://localhost:8000
# Prometheus UI at   http://localhost:9090
# API docs at        http://localhost:8000/docs
```

**Test Token Bucket:**
```bash
# First request — allowed
curl "http://localhost:8000/api/token-bucket?client_id=test"

# Hit 15 times fast to trigger rate limit
for /l %i in (1,1,15) do curl -s "http://localhost:8000/api/token-bucket?client_id=test"
```

**Test Sliding Window:**
```bash
curl "http://localhost:8000/api/sliding-window?client_id=test"
```

## Load Test

```bash
pip install locust
locust -f tests/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089
# Set Users: 300, Spawn rate: 30
```

## Prometheus Metrics

Open **http://localhost:9090** and query:
```
http_requests_total          — total requests by endpoint
http_request_duration_seconds — latency percentiles
```