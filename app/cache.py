from redis import Redis
from app.config import get_settings
import json
from typing import Any, Optional

settings = get_settings()

redis_client = Redis.from_url(settings.REDIS_URL)

def get_subscription_from_cache(subscription_id: int) -> Optional[dict]:
    """Get subscription details from cache"""
    cached_data = redis_client.get(f"subscription:{subscription_id}")
    if cached_data:
        return json.loads(cached_data)
    return None

def set_subscription_in_cache(subscription_id: int, data: dict) -> None:
    """Set subscription details in cache"""
    redis_client.setex(
        f"subscription:{subscription_id}",
        3600,  # Cache for 1 hour
        json.dumps(data)
    )

def delete_subscription_from_cache(subscription_id: int) -> None:
    """Delete subscription from cache"""
    redis_client.delete(f"subscription:{subscription_id}")

def get_delivery_status(delivery_id: int) -> Optional[str]:
    """Get delivery status from cache"""
    return redis_client.get(f"delivery_status:{delivery_id}")

def set_delivery_status(delivery_id: int, status: str) -> None:
    """Set delivery status in cache"""
    redis_client.setex(
        f"delivery_status:{delivery_id}",
        3600,  # Cache for 1 hour
        status
    ) 