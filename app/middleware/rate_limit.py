"""
Rate Limit Middleware
Apply rate limiting globally and handle rate limit errors

Provides:
- Global rate limiting middleware
- Custom 429 error responses with retry-after headers
- Rate limit violation logging
- Graceful degradation if Redis is unavailable
"""
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
import time

from app.services.rate_limiter import RateLimitLogger, limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware

    Applies rate limits globally and logs violations
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler

        Returns:
            Response: HTTP response
        """
        start_time = time.time()

        try:
            # Process the request
            response = await call_next(request)

            # Add rate limit info to response headers (if available)
            if hasattr(request.state, "view_rate_limit"):
                limit_data = request.state.view_rate_limit
                # Handle both dict and tuple formats from SlowAPI
                if isinstance(limit_data, dict):
                    response.headers["X-RateLimit-Limit"] = str(limit_data.get("limit", ""))
                    response.headers["X-RateLimit-Remaining"] = str(limit_data.get("remaining", ""))
                    response.headers["X-RateLimit-Reset"] = str(limit_data.get("reset", ""))
                elif isinstance(limit_data, tuple) and len(limit_data) >= 3:
                    # Tuple format: (limit, remaining, reset)
                    response.headers["X-RateLimit-Limit"] = str(limit_data[0])
                    response.headers["X-RateLimit-Remaining"] = str(limit_data[1])
                    response.headers["X-RateLimit-Reset"] = str(limit_data[2])

            return response

        except RateLimitExceeded as e:
            # Log the violation
            endpoint = request.url.path
            RateLimitLogger.log_violation(request, endpoint, str(e))

            # Calculate retry-after time
            retry_after = self._calculate_retry_after(e)

            # Return 429 response with retry-after header
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                    "endpoint": endpoint,
                    "limit": str(e)
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": self._extract_limit(str(e)),
                    "X-RateLimit-Remaining": "0",
                }
            )

        except Exception as e:
            # Don't let rate limiting errors crash the application
            logger.error(f"Rate limiting error: {e}")
            # Continue processing the request
            response = await call_next(request)
            return response

    def _calculate_retry_after(self, error: RateLimitExceeded) -> int:
        """
        Calculate retry-after time from rate limit error

        Args:
            error: RateLimitExceeded error

        Returns:
            int: Seconds until rate limit resets
        """
        # Default to 60 seconds
        retry_after = 60

        try:
            # Extract time window from error message
            # Format: "X per Y minute" or "X per Y second"
            error_msg = str(error)
            if "minute" in error_msg.lower():
                retry_after = 60
            elif "second" in error_msg.lower():
                retry_after = int(error_msg.split()[2]) if len(error_msg.split()) > 2 else 60
            elif "hour" in error_msg.lower():
                retry_after = 3600
        except Exception as e:
            logger.error(f"Error calculating retry-after: {e}")

        return retry_after

    def _extract_limit(self, error_msg: str) -> str:
        """
        Extract rate limit from error message

        Args:
            error_msg: Error message string

        Returns:
            str: Rate limit string (e.g., "10 per 1 minute")
        """
        try:
            # Error format: "10 per 1 minute"
            return error_msg
        except Exception:
            return "unknown"


async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom error handler for rate limit exceeded

    Args:
        request: HTTP request
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse: Custom error response
    """
    # Log the violation
    endpoint = request.url.path
    RateLimitLogger.log_violation(request, endpoint, str(exc))

    # Calculate retry-after
    retry_after = 60  # Default
    try:
        error_msg = str(exc)
        if "minute" in error_msg.lower():
            retry_after = 60
        elif "second" in error_msg.lower():
            parts = error_msg.split()
            if len(parts) >= 3:
                retry_after = int(parts[2])
        elif "hour" in error_msg.lower():
            retry_after = 3600
    except Exception as e:
        logger.error(f"Error calculating retry-after: {e}")

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests to {endpoint}. Please try again in {retry_after} seconds.",
            "retry_after": retry_after,
            "endpoint": endpoint,
            "limit": str(exc),
            "documentation": "See API documentation for rate limits: /docs"
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc),
            "X-RateLimit-Remaining": "0",
        }
    )


class IPBlacklistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to block blacklisted IPs immediately

    This runs before rate limiting to prevent blacklisted IPs
    from consuming rate limit resources
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check if IP is blacklisted

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler

        Returns:
            Response: HTTP response or 403 Forbidden
        """
        try:
            # Check if IP manager is available
            if hasattr(request.app.state, "ip_manager"):
                ip = get_remote_address(request)
                ip_manager = request.app.state.ip_manager

                # Block blacklisted IPs
                if ip_manager.is_blacklisted(ip):
                    logger.warning(f"Blocked request from blacklisted IP: {ip}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "Forbidden",
                            "message": "Your IP address has been blocked due to suspicious activity."
                        }
                    )

            # Continue to next middleware
            return await call_next(request)

        except Exception as e:
            logger.error(f"Error in IP blacklist middleware: {e}")
            # Don't block requests if there's an error
            return await call_next(request)


def get_rate_limit_status(request: Request, endpoint: str) -> dict:
    """
    Get current rate limit status for an endpoint

    Args:
        request: FastAPI request object
        endpoint: Endpoint identifier

    Returns:
        dict: Rate limit status with limit, remaining, reset
    """
    try:
        from app.services.rate_limiter import get_identifier, get_rate_limit_key
        import redis

        # Get identifier
        identifier = get_identifier(request)

        # Get Redis key
        key = get_rate_limit_key(endpoint, identifier)

        # Get current count from Redis
        # This is a simplified version - actual implementation depends on SlowAPI internals
        return {
            "limit": "unknown",
            "remaining": "unknown",
            "reset": "unknown"
        }
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return {
            "limit": "unknown",
            "remaining": "unknown",
            "reset": "unknown"
        }
