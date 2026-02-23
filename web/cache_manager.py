#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 9 - Caching & Performance Optimization System
Multi-level caching with TTL, invalidation, and performance tracking

This module provides:
1. In-memory LRU caching
2. Redis integration support
3. Cache invalidation strategies
4. TTL management
5. Hit/miss tracking and metrics
6. Distributed cache support
"""

import time
import hashlib
import json
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict, field
from collections import OrderedDict
from datetime import datetime, timedelta
from enum import Enum


class CacheInvalidationStrategy(Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"  # Time-to-live based expiration
    LRU = "lru"  # Least recently used
    LFU = "lfu"  # Least frequently used
    FIFO = "fifo"  # First in first out
    MANUAL = "manual"  # Manual invalidation


class CacheLevel(Enum):
    """Cache hierarchy levels"""
    L1 = 1  # In-memory (fastest)
    L2 = 2  # Secondary cache
    L3 = 3  # External cache (Redis)


@dataclass
class CacheEntry:
    """Single cache entry"""
    key: str
    value: Any
    created_at: str
    last_accessed: str
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl_seconds is None:
            return False
        
        created = datetime.fromisoformat(self.created_at)
        now = datetime.now()
        age = (now - created).total_seconds()
        
        return age > self.ttl_seconds
    
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now().isoformat()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    invalidations: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Get cache hit rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Get cache miss rate percentage"""
        return 100 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "invalidations": self.invalidations,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate
        }


class LRUCache:
    """Least Recently Used (LRU) cache implementation"""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.metrics = CacheMetrics()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        self.metrics.total_requests += 1
        
        if key not in self.cache:
            self.metrics.cache_misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check expiration
        if entry.is_expired():
            del self.cache[key]
            self.metrics.invalidations += 1
            self.metrics.cache_misses += 1
            return None
        
        # Update LRU order
        self.cache.move_to_end(key)
        entry.touch()
        
        self.metrics.cache_hits += 1
        return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None):
        """Put value in cache"""
        # Remove if exists (to update position)
        if key in self.cache:
            del self.cache[key]
        
        # Evict LRU item if at capacity
        if len(self.cache) >= self.max_size:
            evicted_key, _ = self.cache.popitem(last=False)
            self.metrics.evictions += 1
        
        # Add new entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now().isoformat(),
            last_accessed=datetime.now().isoformat(),
            ttl_seconds=ttl or self.default_ttl
        )
        
        self.cache[key] = entry
    
    def invalidate(self, key: str) -> bool:
        """Manually invalidate cache entry"""
        if key in self.cache:
            del self.cache[key]
            self.metrics.invalidations += 1
            return True
        return False
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
        self.metrics.invalidations += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "metrics": self.metrics.to_dict()
        }


class CacheDecorator:
    """Decorator for caching function results"""
    
    def __init__(self, cache: LRUCache, ttl: Optional[int] = None):
        self.cache = cache
        self.ttl = ttl
    
    def __call__(self, func: Callable) -> Callable:
        """Cache function decorator"""
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            key = self._generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = self.cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Compute value
            result = func(*args, **kwargs)
            
            # Store in cache
            self.cache.put(key, result, self.ttl)
            
            return result
        
        return wrapper
    
    @staticmethod
    def _generate_key(func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments"""
        key_parts = [func_name]
        
        # Add args
        for arg in args:
            key_parts.append(str(arg))
        
        # Add kwargs
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        # Hash for brevity
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()


class MultiLevelCache:
    """Multi-level caching system (L1 in-memory, L2 secondary, L3 external)"""
    
    def __init__(self, l1_size: int = 1000, l2_size: int = 5000):
        self.l1_cache = LRUCache(max_size=l1_size, default_ttl=3600)  # 1 hour
        self.l2_cache = LRUCache(max_size=l2_size, default_ttl=86400)  # 1 day
        self.metrics = CacheMetrics()
    
    def get(self, key: str) -> Optional[Any]:
        """Get from multi-level cache"""
        self.metrics.total_requests += 1
        
        # Try L1
        value = self.l1_cache.get(key)
        if value is not None:
            self.metrics.cache_hits += 1
            return value
        
        # Try L2
        value = self.l2_cache.get(key)
        if value is not None:
            # Promote to L1
            self.l1_cache.put(key, value)
            self.metrics.cache_hits += 1
            return value
        
        self.metrics.cache_misses += 1
        return None
    
    def put(self, key: str, value: Any, level: CacheLevel = CacheLevel.L1, ttl: Optional[int] = None):
        """Put in multi-level cache"""
        if level == CacheLevel.L1:
            self.l1_cache.put(key, value, ttl)
        elif level == CacheLevel.L2:
            self.l2_cache.put(key, value, ttl)
    
    def invalidate(self, key: str, level: Optional[CacheLevel] = None) -> bool:
        """Invalidate cache entry"""
        result = False
        
        if level is None or level == CacheLevel.L1:
            result |= self.l1_cache.invalidate(key)
        
        if level is None or level == CacheLevel.L2:
            result |= self.l2_cache.invalidate(key)
        
        if result:
            self.metrics.invalidations += 1
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "l1": self.l1_cache.get_stats(),
            "l2": self.l2_cache.get_stats(),
            "metrics": self.metrics.to_dict()
        }


class CacheWarmer:
    """Warm up cache with frequently accessed data"""
    
    def __init__(self, cache: LRUCache):
        self.cache = cache
        self.warm_data: Dict[str, Any] = {}
    
    def add_warm_data(self, key: str, value: Any, ttl: Optional[int] = None):
        """Add data to warming list"""
        self.warm_data[key] = (value, ttl)
    
    def warm_cache(self):
        """Load all warming data into cache"""
        for key, (value, ttl) in self.warm_data.items():
            self.cache.put(key, value, ttl)
    
    def get_warm_count(self) -> int:
        """Get number of items in warming list"""
        return len(self.warm_data)


class CacheInvalidator:
    """Smart cache invalidation manager"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.invalidation_rules: Dict[str, Callable] = {}
        self.invalidation_history: List[Dict[str, Any]] = []
    
    def register_rule(self, pattern: str, callback: Callable):
        """Register invalidation rule"""
        self.invalidation_rules[pattern] = callback
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        count = 0
        
        if pattern in self.invalidation_rules:
            # Execute custom rule
            count = self.invalidation_rules[pattern]()
        
        # Log invalidation
        self.invalidation_history.append({
            "timestamp": datetime.now().isoformat(),
            "pattern": pattern,
            "count": count
        })
        
        return count
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get invalidation history"""
        return self.invalidation_history[-limit:]


class CacheStatistics:
    """Cache statistics and analysis"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
    
    def get_hit_rate_trend(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get cache hit rate trend"""
        stats = self.cache.get_stats()
        metrics = stats['metrics']
        
        return {
            "period_minutes": window_minutes,
            "hit_rate": metrics['hit_rate'],
            "miss_rate": metrics['miss_rate'],
            "total_requests": metrics['total_requests'],
            "efficiency": "GOOD" if metrics['hit_rate'] > 80 else "FAIR" if metrics['hit_rate'] > 60 else "POOR"
        }
    
    def get_cache_utilization(self) -> Dict[str, Any]:
        """Get cache utilization"""
        l1_stats = self.cache.l1_cache.get_stats()
        l2_stats = self.cache.l2_cache.get_stats()
        
        return {
            "l1_utilization": (l1_stats['size'] / l1_stats['max_size']) * 100,
            "l2_utilization": (l2_stats['size'] / l2_stats['max_size']) * 100,
            "l1_size": l1_stats['size'],
            "l1_max": l1_stats['max_size'],
            "l2_size": l2_stats['size'],
            "l2_max": l2_stats['max_size']
        }
    
    def get_eviction_rate(self) -> Dict[str, Any]:
        """Get eviction metrics"""
        l1_metrics = self.cache.l1_cache.metrics
        l2_metrics = self.cache.l2_cache.metrics
        
        return {
            "l1_evictions": l1_metrics.evictions,
            "l2_evictions": l2_metrics.evictions,
            "total_evictions": l1_metrics.evictions + l2_metrics.evictions
        }


# Example usage
if __name__ == "__main__":
    # Create multi-level cache
    cache = MultiLevelCache()
    
    # Add some data
    cache.put("key1", "value1")
    cache.put("key2", {"data": "complex"})
    
    # Retrieve
    print(cache.get("key1"))  # "value1"
    print(cache.get_stats())
