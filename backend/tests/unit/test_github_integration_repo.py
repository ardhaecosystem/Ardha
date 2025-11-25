"""
Unit tests for GitHubIntegrationRepository.

Tests cover all 15 repository methods including CRUD operations,
connection status management, statistics tracking, and webhook handling.
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from ardha.models.github_integration import GitHubIntegration
from ardha.models.github_webhook import GitHubWebhookDelivery
from ardha.repositories.github_integration import GitHubIntegrationRepository


@pytest.mark.asyncio
class TestGitHubIntegrationRepository:
    """Test suite for GitHubIntegrationRepository."""

    async def test_create_integration_success(self, test_db, sample_user, sample_project):
        """Test successful GitHub integration creation."""
        repo = GitHubIntegrationRepository(test_db)

        integration = GitHubIntegration(
            project_id=sample_project.id,
            repository_owner="octocat",
            repository_name="hello-world",
            repository_url="https://github.com/octocat/hello-world",
            default_branch="main",
            access_token_encrypted="encrypted_token",
            created_by_user_id=sample_user.id,
        )

        created = await repo.create(integration)

        assert created.id is not None
        assert created.repository_owner == "octocat"
        assert created.repository_name == "hello-world"
        assert created.connection_status == "disconnected"
        assert created.is_active is True
        assert created.total_prs == 0

    async def test_create_integration_duplicate_project(self, test_db, sample_user, sample_project):
        """Test creating duplicate integration for same project fails."""
        repo = GitHubIntegrationRepository(test_db)

        # Create first integration
        integration1 = GitHubIntegration(
            project_id=sample_project.id,
            repository_owner="octocat",
            repository_name="hello-world",
            repository_url="https://github.com/octocat/hello-world",
            access_token_encrypted="token1",
            created_by_user_id=sample_user.id,
        )
        await repo.create(integration1)

        # Try to create second integration for same project
        integration2 = GitHubIntegration(
            project_id=sample_project.id,
            repository_owner="octocat",
            repository_name="another-repo",
            repository_url="https://github.com/octocat/another-repo",
            access_token_encrypted="token2",
            created_by_user_id=sample_user.id,
        )

        with pytest.raises(IntegrityError):
            await repo.create(integration2)

    async def test_get_by_id_success(self, test_db, sample_github_integration):
        """Test fetching integration by ID."""
        repo = GitHubIntegrationRepository(test_db)

        integration = await repo.get_by_id(sample_github_integration.id)

        assert integration is not None
        assert integration.id == sample_github_integration.id
        assert integration.repository_owner == sample_github_integration.repository_owner

    async def test_get_by_id_not_found(self, test_db):
        """Test fetching non-existent integration returns None."""
        repo = GitHubIntegrationRepository(test_db)

        integration = await repo.get_by_id(uuid4())

        assert integration is None

    async def test_get_by_project_success(self, test_db, sample_github_integration):
        """Test fetching integration by project ID."""
        repo = GitHubIntegrationRepository(test_db)

        integration = await repo.get_by_project(sample_github_integration.project_id)

        assert integration is not None
        assert integration.project_id == sample_github_integration.project_id

    async def test_get_by_project_not_found(self, test_db):
        """Test fetching integration for non-existent project returns None."""
        repo = GitHubIntegrationRepository(test_db)

        integration = await repo.get_by_project(uuid4())

        assert integration is None

    async def test_get_by_repository_success(self, test_db, sample_github_integration):
        """Test fetching integration by repository owner and name."""
        repo = GitHubIntegrationRepository(test_db)

        integration = await repo.get_by_repository(
            sample_github_integration.repository_owner,
            sample_github_integration.repository_name,
        )

        assert integration is not None
        assert integration.repository_owner == sample_github_integration.repository_owner
        assert integration.repository_name == sample_github_integration.repository_name

    async def test_get_by_repository_not_found(self, test_db):
        """Test fetching non-existent repository returns None."""
        repo = GitHubIntegrationRepository(test_db)

        integration = await repo.get_by_repository("nonexistent", "repo")

        assert integration is None

    async def test_list_active_success(self, test_db, sample_github_integration):
        """Test listing active integrations."""
        repo = GitHubIntegrationRepository(test_db)

        # Update to connected status
        sample_github_integration.is_active = True
        sample_github_integration.connection_status = "connected"
        await test_db.flush()

        integrations = await repo.list_active()

        assert len(integrations) >= 1
        assert all(i.is_active for i in integrations)
        assert all(i.connection_status == "connected" for i in integrations)

    async def test_list_active_excludes_disconnected(self, test_db, sample_github_integration):
        """Test list_active excludes disconnected integrations."""
        repo = GitHubIntegrationRepository(test_db)

        # Set to disconnected
        sample_github_integration.connection_status = "disconnected"
        await test_db.flush()

        integrations = await repo.list_active()

        # Should not include our disconnected integration
        assert sample_github_integration.id not in [i.id for i in integrations]

    async def test_update_success(self, test_db, sample_github_integration):
        """Test updating integration fields."""
        repo = GitHubIntegrationRepository(test_db)

        update_data = {
            "default_branch": "develop",
            "auto_create_pr": True,
            "require_review": False,
        }

        updated = await repo.update(sample_github_integration.id, update_data)

        assert updated is not None
        assert updated.default_branch == "develop"
        assert updated.auto_create_pr is True
        assert updated.require_review is False

    async def test_update_not_found(self, test_db):
        """Test updating non-existent integration returns None."""
        repo = GitHubIntegrationRepository(test_db)

        updated = await repo.update(uuid4(), {"default_branch": "main"})

        assert updated is None

    async def test_update_connection_status_connected(self, test_db, sample_github_integration):
        """Test updating connection status to connected sets last_sync_at."""
        repo = GitHubIntegrationRepository(test_db)

        before_update = datetime.now(timezone.utc)

        updated = await repo.update_connection_status(
            sample_github_integration.id,
            "connected",
        )

        assert updated is not None
        assert updated.connection_status == "connected"
        assert updated.last_sync_at is not None
        assert updated.last_sync_at >= before_update
        assert updated.sync_error is None

    async def test_update_connection_status_error(self, test_db, sample_github_integration):
        """Test updating connection status to error sets error message."""
        repo = GitHubIntegrationRepository(test_db)

        error_msg = "Authentication failed"

        updated = await repo.update_connection_status(
            sample_github_integration.id,
            "error",
            error_message=error_msg,
        )

        assert updated is not None
        assert updated.connection_status == "error"
        assert updated.sync_error == error_msg

    async def test_update_statistics_increment(self, test_db, sample_github_integration):
        """Test updating statistics increments values."""
        repo = GitHubIntegrationRepository(test_db)

        # Set initial values
        sample_github_integration.total_prs = 10
        sample_github_integration.merged_prs = 5
        sample_github_integration.closed_prs = 3
        sample_github_integration.webhook_events_received = 100
        await test_db.flush()

        updated = await repo.update_statistics(
            sample_github_integration.id,
            total_prs=2,
            merged_prs=1,
            closed_prs=1,
            webhook_events_received=5,
        )

        assert updated is not None
        assert updated.total_prs == 12
        assert updated.merged_prs == 6
        assert updated.closed_prs == 4
        assert updated.webhook_events_received == 105

    async def test_update_statistics_partial(self, test_db, sample_github_integration):
        """Test updating only some statistics fields."""
        repo = GitHubIntegrationRepository(test_db)

        sample_github_integration.total_prs = 10
        await test_db.flush()

        updated = await repo.update_statistics(
            sample_github_integration.id,
            total_prs=3,
        )

        assert updated is not None
        assert updated.total_prs == 13
        assert updated.merged_prs == 0  # Unchanged

    async def test_increment_webhook_count(self, test_db, sample_github_integration):
        """Test incrementing webhook count."""
        repo = GitHubIntegrationRepository(test_db)

        initial_count = sample_github_integration.webhook_events_received

        await repo.increment_webhook_count(sample_github_integration.id)
        await test_db.refresh(sample_github_integration)

        assert sample_github_integration.webhook_events_received == initial_count + 1

    async def test_delete_success(self, test_db, sample_github_integration):
        """Test deleting integration."""
        repo = GitHubIntegrationRepository(test_db)

        deleted = await repo.delete(sample_github_integration.id)

        assert deleted is True

        # Verify deletion
        integration = await repo.get_by_id(sample_github_integration.id)
        assert integration is None

    async def test_delete_not_found(self, test_db):
        """Test deleting non-existent integration returns False."""
        repo = GitHubIntegrationRepository(test_db)

        deleted = await repo.delete(uuid4())

        assert deleted is False

    async def test_verify_webhook_signature_valid(self, test_db, sample_github_integration):
        """Test valid webhook signature verification."""
        repo = GitHubIntegrationRepository(test_db)

        # Set webhook secret
        sample_github_integration.webhook_secret = "test_secret"
        await test_db.flush()

        # Create valid signature
        payload = '{"action":"opened"}'
        mac = hmac.new(
            b"test_secret",
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        signature = f"sha256={mac.hexdigest()}"

        is_valid = await repo.verify_webhook_signature(
            sample_github_integration.id,
            payload,
            signature,
        )

        assert is_valid is True

    async def test_verify_webhook_signature_invalid(self, test_db, sample_github_integration):
        """Test invalid webhook signature verification."""
        repo = GitHubIntegrationRepository(test_db)

        sample_github_integration.webhook_secret = "test_secret"
        await test_db.flush()

        payload = '{"action":"opened"}'
        signature = "sha256=invalid_signature"

        is_valid = await repo.verify_webhook_signature(
            sample_github_integration.id,
            payload,
            signature,
        )

        assert is_valid is False

    async def test_verify_webhook_signature_no_secret(self, test_db, sample_github_integration):
        """Test verification fails when webhook_secret is None."""
        repo = GitHubIntegrationRepository(test_db)

        # Ensure no secret
        sample_github_integration.webhook_secret = None
        await test_db.flush()

        payload = '{"action":"opened"}'
        signature = "sha256=anything"

        is_valid = await repo.verify_webhook_signature(
            sample_github_integration.id,
            payload,
            signature,
        )

        assert is_valid is False

    async def test_count_by_status(self, test_db, sample_github_integration):
        """Test counting integrations by status."""
        repo = GitHubIntegrationRepository(test_db)

        # Set status
        sample_github_integration.connection_status = "connected"
        await test_db.flush()

        count = await repo.count_by_status("connected")

        assert count >= 1

    async def test_count_by_status_zero(self, test_db):
        """Test count returns 0 when no integrations match."""
        repo = GitHubIntegrationRepository(test_db)

        count = await repo.count_by_status("unauthorized")

        # Assuming no unauthorized integrations in test data
        assert count == 0

    async def test_list_needing_sync(self, test_db, sample_github_integration):
        """Test listing integrations needing sync."""
        repo = GitHubIntegrationRepository(test_db)

        # Set integration as active but not recently synced
        sample_github_integration.is_active = True
        sample_github_integration.last_sync_at = datetime.now(timezone.utc) - timedelta(hours=2)
        await test_db.flush()

        # Query for integrations not synced in last hour
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        integrations = await repo.list_needing_sync(since)

        assert len(integrations) >= 1
        assert sample_github_integration.id in [i.id for i in integrations]

    async def test_list_needing_sync_excludes_inactive(self, test_db, sample_github_integration):
        """Test list_needing_sync excludes inactive integrations."""
        repo = GitHubIntegrationRepository(test_db)

        # Set as inactive
        sample_github_integration.is_active = False
        sample_github_integration.last_sync_at = None
        await test_db.flush()

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        integrations = await repo.list_needing_sync(since)

        # Should not include inactive integration
        assert sample_github_integration.id not in [i.id for i in integrations]

    async def test_record_webhook_delivery_success(self, test_db, sample_github_integration):
        """Test recording webhook delivery."""
        repo = GitHubIntegrationRepository(test_db)

        initial_count = sample_github_integration.webhook_events_received

        delivery = GitHubWebhookDelivery(
            github_integration_id=sample_github_integration.id,
            delivery_id="test-delivery-123",
            event_type="pull_request",
            action="opened",
            payload={"action": "opened"},
            payload_size=100,
        )

        created = await repo.record_webhook_delivery(
            sample_github_integration.id,
            delivery,
        )

        assert created.id is not None
        assert created.delivery_id == "test-delivery-123"

        # Verify webhook count incremented
        await test_db.refresh(sample_github_integration)
        assert sample_github_integration.webhook_events_received == initial_count + 1

    async def test_record_webhook_delivery_duplicate(self, test_db, sample_github_integration):
        """Test recording duplicate delivery_id fails."""
        repo = GitHubIntegrationRepository(test_db)

        delivery1 = GitHubWebhookDelivery(
            github_integration_id=sample_github_integration.id,
            delivery_id="duplicate-delivery",
            event_type="pull_request",
            action="opened",
            payload={},
            payload_size=50,
        )
        await repo.record_webhook_delivery(sample_github_integration.id, delivery1)

        delivery2 = GitHubWebhookDelivery(
            github_integration_id=sample_github_integration.id,
            delivery_id="duplicate-delivery",
            event_type="push",
            action=None,
            payload={},
            payload_size=50,
        )

        with pytest.raises(IntegrityError):
            await repo.record_webhook_delivery(sample_github_integration.id, delivery2)

    async def test_get_webhook_deliveries_all(self, test_db, sample_github_integration):
        """Test fetching all webhook deliveries."""
        repo = GitHubIntegrationRepository(test_db)

        # Create multiple deliveries
        for i in range(3):
            delivery = GitHubWebhookDelivery(
                github_integration_id=sample_github_integration.id,
                delivery_id=f"delivery-{i}",
                event_type="pull_request" if i % 2 == 0 else "push",
                action="opened",
                payload={},
                payload_size=100,
                status="processed" if i < 2 else "pending",
            )
            await repo.record_webhook_delivery(sample_github_integration.id, delivery)

        deliveries = await repo.get_webhook_deliveries(sample_github_integration.id)

        assert len(deliveries) >= 3

    async def test_get_webhook_deliveries_filtered_by_event(
        self, test_db, sample_github_integration
    ):
        """Test fetching webhook deliveries filtered by event type."""
        repo = GitHubIntegrationRepository(test_db)

        # Create deliveries with different event types
        for event_type in ["pull_request", "push", "pull_request"]:
            delivery = GitHubWebhookDelivery(
                github_integration_id=sample_github_integration.id,
                delivery_id=f"delivery-{event_type}-{uuid4()}",
                event_type=event_type,
                payload={},
                payload_size=50,
            )
            await repo.record_webhook_delivery(sample_github_integration.id, delivery)

        deliveries = await repo.get_webhook_deliveries(
            sample_github_integration.id,
            event_type="pull_request",
        )

        assert len(deliveries) == 2
        assert all(d.event_type == "pull_request" for d in deliveries)

    async def test_get_webhook_deliveries_filtered_by_status(
        self, test_db, sample_github_integration
    ):
        """Test fetching webhook deliveries filtered by status."""
        repo = GitHubIntegrationRepository(test_db)

        # Create deliveries with different statuses
        statuses = ["processed", "pending", "failed"]
        for status in statuses:
            delivery = GitHubWebhookDelivery(
                github_integration_id=sample_github_integration.id,
                delivery_id=f"delivery-{status}-{uuid4()}",
                event_type="pull_request",
                payload={},
                payload_size=50,
                status=status,
            )
            await repo.record_webhook_delivery(sample_github_integration.id, delivery)

        deliveries = await repo.get_webhook_deliveries(
            sample_github_integration.id,
            status="processed",
        )

        assert len(deliveries) == 1
        assert deliveries[0].status == "processed"

    async def test_get_webhook_deliveries_limit(self, test_db, sample_github_integration):
        """Test webhook deliveries respects limit parameter."""
        repo = GitHubIntegrationRepository(test_db)

        # Create 10 deliveries
        for i in range(10):
            delivery = GitHubWebhookDelivery(
                github_integration_id=sample_github_integration.id,
                delivery_id=f"delivery-limit-{i}",
                event_type="pull_request",
                payload={},
                payload_size=50,
            )
            await repo.record_webhook_delivery(sample_github_integration.id, delivery)

        deliveries = await repo.get_webhook_deliveries(
            sample_github_integration.id,
            limit=5,
        )

        assert len(deliveries) == 5
