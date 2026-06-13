import redis
import logging
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

redis_client: Optional[redis.Redis] = None

async def init_redis():
    """初始化Redis连接"""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )
        # 测试连接
        redis_client.ping()
        logger.info("Redis连接成功")
    except Exception as e:
        logger.warning(f"Redis连接失败: {str(e)}，将在不使用缓存的情况下继续运行")
        redis_client = None

def is_rate_limited(key: str) -> bool:
    """检查是否超过限流"""
    if not redis_client:
        return False
    return redis_client.get(key) is not None

def set_rate_limit(key: str, value: str, ttl: int = 5) -> None:
    """设置限流"""
    if redis_client:
        redis_client.setex(key, ttl, value)

def get_from_cache(key: str) -> Optional[str]:
    """从缓存获取"""
    if not redis_client:
        return None
    return redis_client.get(key)

def set_cache(key: str, value: str, ttl: int = 3600) -> None:
    """设置缓存"""
    if redis_client:
        redis_client.setex(key, ttl, value)
