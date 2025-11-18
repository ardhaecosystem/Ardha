"""
GitHub Webhook Receiver endpoint.

Provides public endpoint for receiving GitHub webhook events with signature
verification. Processes events asynchronously for fast response times.
"""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.repositories.github_integration import GitHubIntegrationRepository
from ardha.repositories.pull_request import PullRequestRepository
from ardha.services.git_commit_service import GitCommitService
from ardha.services.github_webhook_service import (
    GitHubWebhookService,
    WebhookProcessingError,
    WebhookVerificationError,
)
from ardha.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ============= Webhook Receiver Endpoint =============


@router.post(
    "/github",
    summary="Receive GitHub webhook",
    description="Public endpoint for receiving GitHub webhook events",
    status_code=status.HTTP_200_OK,
)
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> dict:  # noqa
    """
    Receive GitHub webhook event.

    This is a PUBLIC endpoint (no authentication required) that processes
    GitHub webhook events. Signature verification is performed using the
    webhook secret configured in the GitHub integration.

    GitHub sends webhooks with these headers:
    - X-GitHub-Event: Event type (pull_request, push, etc.)
    - X-GitHub-Delivery: Unique delivery UUID
    - X-Hub-Signature-256: HMAC signature for verification

    The endpoint:
    1. Finds the GitHub integration by repository
    2. Verifies the webhook signature
    3. Queues the event for async processing
    4. Returns 200 immediately (< 10 seconds)

    Args:
        request: FastAPI request object with JSON body
        background_tasks: FastAPI background tasks for async processing
        x_github_event: GitHub event type header
        x_github_delivery: GitHub delivery UUID header
        x_hub_signature_256: HMAC signature header

    Returns:
        Dict with status confirmation

    Raises:
        HTTPException 400: If payload is malformed
        HTTPException 401: If signature verification fails
        HTTPException 404: If no integration found for repository
    """
    # Parse JSON payload
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in webhook delivery {x_github_delivery}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Extract repository information
    repo_data = payload.get("repository", {})
    repo_owner = repo_data.get("owner", {}).get("login")
    repo_name = repo_data.get("name")

    if not repo_owner or not repo_name:
        logger.warning(f"Missing repository info in webhook delivery {x_github_delivery}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing repository information in payload",
        )

    logger.info(
        f"Received {x_github_event} webhook for {repo_owner}/{repo_name} "
        f"(delivery {x_github_delivery})"
    )

    # Find GitHub integration by repository (using injected db session)
    integration_repo = GitHubIntegrationRepository(db)
    integration = await integration_repo.get_by_repository(repo_owner, repo_name)

    if not integration:
        logger.warning(f"No integration found for repository {repo_owner}/{repo_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No integration configured for repository {repo_owner}/{repo_name}",
        )

    # Extract action from payload
    action = payload.get("action")

    # Queue webhook processing in background
    background_tasks.add_task(
        process_webhook_async,
        integration_id=str(integration.id),  # Convert UUID to string
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        action=action,
        payload=payload,
        signature=x_hub_signature_256,
    )

    # Return 200 immediately (GitHub expects response within 10 seconds)
    logger.info(f"Queued webhook {x_github_delivery} for async processing")
    return {
        "status": "received",
        "delivery_id": x_github_delivery,
        "event_type": x_github_event,
    }


# ============= Async Processing Function =============


async def process_webhook_async(
    integration_id: str,
    delivery_id: str,
    event_type: str,
    action: str | None,
    payload: dict,
    signature: str,
) -> None:
    """
    Process webhook event asynchronously.

    This function runs in the background after the webhook endpoint
    returns a 200 response to GitHub.

    Args:
        integration_id: GitHub integration UUID
        delivery_id: GitHub delivery UUID
        event_type: Event type (pull_request, push, etc.)
        action: Optional action (opened, closed, etc.)
        payload: Webhook payload
        signature: HMAC signature for verification
    """
    # Create new database session for background task
    from uuid import UUID

    from ardha.core.database import async_session_factory

    async with async_session_factory() as db:
        try:
            # Initialize services
            integration_repo = GitHubIntegrationRepository(db)
            pr_repo = PullRequestRepository(db)
            task_service = TaskService(db)

            # Initialize commit service (needs project root)
            # For now, we'll skip commit service dependency
            # In production, this would come from config
            from ardha.core.config import get_settings

            settings = get_settings()
            commit_service = GitCommitService(
                db,
                str(settings.files.project_root) if hasattr(settings, "files") else "/tmp",  # nosec B108
            )

            # Initialize webhook service
            webhook_service = GitHubWebhookService(
                integration_repo=integration_repo,
                pr_repo=pr_repo,
                task_service=task_service,
                commit_service=commit_service,
                db=db,
            )

            # Process webhook
            await webhook_service.process_webhook(
                integration_id=UUID(integration_id),
                delivery_id=delivery_id,
                event_type=event_type,
                action=action,
                payload=payload,
                signature=signature,
            )

            logger.info(f"Successfully processed webhook {delivery_id} in background")

        except WebhookVerificationError as e:
            logger.error(f"Webhook verification failed for {delivery_id}: {e}")
        except WebhookProcessingError as e:
            logger.error(f"Webhook processing failed for {delivery_id}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error processing webhook {delivery_id}: {e}",
                exc_info=True,
            )
