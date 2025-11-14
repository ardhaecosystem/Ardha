"""
Memory API routes for Ardha application.

This module provides REST API endpoints for memory operations including
creating, searching, updating, deleting, and ingesting memories with local
embedding support.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_user
from ardha.models.user import User
from ardha.repositories.memory_repository import MemoryRepository
from ardha.schemas.requests.memory import (
    ArchiveMemoryRequest,
    CreateMemoryRequest,
    IngestChatRequest,
    IngestWorkflowRequest,
    UpdateMemoryRequest,
)
from ardha.schemas.responses.memory import (
    MemoryContextResponse,
    MemoryCreationResponse,
    MemoryIngestionResponse,
    MemoryResponse,
    MemorySearchResponse,
    MemorySearchResult,
    MemoryStatsResponse,
    MemoryWithLinksResponse,
)
from ardha.services.memory_service import MemoryService, MemoryServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memories", tags=["memories"])


async def get_memory_service(db: AsyncSession = Depends(get_db)) -> MemoryService:
    """Dependency to get memory service instance."""
    memory_repository = MemoryRepository(db)
    return MemoryService(memory_repository=memory_repository)


@router.post("", response_model=MemoryCreationResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: CreateMemoryRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryCreationResponse:
    """
    Create new memory with local embedding generation.

    Embeddings are generated using all-MiniLM-L6-v2 (FREE, local model).
    """
    try:
        memory = await memory_service.create_memory(
            user_id=current_user.id,
            content=request.content,
            memory_type=request.memory_type,
            project_id=request.project_id,
            importance=request.importance,
            tags=request.tags,
            metadata=request.metadata,
            source_type="manual",
        )

        return MemoryCreationResponse(
            memory=MemoryResponse.model_validate(memory),
            embedding_generated=True,
            vector_stored=True,
            creation_time_ms=None,  # TODO: Implement timing
            collection_used=memory.qdrant_collection,
        )

    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create memory")


@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    min_score: float = Query(0.5, ge=0.0, le=1.0, description="Min similarity score"),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemorySearchResponse:
    """
    Semantic search for memories using local embeddings.

    Uses all-MiniLM-L6-v2 for query embedding (FREE, fast).
    Returns memories sorted by relevance score.
    """
    try:
        results = await memory_service.search_semantic(
            user_id=current_user.id,
            query=q,
            limit=limit,
            project_id=project_id,
            memory_type=memory_type,
            min_score=min_score,
        )

        search_results = [
            MemorySearchResult(
                memory=MemoryResponse.model_validate(memory),
                similarity_score=score,
                relevance_rank=idx + 1,
            )
            for idx, (memory, score) in enumerate(results)
        ]

        return MemorySearchResponse(
            query=q,
            total_results=len(search_results),
            results=search_results,
            search_time_ms=None,  # TODO: Implement timing
            collections_searched=memory_service._get_search_collections(memory_type),
            filters_applied={
                "memory_type": memory_type,
                "project_id": str(project_id) if project_id else None,
                "min_score": min_score,
            },
        )

    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    skip: int = Query(0, ge=0, description="Number of memories to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of memories"),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[MemoryResponse]:
    """List user's memories with optional filtering."""
    try:
        [t.strip() for t in tags.split(",")] if tags else None

        # Get memories using basic repository methods
        # TODO: Implement advanced filtering in repository
        memories = await memory_service.memory_repository.get_by_user(
            user_id=current_user.id,
            limit=limit,
        )

        return [MemoryResponse.model_validate(memory) for memory in memories]

    except Exception as e:
        logger.error(f"Error listing memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list memories")


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Get memory by ID."""
    try:
        memory = await memory_service.memory_repository.get_by_id(memory_id)

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if memory.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Increment access count
        await memory_service.memory_repository.increment_access_count(memory_id)

        return MemoryResponse.model_validate(memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get memory")


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    request: UpdateMemoryRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """
    Update memory. If content changes, re-generates embedding.

    Uses local all-MiniLM-L6-v2 model (FREE).
    """
    try:
        # Verify ownership
        existing_memory = await memory_service.memory_repository.get_by_id(memory_id)
        if not existing_memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if existing_memory.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update memory
        updated_memory = await memory_service.memory_repository.update(
            memory_id=memory_id,
            content=request.content,
            importance=request.importance,
            tags={"tags": request.tags} if request.tags else None,
            extra_metadata=request.metadata,
        )

        # Re-generate embedding if content changed
        if request.content and request.content != existing_memory.content:
            await memory_service.embedding_service.generate_embedding(request.content)
            # Update vector in Qdrant
            await memory_service.qdrant_service.upsert_vectors(
                collection_type=existing_memory.qdrant_collection,
                points=[
                    {
                        "id": existing_memory.qdrant_point_id,
                        "text": request.content[:500],
                        "metadata": {
                            "user_id": str(current_user.id),
                            "project_id": (
                                str(existing_memory.project_id)
                                if existing_memory.project_id
                                else None
                            ),
                            "memory_type": existing_memory.memory_type,
                            "source_type": existing_memory.source_type,
                            "updated_at": (
                                updated_memory.updated_at.isoformat()
                                if updated_memory
                                else datetime.utcnow().isoformat()
                            ),
                        },
                    }
                ],
            )

        return MemoryResponse.model_validate(updated_memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update memory")


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> None:
    """Delete memory from PostgreSQL and Qdrant."""
    try:
        # Verify ownership
        existing_memory = await memory_service.memory_repository.get_by_id(memory_id)
        if not existing_memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if existing_memory.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete from Qdrant
        await memory_service.qdrant_service.delete_points(
            collection_type=existing_memory.qdrant_collection,
            point_ids=[existing_memory.qdrant_point_id],
        )

        # Delete from PostgreSQL
        await memory_service.memory_repository.delete(memory_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete memory")


@router.post("/{memory_id}/archive", response_model=MemoryResponse)
async def archive_memory(
    memory_id: UUID,
    request: ArchiveMemoryRequest = ArchiveMemoryRequest(reason=None),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Archive memory (soft delete)."""
    try:
        # Verify ownership
        existing_memory = await memory_service.memory_repository.get_by_id(memory_id)
        if not existing_memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if existing_memory.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Archive memory
        # Archive memory using update
        archived_memory = await memory_service.memory_repository.update(
            memory_id=memory_id,
            is_archived=True,
        )

        return MemoryResponse.model_validate(archived_memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to archive memory")


@router.get("/{memory_id}/related", response_model=MemoryWithLinksResponse)
async def get_related_memories(
    memory_id: UUID,
    depth: int = Query(2, ge=1, le=3, description="Relationship depth"),
    min_strength: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relationship strength"),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryWithLinksResponse:
    """Get related memories as knowledge graph."""
    try:
        # Verify ownership
        existing_memory = await memory_service.memory_repository.get_by_id(memory_id)
        if not existing_memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if existing_memory.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get related memories
        # TODO: Implement related memories and links in repository
        # For now, return basic memory response
        return MemoryWithLinksResponse(
            **MemoryResponse.model_validate(existing_memory).model_dump(),
            links_from=[],
            links_to=[],
            related_memories=[],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting related memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get related memories")


@router.post("/ingest/chat/{chat_id}", response_model=MemoryIngestionResponse)
async def ingest_chat_memories(
    chat_id: UUID,
    request: IngestChatRequest = IngestChatRequest(),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryIngestionResponse:
    """
    Extract and store important information from chat.

    Automatically identifies key decisions, insights, and facts.
    """
    try:
        memories = await memory_service.ingest_from_chat(
            chat_id=chat_id,
            user_id=current_user.id,
            min_importance=request.min_importance,
        )

        return MemoryIngestionResponse(
            source_id=chat_id,
            source_type="chat",
            memories_created=[MemoryResponse.model_validate(memory) for memory in memories],
            total_memories=len(memories),
            ingestion_time_ms=None,  # TODO: Implement timing
            segments_processed=len(memories),
            relationships_created=0,  # TODO: Implement relationship counting
        )

    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error ingesting chat memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to ingest chat memories")


@router.post("/ingest/workflow/{workflow_id}", response_model=MemoryIngestionResponse)
async def ingest_workflow_memory(
    workflow_id: UUID,
    request: IngestWorkflowRequest = IngestWorkflowRequest(importance_override=None),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryIngestionResponse:
    """Store workflow output as memory."""
    try:
        # TODO: Implement workflow ingestion
        # For now, return a placeholder response
        return MemoryIngestionResponse(
            source_id=workflow_id,
            source_type="workflow",
            memories_created=[],
            total_memories=0,
            ingestion_time_ms=None,  # TODO: Implement timing
            segments_processed=0,
            relationships_created=0,
        )

    except Exception as e:
        logger.error(f"Error ingesting workflow memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to ingest workflow memory")


@router.get("/context/chat/{chat_id}", response_model=MemoryContextResponse)
async def get_chat_context(
    chat_id: UUID,
    max_tokens: int = Query(2000, ge=500, le=8000, description="Maximum token budget"),
    relevance_threshold: float = Query(0.6, ge=0.0, le=1.0, description="Minimum relevance score"),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryContextResponse:
    """
    Get assembled context for chat continuation.

    Combines recent messages with relevant long-term memories.
    """
    try:
        context_data = await memory_service.get_context_for_chat(
            chat_id=chat_id,
            user_id=current_user.id,
            max_tokens=max_tokens,
            relevance_threshold=relevance_threshold,
        )

        # Parse context data to extract memories and counts
        # TODO: Implement proper context parsing

        return MemoryContextResponse(
            chat_id=chat_id,
            context_string=context_data,
            token_count=len(context_data) // 4,  # Rough estimate
            memory_count=0,  # TODO: Extract from context
            recent_message_count=0,  # TODO: Extract from context
            assembly_time_ms=None,  # TODO: Implement timing
            relevance_threshold=relevance_threshold,
        )

    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting chat context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get chat context")


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryStatsResponse:
    """Get user's memory statistics and insights."""
    try:
        stats = await memory_service.get_memory_stats(current_user.id)

        return MemoryStatsResponse(
            user_id=current_user.id,
            total_memories=stats.get("total_memories", 0),
            important_memories=stats.get("important_memories", 0),
            recent_memories=stats.get("recent_memories", 0),
            collections=stats.get("collections", []),
            embedding_model=stats.get("embedding_model", "all-MiniLM-L6-v2"),
            embedding_dimension=stats.get("embedding_dimension", 384),
            last_updated=stats.get("last_updated", datetime.utcnow()),
        )

    except Exception as e:
        logger.error(f"Error getting memory stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get memory stats")
