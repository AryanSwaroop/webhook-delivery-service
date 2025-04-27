# Import required Pydantic components
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Define delivery status enum for schema validation
class DeliveryStatus(str, Enum):
    PENDING = "pending"    # Initial state when webhook is received
    SUCCESS = "success"    # Webhook delivered successfully
    FAILED = "failed"      # Webhook delivery failed after all retries
    RETRYING = "retrying"  # Webhook delivery failed, waiting for retry

# Base schema for subscription data
class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)  # Subscription name with length constraints
    target_url: HttpUrl                                   # Valid HTTP URL for webhook endpoint
    secret_key: str = Field(..., min_length=32, max_length=64)  # Secret key with length constraints

    # Validate secret key format
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v.isalnum():
            raise ValueError('Secret key must contain only alphanumeric characters')
        return v

# Schema for creating a new subscription
class SubscriptionCreate(SubscriptionBase):
    pass

# Schema for subscription response
class SubscriptionResponse(SubscriptionBase):
    id: int              # Subscription ID
    created_at: datetime # Creation timestamp
    updated_at: datetime # Last update timestamp

    class Config:
        orm_mode = True  # Enable ORM mode for SQLAlchemy model conversion

# Schema for webhook payload
class WebhookPayload(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=100)  # Event type with length constraints
    data: Dict[str, Any]                                        # Webhook payload data
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # Timestamp with default value

# Schema for delivery attempt response
class DeliveryAttemptResponse(BaseModel):
    attempt_number: int                    # Sequential attempt number
    status_code: Optional[int]             # HTTP status code from attempt
    response_body: Optional[str]           # Response body from attempt
    error_message: Optional[str]           # Error message if attempt failed
    created_at: datetime                   # Creation timestamp

    class Config:
        orm_mode = True  # Enable ORM mode for SQLAlchemy model conversion

# Schema for delivery status response
class DeliveryStatusResponse(BaseModel):
    delivery_id: int                       # Delivery ID
    status: DeliveryStatus                 # Current delivery status
    attempt_count: int                     # Number of delivery attempts
    last_attempt_at: Optional[datetime]    # Timestamp of last attempt
    next_retry_at: Optional[datetime]      # Timestamp for next retry
    attempts: List[DeliveryAttemptResponse]  # List of delivery attempts

    class Config:
        orm_mode = True  # Enable ORM mode for SQLAlchemy model conversion 