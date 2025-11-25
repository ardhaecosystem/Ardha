"""
GitHub Integration repository for data access abstraction.

This module provides the repository pattern implementation for GitHubIntegration
and webhook delivery models, handling all database operations related to GitHub
repository connections and webhook event tracking.
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.github_integration import GitHubIntegration
from ardha.models.github_webhook import GitHubWebhookDelivery

logger = logging.getLogger(__name__)


class GitHubIntegrationRepository:
    """
    Repository for GitHubIntegration model database operations.

    Provides data access methods for GitHub integration operations including
    CRUD operations, connection status management, statistics tracking, and
    webhook delivery management. Follows the repository pattern to abstract
    database implementation details from business logic.

    Attributes:
        session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the GitHubIntegrationRepository with a database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(self, integration: GitHubIntegration) -> GitHubIntegration:
        """
        Create a new GitHub integration.

        Handles unique constraint (one integration per project).

        Args:
            integration: GitHubIntegration instance to create

        Returns:
            Created GitHubIntegration with generated ID

        Raises:
            IntegrityError: If project already has integration
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add(integration)
            await self.session.flush()
            await self.session.refresh(integration)
            logger.info(
                f"Created GitHub integration {integration.id} for project {integration.project_id}"
            )
            return integration
        except IntegrityError:
            logger.warning(f"Project {integration.project_id} already has a GitHub integration")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating GitHub integration: {e}", exc_info=True)
            raise

    async def get_by_id(self, integration_id: UUID) -> GitHubIntegration | None:
        """
        Fetch a GitHub integration by its UUID.

        Eagerly loads project and pull_requests relationships.

        Args:
            integration_id: UUID of the integration to fetch

        Returns:
            GitHubIntegration object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(GitHubIntegration)
                .where(GitHubIntegration.id == integration_id)
                .options(
                    selectinload(GitHubIntegration.project),
                    selectinload(GitHubIntegration.pull_requests),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching GitHub integration {integration_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_by_project(self, project_id: UUID) -> GitHubIntegration | None:
        """
        Fetch GitHub integration for a specific project.

        Args:
            project_id: UUID of the project

        Returns:
            GitHubIntegration object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitHubIntegration).where(GitHubIntegration.project_id == project_id)
            result = await self.session.execute(stmt)
            integration = result.scalar_one_or_none()
            if integration:
                logger.info(f"Found GitHub integration for project {project_id}")
            return integration
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching GitHub integration for project {project_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_by_repository(self, owner: str, name: str) -> GitHubIntegration | None:
        """
        Fetch GitHub integration by repository owner and name.

        Args:
            owner: GitHub username or organization name
            name: Repository name

        Returns:
            GitHubIntegration object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitHubIntegration).where(
                GitHubIntegration.repository_owner == owner,
                GitHubIntegration.repository_name == name,
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching GitHub integration for {owner}/{name}: {e}",
                exc_info=True,
            )
            raise

    async def list_active(self) -> list[GitHubIntegration]:
        """
        Get all active GitHub integrations.

        Filters by is_active=True and connection_status='connected'.

        Returns:
            List of active GitHubIntegration objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitHubIntegration).where(
                GitHubIntegration.is_active.is_(True),
                GitHubIntegration.connection_status == "connected",
            )
            result = await self.session.execute(stmt)
            integrations = list(result.scalars().all())
            logger.info(f"Found {len(integrations)} active GitHub integrations")
            return integrations
        except SQLAlchemyError as e:
            logger.error(f"Error listing active integrations: {e}", exc_info=True)
            raise

    async def update(
        self,
        integration_id: UUID,
        update_data: dict[str, Any],
    ) -> GitHubIntegration | None:
        """
        Update GitHub integration fields.

        Updates specified fields and automatically sets updated_at timestamp.

        Args:
            integration_id: UUID of integration to update
            update_data: Dictionary of fields to update

        Returns:
            Updated GitHubIntegration if found, None otherwise

        Raises:
            IntegrityError: If update violates unique constraints
            SQLAlchemyError: If database operation fails
        """
        try:
            integration = await self.get_by_id(integration_id)
            if not integration:
                logger.warning(f"Cannot update: GitHub integration {integration_id} not found")
                return None

            # Update only provided fields
            for key, value in update_data.items():
                if hasattr(integration, key):
                    setattr(integration, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")

            await self.session.flush()
            await self.session.refresh(integration)
            logger.info(f"Updated GitHub integration {integration_id}")
            return integration
        except IntegrityError as e:
            logger.warning(f"Integrity error updating integration {integration_id}: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating integration {integration_id}: {e}", exc_info=True)
            raise

    async def update_connection_status(
        self,
        integration_id: UUID,
        status: str,
        error_message: str | None = None,
    ) -> GitHubIntegration | None:
        """
        Update connection status of a GitHub integration.

        Updates connection_status, sets sync_error if provided, and updates
        last_sync_at if status is 'connected'.

        Args:
            integration_id: UUID of integration to update
            status: New connection status (connected, disconnected, error, unauthorized)
            error_message: Optional error message for error status

        Returns:
            Updated GitHubIntegration if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            integration = await self.get_by_id(integration_id)
            if not integration:
                logger.warning(f"Cannot update status: integration {integration_id} not found")
                return None

            integration.connection_status = status
            integration.sync_error = error_message

            # Update last_sync_at if successfully connected
            if status == "connected":
                from datetime import timezone

                integration.last_sync_at = datetime.now(timezone.utc)

            await self.session.flush()
            await self.session.refresh(integration)
            logger.info(f"Updated connection status for integration {integration_id} to {status}")
            return integration
        except SQLAlchemyError as e:
            logger.error(
                f"Error updating connection status for {integration_id}: {e}",
                exc_info=True,
            )
            raise

    async def update_statistics(
        self,
        integration_id: UUID,
        total_prs: int | None = None,
        merged_prs: int | None = None,
        closed_prs: int | None = None,
        webhook_events_received: int | None = None,
    ) -> GitHubIntegration | None:
        """
        Update statistics fields for a GitHub integration.

        Increments statistics if values are provided.

        Args:
            integration_id: UUID of integration to update
            total_prs: Total PRs count to increment
            merged_prs: Merged PRs count to increment
            closed_prs: Closed PRs count to increment
            webhook_events_received: Webhook events count to increment

        Returns:
            Updated GitHubIntegration if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            integration = await self.get_by_id(integration_id)
            if not integration:
                logger.warning(f"Cannot update stats: integration {integration_id} not found")
                return None

            # Increment statistics if provided
            if total_prs is not None:
                integration.total_prs += total_prs
            if merged_prs is not None:
                integration.merged_prs += merged_prs
            if closed_prs is not None:
                integration.closed_prs += closed_prs
            if webhook_events_received is not None:
                integration.webhook_events_received += webhook_events_received

            await self.session.flush()
            await self.session.refresh(integration)
            logger.info(f"Updated statistics for integration {integration_id}")
            return integration
        except SQLAlchemyError as e:
            logger.error(f"Error updating statistics for {integration_id}: {e}", exc_info=True)
            raise

    async def increment_webhook_count(self, integration_id: UUID) -> None:
        """
        Increment webhook_events_received counter by 1.

        Efficient update without full object fetch.

        Args:
            integration_id: UUID of integration to update

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(GitHubIntegration).where(GitHubIntegration.id == integration_id)
            result = await self.session.execute(stmt)
            integration = result.scalar_one_or_none()

            if integration:
                integration.webhook_events_received += 1
                await self.session.flush()
                logger.info(f"Incremented webhook count for integration {integration_id}")
        except SQLAlchemyError as e:
            logger.error(
                f"Error incrementing webhook count for {integration_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete(self, integration_id: UUID) -> bool:
        """
        Delete a GitHub integration (cascade to PRs and webhooks).

        Permanently removes integration and all associated data.

        Args:
            integration_id: UUID of integration to delete

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            integration = await self.get_by_id(integration_id)
            if not integration:
                logger.warning(f"Cannot delete: integration {integration_id} not found")
                return False

            await self.session.delete(integration)
            await self.session.flush()
            logger.info(f"Deleted GitHub integration {integration_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting integration {integration_id}: {e}", exc_info=True)
            raise

    async def verify_webhook_signature(
        self, integration_id: UUID, payload: str, signature: str
    ) -> bool:
        """
        Verify webhook signature using integration's webhook_secret.

        Uses HMAC-SHA256 to verify webhook authenticity.

        Args:
            integration_id: UUID of the integration
            payload: Raw webhook payload string
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid, False otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            integration = await self.get_by_id(integration_id)
            if not integration or not integration.webhook_secret:
                logger.warning(
                    f"Cannot verify signature: integration {integration_id} "
                    f"not found or missing webhook_secret"
                )
                return False

            # GitHub sends signature as 'sha256=<hash>'
            if not signature.startswith("sha256="):
                return False

            expected_signature = signature[7:]  # Remove 'sha256=' prefix

            # Compute HMAC-SHA256
            mac = hmac.new(
                integration.webhook_secret.encode("utf-8"),
                msg=payload.encode("utf-8"),
                digestmod=hashlib.sha256,
            )
            computed_signature = mac.hexdigest()

            # Constant-time comparison
            is_valid = hmac.compare_digest(computed_signature, expected_signature)
            logger.info(f"Webhook signature verification for {integration_id}: {is_valid}")
            return is_valid
        except SQLAlchemyError:
            logger.error(
                f"Error verifying webhook signature for {integration_id}",
                exc_info=True,
            )
            raise

    async def count_by_status(self, status: str) -> int:
        """
        Count GitHub integrations by connection status.

        Args:
            status: Connection status to count (connected, disconnected, error, unauthorized)

        Returns:
            Count of integrations with the specified status

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(func.count())
                .select_from(GitHubIntegration)
                .where(GitHubIntegration.connection_status == status)
            )
            result = await self.session.execute(stmt)
            count = result.scalar() or 0
            logger.info(f"Found {count} integrations with status '{status}'")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error counting integrations by status: {e}", exc_info=True)
            raise

    async def list_needing_sync(self, since: datetime) -> list[GitHubIntegration]:
        """
        Get integrations that haven't synced since specified datetime.

        Filters by is_active=True and last_sync_at before the specified datetime.

        Args:
            since: Datetime threshold for last sync

        Returns:
            List of GitHubIntegration objects needing sync

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitHubIntegration).where(
                GitHubIntegration.is_active.is_(True),
                (GitHubIntegration.last_sync_at.is_(None))
                | (GitHubIntegration.last_sync_at < since),
            )
            result = await self.session.execute(stmt)
            integrations = list(result.scalars().all())
            logger.info(f"Found {len(integrations)} integrations needing sync since {since}")
            return integrations
        except SQLAlchemyError as e:
            logger.error(f"Error listing integrations needing sync: {e}", exc_info=True)
            raise

    async def record_webhook_delivery(
        self,
        integration_id: UUID,
        delivery: GitHubWebhookDelivery,
    ) -> GitHubWebhookDelivery:
        """
        Create webhook delivery record and increment webhook count.

        Args:
            integration_id: UUID of the integration
            delivery: GitHubWebhookDelivery instance to create

        Returns:
            Created GitHubWebhookDelivery with generated ID

        Raises:
            IntegrityError: If delivery_id already exists
            SQLAlchemyError: If database operation fails
        """
        try:
            # Set integration_id if not already set
            delivery.github_integration_id = integration_id

            # Create delivery record
            self.session.add(delivery)
            await self.session.flush()
            await self.session.refresh(delivery)

            # Increment webhook count
            await self.increment_webhook_count(integration_id)

            logger.info(
                f"Recorded webhook delivery {delivery.delivery_id} "
                f"for integration {integration_id}"
            )
            return delivery
        except IntegrityError:
            logger.warning(f"Webhook delivery {delivery.delivery_id} already exists")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error recording webhook delivery: {e}", exc_info=True)
            raise

    async def get_webhook_deliveries(
        self,
        integration_id: UUID,
        event_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[GitHubWebhookDelivery]:
        """
        Get webhook deliveries for a GitHub integration.

        Args:
            integration_id: UUID of the integration
            event_type: Optional filter by event type
            status: Optional filter by processing status
            limit: Maximum number of results (default 50)

        Returns:
            List of GitHubWebhookDelivery objects ordered by received_at DESC

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitHubWebhookDelivery).where(
                GitHubWebhookDelivery.github_integration_id == integration_id
            )

            # Apply optional filters
            if event_type:
                stmt = stmt.where(GitHubWebhookDelivery.event_type == event_type)
            if status:
                stmt = stmt.where(GitHubWebhookDelivery.status == status)

            # Order by received_at DESC and limit
            stmt = stmt.order_by(GitHubWebhookDelivery.received_at.desc()).limit(limit)

            result = await self.session.execute(stmt)
            deliveries = list(result.scalars().all())
            logger.info(
                f"Found {len(deliveries)} webhook deliveries for integration {integration_id}"
            )
            return deliveries
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching webhook deliveries for {integration_id}: {e}",
                exc_info=True,
            )
            raise
