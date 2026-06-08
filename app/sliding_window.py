"""
Sliding Window Algorithm
------------------------
Uses a Redis Sorted Set (ZSET) to store request timestamps.
Each request adds current timestamp to the ZSET.
Requests older than WINDOW_SIZE seconds are removed.
If count in window exceeds LIMIT → block.

Redis structure:
  ZSET  sw:{client_id}
    member = unique request ID (timestamp:random)
    score  = unix timestamp
"""

import time
import uuid
from app.redis_client import REDIS_CLIENT

WINDOW_SIZE = 60    # seconds
LIMIT       = 100   # max requests per window


def is_allowed_sliding_window(client_id: str) -> tuple[bool, int, float]:
    """
    Returns (allowed, remaining_requests, retry_after_seconds)
    Uses Redis ZSET — score = timestamp, member = unique request ID.
    """
    key = f"sw:{client_id}"
    now = time.time()
    window_start = now - WINDOW_SIZE

    pipe = REDIS_CLIENT.pipeline()

    # Remove timestamps outside the window
    pipe.zremrangebyscore(key, 0, window_start)

    # Count requests in current window
    pipe.zcard(key)

    results     = pipe.execute()
    current_count = results[1]

    if current_count < LIMIT:
        # Allow — add this request to the window
        member = f"{now}:{uuid.uuid4().hex}"
        REDIS_CLIENT.zadd(key, {member: now})
        REDIS_CLIENT.expire(key, WINDOW_SIZE + 1)
        remaining = LIMIT - current_count - 1
        return True, remaining, 0.0
    else:
        # Block — find oldest request to calculate retry_after
        oldest = REDIS_CLIENT.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry_after = WINDOW_SIZE - (now - oldest[0][1])
        else:
            retry_after = WINDOW_SIZE
        return False, 0, round(retry_after, 2)