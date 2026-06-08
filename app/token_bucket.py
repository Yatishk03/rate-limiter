"""
Token Bucket Algorithm
----------------------
Each client gets a bucket of MAX_TOKENS tokens.
Tokens refill at REFILL_RATE per second.
Each request consumes 1 token.
If bucket is empty → request blocked (429).

Redis structure:
  HASH  tb:{client_id}
    tokens       → current token count (float)
    last_refill  → unix timestamp of last refill
"""

import time
from app.redis_client import REDIS_CLIENT

MAX_TOKENS   = 10     # max burst — bucket capacity
REFILL_RATE  = 5      # tokens added per second


def is_allowed_token_bucket(client_id: str) -> tuple[bool, int, float]:
    """
    Returns (allowed, remaining_tokens, retry_after_seconds)
    Uses Redis HASH to store token count and last refill time.
    """
    key = f"tb:{client_id}"
    now = time.time()

    # Get current state from Redis
    data = REDIS_CLIENT.hgetall(key)

    if data:
        tokens      = float(data["tokens"])
        last_refill = float(data["last_refill"])
    else:
        # First request — full bucket
        tokens      = MAX_TOKENS
        last_refill = now

    # Calculate how many tokens to add since last refill
    elapsed        = now - last_refill
    tokens_to_add  = elapsed * REFILL_RATE
    tokens         = min(MAX_TOKENS, tokens + tokens_to_add)
    last_refill    = now

    if tokens >= 1:
        # Allow — consume one token
        tokens -= 1
        REDIS_CLIENT.hset(key, mapping={
            "tokens":      tokens,
            "last_refill": last_refill,
        })
        REDIS_CLIENT.expire(key, 3600)  # expire after 1 hour inactivity
        return True, int(tokens), 0.0
    else:
        # Block — calculate when next token arrives
        retry_after = (1 - tokens) / REFILL_RATE
        REDIS_CLIENT.hset(key, mapping={
            "tokens":      tokens,
            "last_refill": last_refill,
        })
        REDIS_CLIENT.expire(key, 3600)
        return False, 0, round(retry_after, 2)