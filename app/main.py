# Import required FastAPI and database components
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import json
from datetime import datetime

# Import local modules
from app.database import get_db
from app.models import Subscription, WebhookDelivery, DeliveryAttempt, DeliveryStatus
from app.schemas import (
    SubscriptionCreate,
    SubscriptionResponse,
    WebhookPayload,
    DeliveryStatusResponse,
    DeliveryAttemptResponse
)
from app.worker import deliver_webhook, cleanup_old_logs
from app.cache import set_subscription_in_cache, delete_subscription_from_cache

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Webhook Delivery Service",
    description="A robust webhook delivery service with retry mechanism and logging",
    version="1.0.0"
)

# Create a new subscription
@app.post("/subscriptions/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    # Create new subscription record
    db_subscription = Subscription(
        name=subscription.name,
        target_url=subscription.target_url,
        secret_key=subscription.secret_key
    )
    db.add(db_subscription)
    await db.commit()
    await db.refresh(db_subscription)
    
    # Cache subscription details for faster access
    set_subscription_in_cache(
        db_subscription.id,
        {
            "target_url": db_subscription.target_url,
            "secret_key": db_subscription.secret_key
        }
    )
    
    return db_subscription

# List all subscriptions
@app.get("/subscriptions/", response_model=List[SubscriptionResponse])
async def list_subscriptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription))
    return result.scalars().all()

# Get a specific subscription by ID
@app.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(subscription_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription

# Update an existing subscription
@app.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription: SubscriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    # Find the subscription to update
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    db_subscription = result.scalar_one_or_none()
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update subscription details
    db_subscription.name = subscription.name
    db_subscription.target_url = subscription.target_url
    db_subscription.secret_key = subscription.secret_key
    
    await db.commit()
    await db.refresh(db_subscription)
    
    # Update cache with new subscription details
    set_subscription_in_cache(
        db_subscription.id,
        {
            "target_url": db_subscription.target_url,
            "secret_key": db_subscription.secret_key
        }
    )
    
    return db_subscription

# Delete a subscription
@app.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(subscription_id: int, db: AsyncSession = Depends(get_db)):
    # Find the subscription to delete
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Delete the subscription
    await db.delete(subscription)
    await db.commit()
    
    # Remove subscription from cache
    delete_subscription_from_cache(subscription_id)

# Ingest a new webhook
@app.post("/ingest/{subscription_id}", status_code=status.HTTP_202_ACCEPTED)
async def ingest_webhook(
    subscription_id: int,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db)
):
    # Verify subscription exists
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Create delivery record for the webhook
    delivery = WebhookDelivery(
        subscription_id=subscription_id,
        payload=payload.dict(),
        status=DeliveryStatus.PENDING
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    
    # Queue the delivery task for background processing
    deliver_webhook.delay(delivery.id)
    
    return {"delivery_id": delivery.id, "status": "accepted"}

# Get delivery status for a specific webhook
@app.get("/deliveries/{delivery_id}", response_model=DeliveryStatusResponse)
async def get_delivery_status(delivery_id: int, db: AsyncSession = Depends(get_db)):
    # Get delivery details
    result = await db.execute(
        select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    # Get all delivery attempts
    result = await db.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.delivery_id == delivery_id)
        .order_by(DeliveryAttempt.attempt_number)
    )
    attempts = result.scalars().all()
    
    # Format response with delivery status and attempts
    return {
        "delivery_id": delivery.id,
        "status": delivery.status.value,
        "attempt_count": delivery.attempt_count,
        "last_attempt_at": delivery.last_attempt_at,
        "next_retry_at": delivery.next_retry_at,
        "attempts": [
            {
                "attempt_number": attempt.attempt_number,
                "status_code": attempt.status_code,
                "response_body": attempt.response_body,
                "error_message": attempt.error_message,
                "created_at": attempt.created_at
            }
            for attempt in attempts
        ]
    }

# List all deliveries for a subscription
@app.get("/subscriptions/{subscription_id}/deliveries", response_model=List[DeliveryStatusResponse])
async def list_subscription_deliveries(
    subscription_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    # Get recent deliveries for the subscription
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.subscription_id == subscription_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    deliveries = result.scalars().all()
    
    # Get delivery attempts for each delivery
    result = []
    for delivery in deliveries:
        attempts_result = await db.execute(
            select(DeliveryAttempt)
            .where(DeliveryAttempt.delivery_id == delivery.id)
            .order_by(DeliveryAttempt.attempt_number)
        )
        attempts = attempts_result.scalars().all()
        
        # Format response for each delivery
        result.append({
            "delivery_id": delivery.id,
            "status": delivery.status.value,
            "attempt_count": delivery.attempt_count,
            "last_attempt_at": delivery.last_attempt_at,
            "next_retry_at": delivery.next_retry_at,
            "attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "status_code": attempt.status_code,
                    "response_body": attempt.response_body,
                    "error_message": attempt.error_message,
                    "created_at": attempt.created_at
                }
                for attempt in attempts
            ]
        })
    
    return result 