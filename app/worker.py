# Import required modules
from celery import Celery
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import WebhookDelivery, DeliveryAttempt, DeliveryStatus, Subscription
from app.cache import get_subscription_from_cache, set_delivery_status
import httpx
import json
from datetime import datetime, timedelta
import logging
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Load application settings
settings = get_settings()

# Initialize Celery application
celery_app = Celery(
    "webhook_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Set up logging
logger = logging.getLogger(__name__)

# Helper function to get delivery details from database
async def get_delivery(session: AsyncSession, delivery_id: int) -> WebhookDelivery:
    result = await session.execute(
        select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
    )
    return result.scalar_one_or_none()

# Helper function to get subscription details from database
async def get_subscription(session: AsyncSession, subscription_id: int) -> Subscription:
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    return result.scalar_one_or_none()

# Main task for delivering webhooks
@celery_app.task(bind=True, max_retries=settings.MAX_RETRY_ATTEMPTS)
async def deliver_webhook(self, delivery_id: int):
    async with AsyncSessionLocal() as session:
        try:
            # Get delivery details from database
            delivery = await get_delivery(session, delivery_id)
            if not delivery:
                logger.error(f"Delivery {delivery_id} not found")
                return

            # Get subscription details from cache or database
            subscription_data = get_subscription_from_cache(delivery.subscription_id)
            if not subscription_data:
                subscription = await get_subscription(session, delivery.subscription_id)
                if not subscription:
                    logger.error(f"Subscription {delivery.subscription_id} not found")
                    return
                subscription_data = {
                    "target_url": subscription.target_url,
                    "secret_key": subscription.secret_key
                }
                set_subscription_in_cache(delivery.subscription_id, subscription_data)

            # Make HTTP request to deliver webhook
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        subscription_data["target_url"],
                        json=delivery.payload,
                        timeout=10.0
                    )
                    
                    # Log delivery attempt
                    attempt = DeliveryAttempt(
                        delivery_id=delivery_id,
                        attempt_number=delivery.attempt_count + 1,
                        status_code=response.status_code,
                        response_body=response.text
                    )
                    session.add(attempt)
                    
                    if response.status_code >= 200 and response.status_code < 300:
                        # Mark delivery as successful
                        delivery.status = DeliveryStatus.SUCCESS
                        set_delivery_status(delivery_id, "success")
                    else:
                        # Handle failure with retry
                        raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Delivery attempt failed: {str(e)}")
                
                # Calculate next retry time with exponential backoff
                retry_delay = min(
                    settings.INITIAL_RETRY_DELAY * (settings.RETRY_BACKOFF_FACTOR ** self.request.retries),
                    settings.MAX_RETRY_DELAY
                )
                
                if self.request.retries < settings.MAX_RETRY_ATTEMPTS:
                    # Schedule retry
                    delivery.status = DeliveryStatus.RETRYING
                    delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                    set_delivery_status(delivery_id, "retrying")
                    raise self.retry(exc=e, countdown=retry_delay)
                else:
                    # Mark as failed after max retries
                    delivery.status = DeliveryStatus.FAILED
                    set_delivery_status(delivery_id, "failed")
                    
            # Update delivery statistics
            delivery.attempt_count += 1
            delivery.last_attempt_at = datetime.utcnow()
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error processing delivery {delivery_id}: {str(e)}")
            await session.rollback()
            raise

# Task to clean up old delivery logs
@celery_app.task
async def cleanup_old_logs():
    """Clean up delivery attempts older than retention period"""
    async with AsyncSessionLocal() as session:
        try:
            # Calculate retention cutoff time
            retention_period = datetime.utcnow() - timedelta(hours=settings.LOG_RETENTION_HOURS)
            
            # Delete old delivery attempts
            await session.execute(
                select(DeliveryAttempt)
                .where(DeliveryAttempt.created_at < retention_period)
                .delete()
            )
            await session.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {str(e)}")
            await session.rollback()
            raise 