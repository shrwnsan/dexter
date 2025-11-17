"""
Rate Limiting and Cost Control for Dexter Financial Research Agent

Protects against API cost explosion, quota exhaustion, and denial of service
by implementing intelligent rate limiting, circuit breakers, and cost monitoring.
"""

import time
import logging
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: int = 10
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    daily_quota: int = 10000

    # Cost controls
    max_daily_cost: float = 100.0  # USD
    cost_per_request: float = 0.001  # Estimated cost per request

    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds

    # API-specific limits
    openai_requests_per_minute: int = 60
    financial_datasets_requests_per_minute: int = 100

@dataclass
class RequestMetrics:
    """Request tracking metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    cost: float = 0.0
    api_type: str = "unknown"

class RateLimiter:
    """Intelligent rate limiting with circuit breaker and cost controls"""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()

        # Rate limiting state
        self._requests: Dict[str, list] = {
            'second': [],
            'minute': [],
            'hour': [],
            'day': []
        }

        # Cost tracking
        self._daily_cost: float = 0.0
        self._daily_requests: int = 0
        self._last_reset_date = datetime.now().date()

        # Circuit breaker state
        self._circuit_state: Dict[str, CircuitState] = {}
        self._failure_count: Dict[str, int] = {}
        self._last_failure_time: Dict[str, datetime] = {}

        # Thread safety
        self._lock = threading.Lock()

        logger.info("Rate limiter initialized with comprehensive protection")

    def _cleanup_old_requests(self) -> None:
        """Remove old requests from tracking lists"""
        now = datetime.now()
        cutoffs = {
            'second': now - timedelta(seconds=1),
            'minute': now - timedelta(minutes=1),
            'hour': now - timedelta(hours=1),
            'day': now - timedelta(days=1)
        }

        for period, cutoff in cutoffs.items():
            self._requests[period] = [
                req for req in self._requests[period]
                if req.timestamp > cutoff
            ]

    def _reset_daily_counters(self) -> None:
        """Reset daily counters at midnight"""
        today = datetime.now().date()
        if today != self._last_reset_date:
            self._daily_cost = 0.0
            self._daily_requests = 0
            self._last_reset_date = today
            logger.info("Daily counters reset")

    def check_rate_limit(self, api_type: str = "default") -> bool:
        """Check if request is allowed under rate limits"""
        with self._lock:
            self._cleanup_old_requests()
            self._reset_daily_counters()

            # Check basic rate limits
            for period, limit in [
                ('second', self.config.requests_per_second),
                ('minute', self.config.requests_per_minute),
                ('hour', self.config.requests_per_hour),
                ('day', self.config.daily_quota)
            ]:
                if len(self._requests[period]) >= limit:
                    logger.warning(f"Rate limit exceeded for {period}: {len(self._requests[period])}/{limit}")
                    return False

            # Check daily cost limit
            if self._daily_cost >= self.config.max_daily_cost:
                logger.warning(f"Daily cost limit exceeded: ${self._daily_cost:.2f}/${self.config.max_daily_cost:.2f}")
                return False

            # Check API-specific limits
            if api_type == "openai" and self._get_requests_in_minute() >= self.config.openai_requests_per_minute:
                logger.warning("OpenAI rate limit exceeded")
                return False

            if api_type == "financial_datasets" and self._get_requests_in_minute() >= self.config.financial_datasets_requests_per_minute:
                logger.warning("Financial Datasets rate limit exceeded")
                return False

            return True

    def check_circuit_breaker(self, api_type: str = "default") -> bool:
        """Check if circuit breaker allows requests"""
        state = self._circuit_state.get(api_type, CircuitState.CLOSED)

        if state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            last_failure = self._last_failure_time.get(api_type)
            if last_failure and (datetime.now() - last_failure).seconds >= self.config.recovery_timeout:
                self._circuit_state[api_type] = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker for {api_type} moving to HALF_OPEN")
                return True
            else:
                return False

        return True

    def record_request(self, success: bool, api_type: str = "default", cost: float = 0.0) -> None:
        """Record a request outcome"""
        with self._lock:
            now = datetime.now()

            # Record in rate limiting lists
            for period in ['second', 'minute', 'hour', 'day']:
                self._requests[period].append(RequestMetrics(
                    timestamp=now,
                    success=success,
                    cost=cost,
                    api_type=api_type
                ))

            # Update daily statistics
            self._daily_requests += 1
            self._daily_cost += cost

            # Update circuit breaker
            if success:
                if self._circuit_state.get(api_type) == CircuitState.HALF_OPEN:
                    self._circuit_state[api_type] = CircuitState.CLOSED
                    self._failure_count[api_type] = 0
                    logger.info(f"Circuit breaker for {api_type} closed after successful request")
            else:
                self._failure_count[api_type] = self._failure_count.get(api_type, 0) + 1
                self._last_failure_time[api_type] = now

                if self._failure_count[api_type] >= self.config.failure_threshold:
                    self._circuit_state[api_type] = CircuitState.OPEN
                    logger.warning(f"Circuit breaker for {api_type} OPEN after {self._failure_count[api_type]} failures")

    def _get_requests_in_minute(self) -> int:
        """Get number of requests in the last minute"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        return len([req for req in self._requests['minute'] if req.timestamp > cutoff])

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for monitoring"""
        with self._lock:
            self._cleanup_old_requests()

            return {
                'requests_per_second': len(self._requests['second']),
                'requests_per_minute': len(self._requests['minute']),
                'requests_per_hour': len(self._requests['hour']),
                'requests_per_day': len(self._requests['day']),
                'daily_cost': self._daily_cost,
                'daily_requests': self._daily_requests,
                'circuit_states': {k: v.value for k, v in self._circuit_state.items()},
                'failure_counts': self._failure_count.copy()
            }

    def wait_if_needed(self, api_type: str = "default") -> None:
        """Wait if rate limits are exceeded"""
        # Simple exponential backoff implementation
        max_wait_time = 60  # Maximum wait time in seconds
        wait_time = 1

        while not self.check_rate_limit(api_type):
            logger.info(f"Rate limit exceeded, waiting {wait_time}s...")
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, max_wait_time)

# Global rate limiter instance
_rate_limiter = RateLimiter()

def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter

def rate_limit(api_type: str = "default", cost: float = 0.0):
    """Decorator for rate limiting function calls"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()

            # Check rate limits
            if not limiter.check_rate_limit(api_type):
                raise Exception(f"Rate limit exceeded for {api_type}")

            # Check circuit breaker
            if not limiter.check_circuit_breaker(api_type):
                raise Exception(f"Circuit breaker open for {api_type}")

            try:
                result = func(*args, **kwargs)
                limiter.record_request(success=True, api_type=api_type, cost=cost)
                return result
            except Exception as e:
                limiter.record_request(success=False, api_type=api_type)
                raise

        return wrapper
    return decorator