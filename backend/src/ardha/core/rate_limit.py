"""
Rate limiting utilities for API endpoints.

This module provides rate limiting functionality using Redis as a backend
to track request counts per user and enforce limits.
"""

import asyncio
import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis

from ardha.core.config import settings
from ardha.core.security import get_current_user
from ardha.models.user import User

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter for API endpoints.

    Tracks request counts per user in sliding time windows
    and enforces configurable limits with proper error responses.

    Attributes:
        redis: Redis client for storing rate limit data
        requests_per_minute: Maximum requests per minute
        burst_size: Maximum burst size for short spikes
    """

    def __init__(self, redis: Redis, requests_per_minute: int = 10, burst_size: int = 20):
        """
        Initialize rate limiter.

        Args:
            redis: Redis client instance
            requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum burst size for short spikes
        """
        self.redis = redis
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size

    async def is_allowed(self, user_id: UUID, window_seconds: int = 60) -> tuple[bool, dict]:
        """
        Check if user is allowed to make a request.

        Uses sliding window algorithm with Redis to track requests
        in the time window and enforce limits.

        Args:
            user_id: UUID of user making request
            window_seconds: Time window in seconds (default: 60)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            - is_allowed: True if request is allowed
            - rate_limit_info: Dictionary with rate limit details

        Rate Limit Info:
        {
            "allowed": bool,
            "remaining": int,
            "reset_time": int,
            "limit": int,
            "retry_after": int
        }
        """
        current_time = int(time.time())
        window_start = current_time - window_seconds

        # Redis key for this user's requests
        key = f"rate_limit:{user_id}"

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration on the key
            pipe.expire(key, window_seconds)

            # Execute pipeline
            results = await pipe.execute()

            current_requests = results[1]  # zcard result

            # Check if within limits
            if current_requests > self.requests_per_minute:
                # Calculate retry after (when oldest request expires)
                oldest_request_time = await self.redis.zrange(key, 0, 0, withscores=True)
                retry_after = 0

                if oldest_request_time:
                    retry_after = int(oldest_request_time[0][1] + window_seconds - current_time)
                    retry_after = max(1, retry_after)  # At least 1 second

                return False, {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": current_time + retry_after,
                    "limit": self.requests_per_minute,
                    "retry_after": retry_after,
                }

            remaining = max(0, self.requests_per_minute - current_requests)

            return True, {
                "allowed": True,
                "remaining": remaining,
                "reset_time": current_time + window_seconds,
                "limit": self.requests_per_minute,
                "retry_after": 0,
            }

        except Exception as e:
            logger.error(f"Rate limit check failed for user {user_id}: {e}", exc_info=True)
            # Fail open - allow request if rate limiting fails
            return True, {
                "allowed": True,
                "remaining": self.requests_per_minute,
                "reset_time": current_time + window_seconds,
                "limit": self.requests_per_minute,
                "retry_after": 0,
            }

    async def get_rate_limit_headers(self, user_id: UUID) -> dict:
        """
        Get rate limit headers for response.

        Returns standard rate limit headers that can be added
        to HTTP responses for client visibility.

        Args:
            user_id: UUID of user

        Returns:
            Dictionary with rate limit headers
        """
        _, info = await self.is_allowed(user_id)

        return {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset_time"]),
            "X-RateLimit-Retry-After": (
                str(info["retry_after"]) if info["retry_after"] > 0 else None
            ),
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """
    Get or create global rate limiter instance.

    Returns:
        RateLimiter: Configured rate limiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        # Import here to avoid circular imports
        from redis.asyncio import Redis

        redis_client = Redis.from_url(settings.redis.url)
        _rate_limiter = RateLimiter(
            redis=redis_client,
            requests_per_minute=settings.rate_limit.per_minute,
            burst_size=settings.rate_limit.burst,
        )

    return _rate_limiter


async def check_chat_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    """
    Check chat-specific rate limit and raise exception if exceeded.

    This is a FastAPI dependency that enforces rate limiting
    for chat endpoints (10 messages per minute).

    Args:
        current_user: Currently authenticated user

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    rate_limiter = await get_rate_limiter()

    # Use stricter limit for chat messages (10 per minute)
    chat_limiter = RateLimiter(
        redis=rate_limiter.redis,
        requests_per_minute=10,
        burst_size=15,
    )

    is_allowed, info = await chat_limiter.is_allowed(current_user.id)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many messages. Please wait {info['retry_after']} seconds.",
                "retry_after": info["retry_after"],
                "limit": info["limit"],
                "reset_time": info["reset_time"],
            },
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
                "X-RateLimit-Retry-After": str(info["retry_after"]),
                "Retry-After": str(info["retry_after"]),
            },
        )
