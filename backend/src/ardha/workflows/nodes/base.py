"""
Base node class for workflow nodes.

This module provides the base functionality that all
workflow nodes should inherit from.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from ...core.openrouter import OpenRouterClient, OpenRouterError
from ...core.qdrant import QdrantService, QdrantError
from ..state import WorkflowState, NodeState, WorkflowContext

logger = logging.getLogger(__name__)


class BaseNode:
    """
    Base class for all workflow nodes.
    
    Provides common functionality for AI interaction,
    memory retrieval, and result processing.
    """
    
    def __init__(self, node_name: str):
        """
        Initialize base node.
        
        Args:
            node_name: Unique name for this node
        """
        self.node_name = node_name
        self.logger = logger.getChild(node_name)
    
    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute the node's primary logic.
        
        Args:
            state: Current workflow state
            context: Workflow execution context
            
        Returns:
            Node execution results
            
        Raises:
            Exception: If execution fails
        """
        raise NotImplementedError("Subclasses must implement execute method")
    
    async def _get_relevant_context(
        self,
        query: str,
        context: WorkflowContext,
        state: WorkflowState,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from vector memory.
        
        Args:
            query: Query to search for
            context: Workflow execution context
            state: Current workflow state
            limit: Maximum number of results
            
        Returns:
            List of relevant context items
        """
        try:
            # Search in general knowledge base
            results = await context.qdrant_service.search_similar(
                collection_type="chats",
                query_text=query,
                limit=limit,
                score_threshold=0.6,
            )
            
            # Also search project-specific context if available
            if state.project_id:
                project_results = await context.qdrant_service.search_similar(
                    collection_type="projects",
                    query_text=query,
                    identifier=str(state.project_id),
                    limit=limit,
                    score_threshold=0.6,
                )
                results.extend(project_results)
            
            self.logger.info(f"Retrieved {len(results)} context items for query: {query[:100]}...")
            return results
            
        except QdrantError as e:
            self.logger.warning(f"Failed to retrieve context: {e}")
            return []
    
    async def _call_ai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        context: WorkflowContext,
        state: WorkflowState,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Make an AI call with error handling and tracking.
        
        Args:
            messages: List of message dictionaries
            model: AI model to use
            context: Workflow execution context
            state: Current workflow state
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            AI response text
            
        Raises:
            Exception: If AI call fails
        """
        try:
            # Get model info for cost calculation
            model_info = context.get_model(model)
            if not model_info:
                raise ValueError(f"Unsupported model: {model}")
            
            # Prepare request
            from ...schemas.ai.requests import CompletionRequest, ChatMessage, MessageRole as AIMessageRole
            
            chat_messages = [
                ChatMessage(role=AIMessageRole(msg["role"]), content=msg["content"])
                for msg in messages
            ]
            
            request = CompletionRequest(
                model=model,
                messages=chat_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Make the call
            response = await context.openrouter_client.complete(request)
            
            # Extract content and usage
            content = response.content
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                cost = model_info.calculate_cost(input_tokens, output_tokens)
                
                # Track usage in state if method exists
                if hasattr(state, 'add_ai_call'):
                    state.add_ai_call(model, self.node_name, input_tokens, output_tokens, cost)
                
                self.logger.info(
                    f"AI call completed: {input_tokens} input, {output_tokens} output, ${cost:.6f} cost"
                )
            
            return content
            
        except OpenRouterError as e:
            self.logger.error(f"AI call failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in AI call: {e}")
            raise
    
    async def _store_memory(
        self,
        content: str,
        metadata: Dict[str, Any],
        context: WorkflowContext,
        state: WorkflowState,
        collection_type: str = "chats",
    ) -> bool:
        """
        Store content in vector memory for future retrieval.
        
        Args:
            content: Text content to store
            metadata: Metadata for the content
            context: Workflow execution context
            state: Current workflow state
            collection_type: Type of collection to store in
            
        Returns:
            True if stored successfully
        """
        try:
            point = {
                "id": str(UUID()),
                "text": content,
                "metadata": {
                    **metadata,
                    "node": self.node_name,
                    "workflow_id": str(state.workflow_id),
                },
                "created_at": self._get_timestamp(),
            }
            
            await context.qdrant_service.upsert_vectors(
                collection_type=collection_type,
                points=[point],
            )
            
            self.logger.debug(f"Stored memory in {collection_type}: {content[:100]}...")
            return True
            
        except QdrantError as e:
            self.logger.warning(f"Failed to store memory: {e}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat() + "Z"