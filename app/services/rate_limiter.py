"""
Rate Limiting Service
Redis-based rate limiter for API endpoints using SlowAPI

Provides configurable rate limits per endpoint type:
- OCR upload: 10 requests/minute
- RAG query: 20 requests/minute
- Summary: 5 requests/minute
- Standard API: 60 requests/minute
- Auth endpoints: 5 requests/minute
"""
import logging
from typing import Optional, Set
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limit configuration for different endpoint types"""

    # Rate limit strings (requests per time period)
    OCR_UPLOAD = "10/minute"      # Expensive OCR operations
    RAG_QUERY = "20/minute"       # RAG queries
    SUMMARY = "5/minute"          # Expensive LLM summarization
    STANDARD_API = "60/minute"    # General API endpoints
    AUTH = "5/minute"             # Prevent brute force attacks
    CAPTURE = "10/minute"         # Auto-capture operations
    KNOWLEDGE = "15/minute"       # Knowledge extraction
    BUSINESS = "15/minute"        # Business RAG operations
    FEEDBACK = "30/minute"        # Feedback endpoints

    # Global default
    GLOBAL_DEFAULT = "100/minute"


class IPWhitelistBlacklist:
    """Manage IP whitelist and blacklist using Redis"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.whitelist_key = "ratelimit:whitelist"
        self.blacklist_key = "ratelimit:blacklist"

    def add_to_whitelist(self, ip: str) -> None:
        """Add IP to whitelist (no rate limits)"""
        try:
            self.redis.sadd(self.whitelist_key, ip)
            logger.info(f"Added IP {ip} to whitelist")
        except Exception as e:
            logger.error(f"Failed to add IP to whitelist: {e}")

    def remove_from_whitelist(self, ip: str) -> None:
        """Remove IP from whitelist"""
        try:
            self.redis.srem(self.whitelist_key, ip)
            logger.info(f"Removed IP {ip} from whitelist")
        except Exception as e:
            logger.error(f"Failed to remove IP from whitelist: {e}")

    def add_to_blacklist(self, ip: str, duration_seconds: Optional[int] = None) -> None:
        """
        Add IP to blacklist (block all requests)

        Args:
            ip: IP address to block
            duration_seconds: Optional duration in seconds (None = permanent)
        """
        try:
            self.redis.sadd(self.blacklist_key, ip)
            if duration_seconds:
                # Set expiration for temporary blocks
                self.redis.expire(f"{self.blacklist_key}:{ip}", duration_seconds)
            logger.warning(f"Added IP {ip} to blacklist (duration: {duration_seconds}s)")
        except Exception as e:
            logger.error(f"Failed to add IP to blacklist: {e}")

    def remove_from_blacklist(self, ip: str) -> None:
        """Remove IP from blacklist"""
        try:
            self.redis.srem(self.blacklist_key, ip)
            logger.info(f"Removed IP {ip} from blacklist")
        except Exception as e:
            logger.error(f"Failed to remove IP from blacklist: {e}")

    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        try:
            return self.redis.sismember(self.whitelist_key, ip)
        except Exception as e:
            logger.error(f"Failed to check whitelist: {e}")
            return False

    def is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        try:
            return self.redis.sismember(self.blacklist_key, ip)
        except Exception as e:
            logger.error(f"Failed to check blacklist: {e}")
            return False

    def get_whitelist(self) -> Set[str]:
        """Get all whitelisted IPs"""
        try:
            return self.redis.smembers(self.whitelist_key)
        except Exception as e:
            logger.error(f"Failed to get whitelist: {e}")
            return set()

    def get_blacklist(self) -> Set[str]:
        """Get all blacklisted IPs"""
        try:
            return self.redis.smembers(self.blacklist_key)
        except Exception as e:
            logger.error(f"Failed to get blacklist: {e}")
            return set()


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting

    Tries to get user ID from request state, falls back to IP address
    Checks whitelist/blacklist before returning

    Args:
        request: FastAPI request object

    Returns:
        str: User identifier (user_id or IP address)
    """
    # Check if IP is blacklisted
    ip = get_remote_address(request)

    try:
        # Try to get whitelist/blacklist manager
        if hasattr(request.app.state, "ip_manager"):
            ip_manager: IPWhitelistBlacklist = request.app.state.ip_manager

            # Bypass rate limiting for whitelisted IPs
            if ip_manager.is_whitelisted(ip):
                logger.debug(f"IP {ip} is whitelisted - bypassing rate limit")
                # Return a special key that has very high limits
                return f"whitelisted:{ip}"

            # Block blacklisted IPs immediately
            if ip_manager.is_blacklisted(ip):
                logger.warning(f"Blocked request from blacklisted IP: {ip}")
                # This will cause rate limit to trigger immediately
                return f"blacklisted:{ip}"
    except Exception as e:
        logger.error(f"Error checking IP whitelist/blacklist: {e}")

    # Try to get user_id from request state (set by auth middleware)
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # Fall back to IP address
    return f"ip:{ip}"


def create_limiter() -> Limiter:
    """
    Create and configure SlowAPI rate limiter

    Returns:
        Limiter: Configured rate limiter instance
    """
    # Initialize Redis connection for rate limiting
    # Use a different Redis database (1) for rate limiting data
    storage_url = settings.RATE_LIMIT_STORAGE_URL if hasattr(settings, 'RATE_LIMIT_STORAGE_URL') else "redis://localhost:6379/1"

    try:
        limiter = Limiter(
            key_func=get_identifier,
            storage_uri=storage_url,
            default_limits=[RateLimitConfig.GLOBAL_DEFAULT],
            headers_enabled=False,  # Disable header injection to avoid Response parameter requirement
            swallow_errors=True,   # Don't crash if Redis is down
        )
        logger.info(f"Rate limiter initialized with storage: {storage_url}")
        return limiter
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {e}")
        # Return a limiter with in-memory storage as fallback
        limiter = Limiter(
            key_func=get_identifier,
            default_limits=[RateLimitConfig.GLOBAL_DEFAULT],
            headers_enabled=False,
            swallow_errors=True,
        )
        logger.warning("Rate limiter using in-memory storage (fallback)")
        return limiter


# Global limiter instance
limiter = create_limiter()


def get_rate_limit_key(endpoint: str, identifier: str) -> str:
    """
    Generate Redis key for rate limiting

    Args:
        endpoint: API endpoint path
        identifier: User/IP identifier

    Returns:
        str: Redis key in format "ratelimit:{endpoint}:{identifier}"
    """
    return f"ratelimit:{endpoint}:{identifier}"


class RateLimitLogger:
    """Log rate limit violations for monitoring"""

    @staticmethod
    def log_violation(request: Request, endpoint: str, limit: str) -> None:
        """
        Log rate limit violation

        Args:
            request: FastAPI request object
            endpoint: API endpoint that was rate limited
            limit: Rate limit that was exceeded
        """
        ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "unknown")

        logger.warning(
            f"Rate limit exceeded | "
            f"IP: {ip} | "
            f"Endpoint: {endpoint} | "
            f"Limit: {limit} | "
            f"User-Agent: {user_agent}"
        )

        # TODO: Could integrate with monitoring system (e.g., Prometheus, CloudWatch)
        # TODO: Could trigger alerts for suspicious activity
        # TODO: Could auto-blacklist IPs with excessive violations


def get_ip_manager(redis_url: Optional[str] = None) -> IPWhitelistBlacklist:
    """
    Get IP whitelist/blacklist manager

    Args:
        redis_url: Optional Redis URL (defaults to settings)

    Returns:
        IPWhitelistBlacklist: Manager instance
    """
    if redis_url is None:
        redis_url = settings.RATE_LIMIT_STORAGE_URL if hasattr(settings, 'RATE_LIMIT_STORAGE_URL') else settings.REDIS_URL

    redis_client = redis.from_url(redis_url)
    return IPWhitelistBlacklist(redis_client)
