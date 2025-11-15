"""
Memory ingestion service for Qdrant vector database.

This module provides functionality to ingest and retrieve
workflow memories, conversations, and artifacts from Qdrant.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.qdrant import get_qdrant_service
from .state import WorkflowState

logger = logging.getLogger(__name__)


class MemoryIngestionService:
    """
    Service for ingesting and retrieving workflow memories.

    Handles storage and retrieval of:
    - Workflow execution results
    - AI conversation history
    - Generated artifacts and code
    - User preferences and context
    """

    def __init__(self) -> None:
        """Initialize memory ingestion service."""
        self.logger = logger
        self.qdrant_service = get_qdrant_service()

        # Collection names for different memory types
        self.collections = {
            "workflows": "workflow_memories",
            "conversations": "conversation_history",
            "artifacts": "generated_artifacts",
            "context": "user_context",
        }

        self.logger.info("Memory ingestion service initialized")

    async def ingest_workflow_execution(
        self,
        workflow_state: WorkflowState,
    ) -> bool:
        """
        Ingest workflow execution into memory.

        Args:
            workflow_state: Completed workflow state

        Returns:
            True if ingestion successful
        """
        try:
            # Prepare workflow memory document
            memory_doc = {
                "id": str(workflow_state.execution_id),
                "workflow_id": str(workflow_state.workflow_id),
                "workflow_type": workflow_state.workflow_type.value,
                "user_id": str(workflow_state.user_id),
                "project_id": str(workflow_state.project_id) if workflow_state.project_id else None,
                "initial_request": workflow_state.initial_request,
                "context": workflow_state.context,
                "parameters": workflow_state.parameters,
                "status": workflow_state.status.value,
                "results": workflow_state.results,
                "artifacts": workflow_state.artifacts,
                "metadata": workflow_state.metadata,
                "ai_calls": workflow_state.ai_calls,
                "token_usage": workflow_state.token_usage,
                "total_cost": workflow_state.total_cost,
                "errors": workflow_state.errors,
                "retry_count": workflow_state.retry_count,
                "created_at": workflow_state.created_at,
                "started_at": workflow_state.started_at,
                "completed_at": workflow_state.completed_at,
                "last_activity": workflow_state.last_activity,
                "ingested_at": workflow_state._get_timestamp(),
            }

            # Generate embedding for search
            text_content = self._extract_text_content(memory_doc)

            # Store in Qdrant
            success = await self.qdrant_service.upsert_vectors(
                collection_type=self.collections["workflows"],
                points=[
                    {
                        "id": str(workflow_state.execution_id),
                        "text": text_content,
                        "metadata": memory_doc,
                    }
                ],
            )

            if success:
                self.logger.info(f"Ingested workflow execution: {workflow_state.execution_id}")
                return True
            else:
                self.logger.error(
                    f"Failed to ingest workflow execution: {workflow_state.execution_id}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error ingesting workflow execution: {e}")
            return False

    async def ingest_conversation(
        self,
        conversation_id: str,
        user_id: UUID,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ingest conversation into memory.

        Args:
            conversation_id: Unique conversation identifier
            user_id: User who participated
            messages: List of conversation messages
            metadata: Additional conversation metadata

        Returns:
            True if ingestion successful
        """
        try:
            # Prepare conversation memory document
            memory_doc = {
                "id": conversation_id,
                "user_id": str(user_id),
                "messages": messages,
                "metadata": metadata or {},
                "message_count": len(messages),
                "ingested_at": self._get_timestamp(),
            }

            # Generate embedding from conversation summary
            text_content = self._extract_conversation_text(messages)

            # Store in Qdrant
            success = await self.qdrant_service.upsert_vectors(
                collection_type=self.collections["conversations"],
                points=[
                    {
                        "id": conversation_id,
                        "text": text_content,
                        "metadata": memory_doc,
                    }
                ],
            )

            if success:
                self.logger.info(f"Ingested conversation: {conversation_id}")
                return True
            else:
                self.logger.error(f"Failed to ingest conversation: {conversation_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error ingesting conversation: {e}")
            return False

    async def ingest_artifact(
        self,
        artifact_id: str,
        workflow_execution_id: UUID,
        artifact_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ingest artifact into memory.

        Args:
            artifact_id: Unique artifact identifier
            workflow_execution_id: Associated workflow execution
            artifact_type: Type of artifact (code, document, image, etc.)
            content: Artifact content
            metadata: Additional artifact metadata

        Returns:
            True if ingestion successful
        """
        try:
            # Prepare artifact memory document
            memory_doc = {
                "id": artifact_id,
                "workflow_execution_id": str(workflow_execution_id),
                "artifact_type": artifact_type,
                "content": content,
                "metadata": metadata or {},
                "ingested_at": self._get_timestamp(),
            }

            # Generate embedding from content description
            text_content = self._extract_artifact_text(content, metadata)

            # Store in Qdrant
            success = await self.qdrant_service.upsert_vectors(
                collection_type=self.collections["artifacts"],
                points=[
                    {
                        "id": artifact_id,
                        "text": text_content,
                        "metadata": memory_doc,
                    }
                ],
            )

            if success:
                self.logger.info(f"Ingested artifact: {artifact_id}")
                return True
            else:
                self.logger.error(f"Failed to ingest artifact: {artifact_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error ingesting artifact: {e}")
            return False

    async def search_workflows(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        workflow_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search workflow executions by semantic similarity.

        Args:
            query: Search query
            user_id: Filter by user
            project_id: Filter by project
            workflow_type: Filter by workflow type
            limit: Maximum results to return

        Returns:
            List of matching workflow executions
        """
        try:

            # Build filter conditions
            filter_conditions = {}
            if user_id:
                filter_conditions["user_id"] = str(user_id)
            if project_id:
                filter_conditions["project_id"] = str(project_id)
            if workflow_type:
                filter_conditions["workflow_type"] = workflow_type

            # Search in Qdrant
            results = await self.qdrant_service.search_similar(
                collection_type=self.collections["workflows"],
                query_text=query,
                limit=limit,
                filter_conditions=filter_conditions if filter_conditions else None,
            )

            # Extract payloads from results
            workflows = (
                results if results else []
            )  # Results are already dictionaries from search_similar

            self.logger.info(f"Found {len(workflows)} matching workflows for query: {query}")
            return workflows

        except Exception as e:
            self.logger.error(f"Error searching workflows: {e}")
            return []

    async def search_conversations(
        self,
        query: str,
        user_id: UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by semantic similarity.

        Args:
            query: Search query
            user_id: Filter by user
            limit: Maximum results to return

        Returns:
            List of matching conversations
        """
        try:

            # Search in Qdrant
            results = await self.qdrant_service.search_similar(
                collection_type=self.collections["conversations"],
                query_text=query,
                limit=limit,
                filter_conditions={"user_id": str(user_id)},
            )

            # Extract payloads from results
            conversations = (
                results if results else []
            )  # Results are already dictionaries from search_similar

            self.logger.info(
                f"Found {len(conversations)} matching conversations for query: {query}"
            )
            return conversations

        except Exception as e:
            self.logger.error(f"Error searching conversations: {e}")
            return []

    async def search_artifacts(
        self,
        query: str,
        workflow_execution_id: Optional[UUID] = None,
        artifact_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search artifacts by semantic similarity.

        Args:
            query: Search query
            workflow_execution_id: Filter by workflow execution
            artifact_type: Filter by artifact type
            limit: Maximum results to return

        Returns:
            List of matching artifacts
        """
        try:

            # Build filter conditions
            filter_conditions = {}
            if workflow_execution_id:
                filter_conditions["workflow_execution_id"] = str(workflow_execution_id)
            if artifact_type:
                filter_conditions["artifact_type"] = artifact_type

            # Search in Qdrant
            results = await self.qdrant_service.search_similar(
                collection_type=self.collections["artifacts"],
                query_text=query,
                limit=limit,
                filter_conditions=filter_conditions if filter_conditions else None,
            )

            # Extract payloads from results
            artifacts = (
                results if results else []
            )  # Results are already dictionaries from search_similar

            self.logger.info(f"Found {len(artifacts)} matching artifacts for query: {query}")
            return artifacts

        except Exception as e:
            self.logger.error(f"Error searching artifacts: {e}")
            return []

    async def get_workflow_context(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get relevant context for user/project.

        Args:
            user_id: User identifier
            project_id: Optional project identifier

        Returns:
            Context dictionary with relevant information
        """
        try:
            # Search for recent workflows and conversations
            context_query = (
                f"user context preferences project {project_id}"
                if project_id
                else "user context preferences"
            )

            # Get recent workflows
            recent_workflows = await self.search_workflows(
                query=context_query,
                user_id=user_id,
                project_id=project_id,
                limit=5,
            )

            # Get recent conversations
            recent_conversations = await self.search_conversations(
                query=context_query,
                user_id=user_id,
                limit=3,
            )

            # Build context
            context = {
                "user_id": str(user_id),
                "project_id": str(project_id) if project_id else None,
                "recent_workflows": recent_workflows,
                "recent_conversations": recent_conversations,
                "workflow_patterns": self._extract_workflow_patterns(recent_workflows),
                "preferences": await self._get_user_preferences(user_id),
            }

            self.logger.info(f"Retrieved context for user {user_id}")
            return context

        except Exception as e:
            self.logger.error(f"Error getting workflow context: {e}")
            return {}

    def _extract_text_content(self, document: Dict[str, Any]) -> str:
        """Extract searchable text content from document."""
        text_parts = []

        # Add key fields
        if "initial_request" in document:
            text_parts.append(document["initial_request"])
        if "results" in document and document["results"]:
            text_parts.append(str(document["results"]))
        if "status" in document:
            text_parts.append(document["status"])

        # Add metadata text
        if "metadata" in document and document["metadata"]:
            text_parts.append(str(document["metadata"]))

        return " ".join(text_parts)

    def _extract_conversation_text(self, messages: List[Dict[str, Any]]) -> str:
        """Extract searchable text from conversation messages."""
        text_parts = []

        for message in messages:
            if "content" in message:
                text_parts.append(message["content"])
            if "role" in message:
                text_parts.append(message["role"])

        return " ".join(text_parts)

    def _extract_artifact_text(self, content: Any, metadata: Optional[Dict[str, Any]]) -> str:
        """Extract searchable text from artifact."""
        text_parts = []

        # Add content as text
        if isinstance(content, str):
            text_parts.append(content)
        else:
            text_parts.append(str(content))

        # Add metadata
        if metadata:
            text_parts.append(str(metadata))

        return " ".join(text_parts)

    def _extract_workflow_patterns(self, workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common patterns from workflow executions."""
        common_workflow_types: Dict[str, int] = {}
        patterns = {
            "common_workflow_types": common_workflow_types,
            "average_duration": 0,
            "success_rate": 0,
            "common_errors": [],
        }

        if not workflows:
            return patterns

        # Count workflow types
        for workflow in workflows:
            workflow_type = workflow.get("workflow_type", "unknown")
            common_workflow_types[workflow_type] = common_workflow_types.get(workflow_type, 0) + 1

        # Calculate success rate
        successful = sum(1 for w in workflows if w.get("status") == "completed")
        patterns["success_rate"] = successful / len(workflows) if workflows else 0

        # Extract common errors
        all_errors = []
        for workflow in workflows:
            errors = workflow.get("errors", [])
            all_errors.extend([e.get("error", "") for e in errors])

        # Count error frequency
        error_counts: Dict[str, int] = {}
        for error in all_errors:
            if error:
                error_counts[error] = error_counts.get(error, 0) + 1

        # Get top 5 errors
        patterns["common_errors"] = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return patterns

    async def _get_user_preferences(self, user_id: UUID) -> Dict[str, Any]:
        """Get user preferences from memory (placeholder for now)."""
        # In a real implementation, this would search user context
        # For now, return default preferences
        return {
            "preferred_workflow_types": ["implement", "research"],
            "notification_settings": {
                "email": True,
                "push": False,
            },
            "ui_preferences": {
                "theme": "dark",
                "language": "en",
            },
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"


# Global memory service instance
_memory_service: Optional[MemoryIngestionService] = None


def get_memory_service() -> MemoryIngestionService:
    """
    Get cached memory ingestion service instance.

    Returns:
        MemoryIngestionService instance
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryIngestionService()
    return _memory_service
