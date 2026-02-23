#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 8 - API Rate Limiting & Request Throttling System
Implement rate limiting, request throttling, quota management, and fair access

This module provides:
1. Token bucket rate limiting
2. Sliding window request tracking
3. Per-user and per-endpoint quotas
4. Adaptive throttling based on load
5. Fair access scheduling and prioritization
6. Rate limit headers and responses
"""

import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


class RequestPriority(Enum):
    """Request priority levels"""
    LOW = 1
    NORMAL = 10
    HIGH = 100
    CRITICAL = 1000


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests_per_period: int
    period_seconds: int
    burst_size: int = 0
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    
    @property
    def tokens_per_second(self) -> float:
        """Tokens generated per second"""
        return self.requests_per_period / self.period_seconds


@dataclass
class QuotaUsage:
    """Quota usage tracking"""
    user_id: str
    endpoint: str
    requests_made: int
    requests_limit: int
    reset_time: str
    percentage_used: float = 0.0
    
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded"""
        return self.requests_made >= self.requests_limit
    
    def remaining(self) -> int:
        """Get remaining requests"""
        return max(0, self.requests_limit - self.requests_made)


@dataclass
class RateLimitResponse:
    """Rate limit response information"""
    allowed: bool
    retry_after_seconds: Optional[float] = None
    requests_remaining: int = 0
    requests_limit: int = 0
    reset_timestamp: Optional[float] = None
    error_message: str = ""


class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def try_consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens
        
        Returns:
            (success, wait_time_seconds)
        """
        with self.lock:
            now = time.time()
            time_passed = now - self.last_refill
            
            # Refill tokens
            self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate
                return False, wait_time
    
    def get_status(self) -> Dict[str, float]:
        """Get current bucket status"""
        with self.lock:
            now = time.time()
            time_passed = now - self.last_refill
            tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
            
            return {
                "available_tokens": tokens,
                "capacity": self.capacity,
                "refill_rate": self.refill_rate
            }


class SlidingWindowLimiter:
    """Sliding window rate limiter"""
    
    def __init__(self, requests_limit: int, window_seconds: int):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = threading.Lock()
    
    def try_consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """Try to consume tokens within sliding window"""
        with self.lock:
            now = time.time()
            
            # Remove expired requests
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            if len(self.requests) + tokens <= self.requests_limit:
                for _ in range(tokens):
                    self.requests.append(now)
                return True, 0.0
            else:
                # Calculate wait time until oldest request expires
                if self.requests:
                    oldest = self.requests[0]
                    wait_time = (oldest + self.window_seconds) - now
                    return False, wait_time
                return False, self.window_seconds


class AdaptiveThrottler:
    """Adaptive throttling based on system load"""
    
    def __init__(self, base_limit: int, min_limit: int = 10, max_limit: int = 1000):
        self.base_limit = base_limit
        self.current_limit = base_limit
        self.min_limit = min_limit
        self.max_limit = max_limit
        
        self.error_count = 0
        self.success_count = 0
        self.load_factor = 1.0
        
        self.token_bucket = TokenBucket(base_limit, base_limit / 60)
        self.lock = threading.Lock()
    
    def adjust_limit(self, error_rate: float):
        """Adjust limit based on error rate"""
        with self.lock:
            if error_rate > 0.05:  # More than 5% error
                self.current_limit = max(self.min_limit, int(self.current_limit * 0.9))
                self.load_factor = 0.9
            elif error_rate < 0.01:  # Less than 1% error
                self.current_limit = min(self.max_limit, int(self.current_limit * 1.1))
                self.load_factor = 1.1
    
    def try_consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """Try to consume with adaptive limiting"""
        return self.token_bucket.try_consume(tokens)
    
    def get_status(self) -> Dict[str, float]:
        """Get throttler status"""
        with self.lock:
            return {
                "current_limit": self.current_limit,
                "load_factor": self.load_factor,
                "error_count": self.error_count,
                "success_count": self.success_count
            }


class RateLimiter:
    """Main rate limiter managing user and endpoint limits"""
    
    def __init__(self, default_limit: RateLimit = None):
        self.default_limit = default_limit or RateLimit(100, 60)
        
        # Per-user limiters
        self.user_limiters: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                self.default_limit.requests_per_period,
                self.default_limit.tokens_per_second
            )
        )
        
        # Per-endpoint limiters
        self.endpoint_limiters: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                self.default_limit.requests_per_period * 10,  # Higher limit for endpoints
                self.default_limit.tokens_per_second * 10
            )
        )
        
        # Per-user-endpoint custom quotas
        self.custom_quotas: Dict[Tuple[str, str], RateLimit] = {}
        
        # Request history for analytics
        self.request_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        
        self.lock = threading.Lock()
    
    def set_user_limit(self, user_id: str, limit: RateLimit):
        """Set custom limit for user"""
        bucket = TokenBucket(limit.requests_per_period, limit.tokens_per_second)
        self.user_limiters[user_id] = bucket
    
    def set_endpoint_limit(self, endpoint: str, limit: RateLimit):
        """Set custom limit for endpoint"""
        bucket = TokenBucket(limit.requests_per_period, limit.tokens_per_second)
        self.endpoint_limiters[endpoint] = bucket
    
    def set_quota(self, user_id: str, endpoint: str, limit: RateLimit):
        """Set custom quota for user+endpoint combination"""
        with self.lock:
            self.custom_quotas[(user_id, endpoint)] = limit
    
    def check_rate_limit(self, user_id: str, endpoint: str) -> RateLimitResponse:
        """Check if request is allowed"""
        current_time = time.time()
        
        # Check user limit
        user_bucket = self.user_limiters[user_id]
        user_allowed, user_wait = user_bucket.try_consume(1)
        
        # Check endpoint limit
        endpoint_bucket = self.endpoint_limiters[endpoint]
        endpoint_allowed, endpoint_wait = endpoint_bucket.try_consume(1)
        
        # Check custom quota
        quota_allowed = True
        quota_wait = 0.0
        
        with self.lock:
            if (user_id, endpoint) in self.custom_quotas:
                # Use sliding window for custom quotas
                key = (user_id, endpoint)
                if key not in self.request_history:
                    self.request_history[key] = deque()
                
                quota = self.custom_quotas[key]
                limit = quota.requests_per_period
                window = quota.period_seconds
                
                # Remove old requests
                cutoff = current_time - window
                while self.request_history[key] and self.request_history[key][0] < cutoff:
                    self.request_history[key].popleft()
                
                quota_allowed = len(self.request_history[key]) < limit
                
                if quota_allowed:
                    self.request_history[key].append(current_time)
                else:
                    if self.request_history[key]:
                        oldest = self.request_history[key][0]
                        quota_wait = (oldest + window) - current_time
        
        # Track request
        with self.lock:
            key = f"{user_id}:{endpoint}"
            self.request_history[key].append(current_time)
        
        # Determine if request is allowed
        allowed = user_allowed and endpoint_allowed and quota_allowed
        
        if not allowed:
            wait_time = max(user_wait, endpoint_wait, quota_wait)
            reset_time = current_time + wait_time
            
            return RateLimitResponse(
                allowed=False,
                retry_after_seconds=wait_time,
                reset_timestamp=reset_time,
                error_message=f"Rate limit exceeded. Retry after {wait_time:.1f}s"
            )
        
        # Calculate remaining
        user_status = user_bucket.get_status()
        remaining = int(user_status["available_tokens"])
        limit = user_status["capacity"]
        
        return RateLimitResponse(
            allowed=True,
            requests_remaining=remaining,
            requests_limit=limit,
            reset_timestamp=current_time + self.default_limit.period_seconds
        )
    
    def get_user_usage(self, user_id: str, endpoint: Optional[str] = None) -> Dict[str, QuotaUsage]:
        """Get usage statistics for user"""
        usage = {}
        
        current_time = time.time()
        
        # User overall usage
        user_bucket = self.user_limiters[user_id]
        user_status = user_bucket.get_status()
        used = user_status["capacity"] - int(user_status["available_tokens"])
        
        usage["overall"] = QuotaUsage(
            user_id=user_id,
            endpoint="*",
            requests_made=used,
            requests_limit=int(user_status["capacity"]),
            reset_time=(datetime.now() + timedelta(seconds=self.default_limit.period_seconds)).isoformat(),
            percentage_used=(used / user_status["capacity"] * 100) if user_status["capacity"] > 0 else 0
        )
        
        # Per-endpoint usage
        if endpoint:
            key = f"{user_id}:{endpoint}"
            history = self.request_history.get(key, deque())
            cutoff = current_time - self.default_limit.period_seconds
            requests_in_window = sum(1 for t in history if t > cutoff)
            
            usage[endpoint] = QuotaUsage(
                user_id=user_id,
                endpoint=endpoint,
                requests_made=requests_in_window,
                requests_limit=int(self.user_limiters[user_id].capacity),
                reset_time=(datetime.now() + timedelta(seconds=self.default_limit.period_seconds)).isoformat(),
                percentage_used=(requests_in_window / self.user_limiters[user_id].capacity * 100)
            )
        
        return usage


class RequestScheduler:
    """Fair request scheduling with priority support"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.queue: Dict[int, deque] = {
            priority.value: deque() for priority in RequestPriority
        }
        self.max_queue_size = max_queue_size
        self.lock = threading.Lock()
    
    def enqueue_request(self, request_id: str, priority: RequestPriority = RequestPriority.NORMAL):
        """Enqueue a request"""
        with self.lock:
            total_queued = sum(len(q) for q in self.queue.values())
            if total_queued >= self.max_queue_size:
                return False
            
            self.queue[priority.value].append(request_id)
            return True
    
    def dequeue_request(self) -> Optional[str]:
        """Dequeue next request (highest priority first)"""
        with self.lock:
            # Check priorities from highest to lowest
            for priority in sorted(self.queue.keys(), reverse=True):
                if self.queue[priority]:
                    return self.queue[priority].popleft()
            
            return None
    
    def get_queue_status(self) -> Dict[str, int]:
        """Get queue status"""
        with self.lock:
            return {
                priority.name: len(self.queue[priority.value])
                for priority in RequestPriority
            }


# Example usage
if __name__ == "__main__":
    # Create rate limiter
    limiter = RateLimiter()
    
    # Test requests
    for i in range(5):
        response = limiter.check_rate_limit(f"user_{i % 2}", f"/api/endpoint{i % 3}")
        print(f"Request {i}: {'✓ ALLOWED' if response.allowed else '✗ BLOCKED'}")
        if not response.allowed:
            print(f"  Retry after {response.retry_after_seconds:.1f}s")
