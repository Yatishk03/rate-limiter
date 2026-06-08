from pydantic import BaseModel
from typing import Literal


class RateLimitResponse(BaseModel):
    allowed:      bool
    client_id:    str
    algorithm:    str
    remaining:    int
    retry_after:  float | None = None  # seconds to wait if blocked
    message:      str