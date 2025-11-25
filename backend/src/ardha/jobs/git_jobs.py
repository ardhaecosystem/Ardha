"""
Git-related background jobs.

This module provides Celery tasks for Git operations including
commit memory ingestion and code analysis.
"""

import logging
import re
from typing import Any, Dict
from uuid import UUID

from ardha.core.celery_app import celery_app
from ardha.core.database import async_session_factory
from ardha.repositories.git_commit import GitCommitRepository
from ardha.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="git.ingest_commit_to_memory",
    queue="memory",
    time_limit=300,  # 5 minutes
    soft_time_limit=240,  # 4 minutes
    max_retries=3,
    default_retry_delay=60,  # 1 minute
)
async def ingest_commit_to_memory(commit_id: str) -> Dict[str, Any]:
    """
    Ingest Git commit into memory system.

    Extracts:
    - Technical decisions from commit message
    - Code changes and file impact
    - Related task references
    - Author contributions

    Args:
        commit_id: UUID of commit to process

    Returns:
        Dict with ingestion results

    Raises:
        Exception: If commit not found or processing fails
    """
    logger.info(f"Starting commit memory ingestion: {commit_id}")

    try:
        async with async_session_factory() as db:
            # Get commit details
            commit_repo = GitCommitRepository(db)

            # Try to get commit with file details
            result = await commit_repo.get_commit_with_files(UUID(commit_id))

            if not result:
                # Fallback to just getting commit if no files or not found via that method
                commit = await commit_repo.get_by_id(UUID(commit_id))
                file_changes = []
            else:
                commit, file_changes_data = result
                # file_changes_data is List[Tuple["File", Dict]]
                # We need to process it
                file_changes = []
                for file_obj, change_info in file_changes_data:
                    file_changes.append(
                        {
                            "file": file_obj.path,
                            "additions": change_info.get("insertions", 0),
                            "deletions": change_info.get("deletions", 0),
                            "change_type": change_info.get("change_type"),
                        }
                    )

            if not commit:
                raise ValueError(f"Commit {commit_id} not found")

            # Extract insights from commit
            insights = {
                "technical_decisions": [],
                "code_changes": file_changes,
                "related_tasks": [],
            }

            # Parse commit message for decisions
            # Look for keywords: "decided", "chose", "implemented"
            message_lower = commit.message.lower()
            if any(
                keyword in message_lower
                for keyword in ["decided", "chose", "implemented", "fixed", "refactored"]
            ):
                insights["technical_decisions"].append(
                    {
                        "decision": commit.message,
                        "commit_hash": commit.sha,
                        "timestamp": (
                            commit.committed_at.isoformat() if commit.committed_at else None
                        ),
                    }
                )

            # Extract task references from commit message
            # Pattern: "fixes #123", "closes #456", "TAS-123"
            task_pattern = r"(?:fixes|closes|refs?)\s+#(\d+)|([A-Z]+-\d+)"
            task_refs = []
            for match in re.finditer(task_pattern, message_lower):
                # match.group(1) is #123 number, match.group(2) is TAS-123
                ref = match.group(1) or match.group(2)
                if ref:
                    task_refs.append(ref)

            insights["related_tasks"] = list(set(task_refs))

            # Create memory entry
            from ardha.repositories.memory_repository import MemoryRepository

            memory_repo = MemoryRepository(db)
            memory_service = MemoryService(memory_repository=memory_repo)

            memory = await memory_service.create_memory(
                user_id=commit.ardha_user_id
                or commit.project.owner_id,  # Fallback to project owner if no user mapped
                content=f"Git Commit: {commit.message}",
                memory_type="code_decision",
                source_type="git_commit",
                source_id=commit.id,
                metadata={
                    "commit_sha": commit.sha,
                    "files_changed_count": commit.files_changed,
                    "insights": insights,
                    "repository_id": str(commit.project_id),
                },
                importance=7,  # Technical decisions are important
                tags=["git", "commit", "technical"],
            )

            logger.info(f"Successfully ingested commit {commit_id} " f"as memory {memory.id}")

            return {
                "success": True,
                "commit_id": commit_id,
                "memory_id": str(memory.id),
                "insights": insights,
            }

    except Exception as e:
        logger.error(f"Error ingesting commit {commit_id}: {e}")
        raise
