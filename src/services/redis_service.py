import redis
import json
from typing import Optional, Any, Dict, List
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class RedisSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

class RedisService:
    def __init__(self):
        self.settings = RedisSettings()
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False

    # MARK: - Media Caching

    def cache_media_url(self, media_id: str, url: str, ttl: int = 3600) -> bool:
        """Cache media URL with TTL (default 1 hour)"""
        if not self.is_connected():
            return False

        try:
            key = f"media:url:{media_id}"
            self.redis_client.setex(key, ttl, url)
            logger.debug(f"Cached media URL for {media_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache media URL: {e}")
            return False

    def get_cached_media_url(self, media_id: str) -> Optional[str]:
        """Get cached media URL"""
        if not self.is_connected():
            return None

        try:
            key = f"media:url:{media_id}"
            url = self.redis_client.get(key)
            if url:
                logger.debug(f"Retrieved cached media URL for {media_id}")
            return url
        except Exception as e:
            logger.error(f"Failed to get cached media URL: {e}")
            return None

    def cache_media_metadata(self, media_id: str, metadata: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache media metadata (size, type, etc.) with TTL (default 2 hours)"""
        if not self.is_connected():
            return False

        try:
            key = f"media:meta:{media_id}"
            self.redis_client.setex(key, ttl, json.dumps(metadata))
            logger.debug(f"Cached media metadata for {media_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache media metadata: {e}")
            return False

    def get_cached_media_metadata(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get cached media metadata"""
        if not self.is_connected():
            return None

        try:
            key = f"media:meta:{media_id}"
            metadata_json = self.redis_client.get(key)
            if metadata_json:
                logger.debug(f"Retrieved cached media metadata for {media_id}")
                return json.loads(metadata_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached media metadata: {e}")
            return None

    # MARK: - User Session Caching

    def cache_user_session(self, user_id: int, session_data: Dict[str, Any], ttl: int = 86400) -> bool:
        """Cache user session data (default 24 hours)"""
        if not self.is_connected():
            return False

        try:
            key = f"user:session:{user_id}"
            self.redis_client.setex(key, ttl, json.dumps(session_data))
            return True
        except Exception as e:
            logger.error(f"Failed to cache user session: {e}")
            return False

    def get_cached_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user session data"""
        if not self.is_connected():
            return None

        try:
            key = f"user:session:{user_id}"
            session_json = self.redis_client.get(key)
            if session_json:
                return json.loads(session_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached user session: {e}")
            return None

    # MARK: - Close Friends Caching

    def cache_close_friends(self, user_id: int, close_friends_ids: List[int], ttl: int = 1800) -> bool:
        """Cache close friends list (default 30 minutes)"""
        if not self.is_connected():
            return False

        try:
            key = f"user:close_friends:{user_id}"
            self.redis_client.setex(key, ttl, json.dumps(close_friends_ids))
            logger.debug(f"Cached close friends for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache close friends: {e}")
            return False

    def get_cached_close_friends(self, user_id: int) -> Optional[List[int]]:
        """Get cached close friends list"""
        if not self.is_connected():
            return None

        try:
            key = f"user:close_friends:{user_id}"
            friends_json = self.redis_client.get(key)
            if friends_json:
                logger.debug(f"Retrieved cached close friends for user {user_id}")
                return json.loads(friends_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached close friends: {e}")
            return None

    def invalidate_close_friends_cache(self, user_id: int) -> bool:
        """Invalidate close friends cache when updated"""
        if not self.is_connected():
            return False

        try:
            key = f"user:close_friends:{user_id}"
            self.redis_client.delete(key)
            logger.debug(f"Invalidated close friends cache for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate close friends cache: {e}")
            return False

    # MARK: - General Cache Operations

    def delete_key(self, key: str) -> bool:
        """Delete a specific cache key"""
        if not self.is_connected():
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    def clear_user_cache(self, user_id: int) -> bool:
        """Clear all cached data for a user"""
        if not self.is_connected():
            return False

        try:
            pattern = f"user:*:{user_id}"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared all cache for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear user cache: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        if not self.is_connected():
            return {"status": "disconnected"}

        try:
            info = self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}

# Global Redis service instance
redis_service = RedisService()