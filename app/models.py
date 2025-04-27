# Import required SQLAlchemy components
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index, text, event
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

# Create base class for declarative models
Base = declarative_base()

# Define delivery status enum
class DeliveryStatus(enum.Enum):
    PENDING = "pending"    # Initial state when webhook is received
    SUCCESS = "success"    # Webhook delivered successfully
    FAILED = "failed"      # Webhook delivery failed after all retries
    RETRYING = "retrying"  # Webhook delivery failed, waiting for retry

# Subscription model for webhook endpoints
class Subscription(Base):
    __tablename__ = "subscriptions"

    # Primary key and basic fields
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)           # Subscription name
    target_url = Column(String, nullable=False)     # Webhook endpoint URL
    secret_key = Column(String, nullable=True)      # Secret key for webhook verification
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Creation timestamp
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())        # Last update timestamp
    search_vector = Column(TSVECTOR)                # Full-text search vector

    # Define relationship with deliveries
    deliveries = relationship("WebhookDelivery", back_populates="subscription", cascade="all, delete-orphan")

    # Define PostgreSQL-specific indexes
    __table_args__ = (
        # Index for case-insensitive name search
        Index('ix_subscriptions_name', text('lower(name)')),
        # Index for created_at for efficient time-based queries
        Index('ix_subscriptions_created_at', 'created_at'),
        # GIN index for full-text search
        Index('ix_subscriptions_search_vector', 'search_vector', postgresql_using='gin'),
    )

# Event listener to update search vector before insert/update
@event.listens_for(Subscription, 'before_insert')
@event.listens_for(Subscription, 'before_update')
def update_search_vector(mapper, connection, target):
    target.search_vector = func.to_tsvector('english', target.name)

# Webhook delivery model
class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    # Primary key and basic fields
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"))  # Related subscription
    payload = Column(JSONB, nullable=False)         # Webhook payload data
    status = Column(Enum(DeliveryStatus, name='deliverystatus'), default=DeliveryStatus.PENDING)  # Delivery status
    attempt_count = Column(Integer, default=0)      # Number of delivery attempts
    last_attempt_at = Column(DateTime(timezone=True))  # Timestamp of last attempt
    next_retry_at = Column(DateTime(timezone=True))    # Timestamp for next retry
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Creation timestamp
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())        # Last update timestamp
    payload_search = Column(TSVECTOR)               # Full-text search vector for payload

    # Define relationships
    subscription = relationship("Subscription", back_populates="deliveries")
    attempts = relationship("DeliveryAttempt", back_populates="delivery", cascade="all, delete-orphan")

    # Define PostgreSQL-specific indexes
    __table_args__ = (
        # Index for status filtering
        Index('ix_webhook_deliveries_status', 'status'),
        # Index for created_at for efficient time-based queries
        Index('ix_webhook_deliveries_created_at', 'created_at'),
        # Index for subscription_id for efficient filtering
        Index('ix_webhook_deliveries_subscription_id', 'subscription_id'),
        # Index for next_retry_at for efficient retry scheduling
        Index('ix_webhook_deliveries_next_retry_at', 'next_retry_at'),
        # GIN index for full-text search on payload
        Index('ix_webhook_deliveries_payload_search', 'payload_search', postgresql_using='gin'),
    )

# Event listener to update payload search vector before insert/update
@event.listens_for(WebhookDelivery, 'before_insert')
@event.listens_for(WebhookDelivery, 'before_update')
def update_payload_search(mapper, connection, target):
    target.payload_search = func.to_tsvector('english', func.jsonb_path_query_array(target.payload, '$.*'))

# Delivery attempt model
class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    # Primary key and basic fields
    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("webhook_deliveries.id", ondelete="CASCADE"))  # Related delivery
    attempt_number = Column(Integer, nullable=False)  # Sequential attempt number
    status_code = Column(Integer, nullable=True)      # HTTP status code from attempt
    response_body = Column(String, nullable=True)     # Response body from attempt
    error_message = Column(String, nullable=True)     # Error message if attempt failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Creation timestamp

    # Define relationship with delivery
    delivery = relationship("WebhookDelivery", back_populates="attempts")

    # Define PostgreSQL-specific indexes
    __table_args__ = (
        # Index for delivery_id for efficient filtering
        Index('ix_delivery_attempts_delivery_id', 'delivery_id'),
        # Index for created_at for efficient time-based queries
        Index('ix_delivery_attempts_created_at', 'created_at'),
        # Index for status_code for efficient filtering
        Index('ix_delivery_attempts_status_code', 'status_code'),
    ) 