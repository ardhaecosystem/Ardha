"""
GitHub Webhook models for event processing.

This module defines the GitHubWebhookDelivery model for tracking webhook
events from GitHub, including processing status and error handling.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.github_integration import GitHubIntegration


class GitHubWebhookDelivery(Base, BaseModel):
    """
    GitHub Webhook Delivery model for tracking webhook events.

    Tracks complete webhook delivery information including:
    - Event metadata (delivery ID, event type, action)
    - Payload and headers for replay capability
    - Processing status and error tracking
    - Verification information
    - Related entity linking (PR, commit, etc.)

    Attributes:
        github_integration_id: Foreign key to GitHub integration
        delivery_id: GitHub's delivery UUID
        event_type: Type of webhook event (e.g., 'pull_request', 'push')
        action: Event action (e.g., 'opened', 'closed', 'synchronize')
        payload: Full webhook payload JSON
        payload_size: Payload size in bytes
        headers: Request headers as JSON
        status: Processing status (pending, processing, processed, failed, ignored)
        processed_at: Processing timestamp
        error_message: Processing error message
        retry_count: Number of processing retry attempts
        signature: X-Hub-Signature-256 header value
        signature_verified: Whether signature was verified
        pr_number: Related PR number (if event related to PR)
        commit_sha: Related commit SHA (if event related to commit)
        related_entity_type: Type of related entity
        related_entity_id: Ardha entity ID
        received_at: When webhook was received
        processed_by: Worker/service that processed it
    """

    __tablename__ = "github_webhook_deliveries"

    # ============= Identity =============

    github_integration_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("github_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to GitHub integration",
    )

    delivery_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="GitHub's delivery UUID",
    )

    # ============= Event Information =============

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of webhook event (e.g., 'pull_request', 'push', 'check_suite')",
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Event action (e.g., 'opened', 'closed', 'synchronize')",
    )

    # ============= Payload Information =============

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Full webhook payload for replay and debugging",
    )

    payload_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Payload size in bytes",
    )

    headers: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Request headers as JSON",
    )

    # ============= Processing Status =============

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Processing status: pending, processing, processed, failed, ignored",
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When webhook was processed",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Processing error message if status is 'failed'",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of processing retry attempts",
    )

    # ============= Verification =============

    signature: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="X-Hub-Signature-256 header value",
    )

    signature_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether signature was successfully verified",
    )

    # ============= Related Entities =============

    pr_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Related PR number (if event related to PR)",
    )

    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
        comment="Related commit SHA (if event related to commit)",
    )

    related_entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of related entity: pull_request, commit, check_run, review",
    )

    related_entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Ardha entity UUID (if mapped to internal entity)",
    )

    # ============= Audit Fields =============

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When webhook was received",
    )

    processed_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Worker/service that processed this webhook",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    github_integration: Mapped["GitHubIntegration"] = relationship(
        "GitHubIntegration",
        back_populates="webhook_deliveries",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Unique constraint: GitHub guarantees delivery_id uniqueness
        UniqueConstraint("delivery_id", name="uq_webhook_delivery_id"),
        # Index for integration queries
        Index("ix_webhook_integration", "github_integration_id"),
        # Index for event type queries
        Index("ix_webhook_event_type", "event_type"),
        # Index for status queries
        Index("ix_webhook_status", "status"),
        # Index for chronological queries
        Index("ix_webhook_received", "received_at", postgresql_ops={"received_at": "DESC"}),
        # Index for PR-related webhooks
        Index("ix_webhook_pr_number", "pr_number"),
        # Index for commit-related webhooks
        Index("ix_webhook_commit_sha", "commit_sha"),
        # Index for entity type queries
        Index("ix_webhook_entity_type", "related_entity_type"),
        # Check constraints
        CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed', 'ignored')",
            name="ck_webhook_status",
        ),
        CheckConstraint(
            "related_entity_type IS NULL OR related_entity_type IN "
            "('pull_request', 'commit', 'check_run', 'review')",
            name="ck_webhook_entity_type",
        ),
        CheckConstraint(
            "payload_size >= 0",
            name="ck_webhook_payload_size",
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="ck_webhook_retry_count",
        ),
    )

    # ============= Methods =============

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<GitHubWebhookDelivery(id={self.id}, "
            f"event_type='{self.event_type}', "
            f"action='{self.action}', "
            f"status='{self.status}')>"
        )

    def to_dict(self) -> dict:
        """
        Serialize webhook delivery to dictionary.

        Excludes full payload for performance (use payload only for debugging).

        Returns:
            Dictionary with webhook delivery attributes
        """
        return {
            "id": str(self.id),
            "github_integration_id": str(self.github_integration_id),
            "delivery_id": self.delivery_id,
            "event_type": self.event_type,
            "action": self.action,
            "payload_size": self.payload_size,
            "status": self.status,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "signature_verified": self.signature_verified,
            "pr_number": self.pr_number,
            "commit_sha": self.commit_sha,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": str(self.related_entity_id) if self.related_entity_id else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "processed_by": self.processed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_processed(self) -> None:
        """
        Mark webhook as successfully processed.

        Updates status to 'processed' and sets processed_at timestamp.
        """
        self.status = "processed"
        self.processed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """
        Mark webhook as failed with error message.

        Args:
            error: Error message describing the failure
        """
        self.status = "failed"
        self.error_message = error
        self.processed_at = datetime.now(timezone.utc)

    def increment_retry(self) -> None:
        """
        Increment retry count for failed webhook processing.

        Updates retry_count and resets status to 'pending' for retry.
        """
        self.retry_count += 1
        self.status = "pending"
