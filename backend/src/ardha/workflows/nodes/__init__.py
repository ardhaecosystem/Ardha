"""
Workflow nodes package.

This package contains all workflow node implementations
for different types of AI agents and processing steps.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from ...core.openrouter import OpenRouterClient, OpenRouterError
from ...core.qdrant import QdrantError, QdrantService
from ..state import NodeState, WorkflowContext, WorkflowState
from .base import BaseNode
from .prd_nodes import (
    DefineFeaturesNode,
    ExtractRequirementsNode,
    GeneratePRDNode,
    PRDNodeException,
    ReviewFormatNode,
    SetMetricsNode,
)
from .research_nodes import (
    AnalyzeIdeaNode,
    CompetitiveAnalysisNode,
    MarketResearchNode,
    ResearchNodeException,
    SynthesizeResearchNode,
    TechnicalFeasibilityNode,
)

# Create a ResearchNode alias for AnalyzeIdeaNode for compatibility
ResearchNode = AnalyzeIdeaNode

logger = logging.getLogger(__name__)


class ArchitectNode(BaseNode):
    """
    Architecture workflow node for system design and planning.

    Analyzes requirements, creates architectural designs,
    and provides implementation guidance.
    """

    def __init__(self) -> None:
        super().__init__("architect")

    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute architecture workflow node.

        Args:
            state: Current workflow state
            context: Workflow execution context

        Returns:
            Architecture design and implementation plan
        """
        self.logger.info(f"Starting architecture design for: {state.initial_request[:100]}...")

        try:
            # Get relevant context (previous designs, patterns)
            context_items = await self._get_relevant_context(
                f"architecture design {state.initial_request}", context, state, limit=8
            )

            # Get research results if available
            research_findings = state.get_result("research", {}).get("research_findings", "")

            # Prepare architecture prompt
            system_prompt = """You are a software architect. Design a robust, scalable system based on the requirements. Provide:

1. **System Overview**: High-level architecture description
2. **Components**: Key system components and their responsibilities
3. **Data Flow**: How data moves through the system
4. **Technology Stack**: Recommended technologies and frameworks
5. **API Design**: Key endpoints and data structures
6. **Security Considerations**: Authentication, authorization, data protection
7. **Scalability Plan**: How the system handles growth
8. **Implementation Steps**: Phased development approach

Consider performance, maintainability, and cost-effectiveness."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Requirements: {state.initial_request}"},
            ]

            # Add research findings if available
            if research_findings:
                messages.insert(
                    1,
                    {
                        "role": "system",
                        "content": f"Research findings to inform architecture:\n{research_findings}",
                    },
                )

            # Add context if available
            if context_items:
                context_text = "\n".join([f"- {item['text']}" for item in context_items[:3]])
                messages.insert(
                    -1,
                    {
                        "role": "system",
                        "content": f"Relevant architectural patterns and previous designs:\n{context_text}",
                    },
                )

            # Call AI for architecture design
            architecture_result = await self._call_ai(
                messages=messages,
                model="anthropic/claude-sonnet-4.5",
                context=context,
                state=state,
                temperature=0.4,  # Balanced creativity and structure
                max_tokens=4000,
            )

            # Store architecture in memory
            await self._store_memory(
                content=architecture_result,
                metadata={
                    "type": "architecture",
                    "requirements": state.initial_request,
                    "research_informed": bool(research_findings),
                },
                context=context,
                state=state,
                collection_type="projects" if state.project_id else "chats",
            )

            result = {
                "architecture_design": architecture_result,
                "research_informed": bool(research_findings),
                "context_used": len(context_items),
                "architecture_model": "anthropic/claude-sonnet-4.5",
                "design_patterns": [
                    "modular",
                    "scalable",
                    "secure",
                ],  # Could be extracted from AI response
            }

            self.logger.info("Architecture node completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Architecture node failed: {e}")
            raise


class ImplementNode(BaseNode):
    """
    Implementation workflow node for code generation and development.

    Generates production-ready code based on architecture
    designs and requirements.
    """

    def __init__(self) -> None:
        super().__init__("implement")

    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute implementation workflow node.

        Args:
            state: Current workflow state
            context: Workflow execution context

        Returns:
            Generated code and implementation details
        """
        self.logger.info(f"Starting implementation for: {state.initial_request[:100]}...")

        try:
            # Get architecture design if available
            architecture_design = state.get_result("architect", {}).get("architecture_design", "")

            # Get relevant code examples and patterns
            context_items = await self._get_relevant_context(
                f"code implementation {state.initial_request}", context, state, limit=8
            )

            # Prepare implementation prompt
            system_prompt = """You are an expert developer. Write production-ready code based on the architecture and requirements. Provide:

1. **Code Implementation**: Clean, well-documented code
2. **File Structure**: Organization of files and directories
3. **Dependencies**: Required packages and libraries
4. **Configuration**: Setup and configuration files
5. **Tests**: Unit tests for critical functionality
6. **Documentation**: README and inline documentation
7. **Deployment Notes**: Instructions for deployment

Follow best practices, include error handling, and optimize for performance."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Requirements: {state.initial_request}"},
            ]

            # Add architecture design if available
            if architecture_design:
                messages.insert(
                    1,
                    {
                        "role": "system",
                        "content": f"Architecture design to implement:\n{architecture_design}",
                    },
                )

            # Add code context if available
            if context_items:
                context_text = "\n".join([f"- {item['text']}" for item in context_items[:5]])
                messages.insert(
                    -1,
                    {
                        "role": "system",
                        "content": f"Relevant code examples and patterns:\n{context_text}",
                    },
                )

            # Call AI for implementation
            implementation_result = await self._call_ai(
                messages=messages,
                model="z-ai/glm-4.6",  # Cost-effective for code generation
                context=context,
                state=state,
                temperature=0.2,  # Lower temperature for consistent code
                max_tokens=4000,
            )

            # Store implementation in memory
            await self._store_memory(
                content=implementation_result,
                metadata={
                    "type": "implementation",
                    "requirements": state.initial_request,
                    "architecture_informed": bool(architecture_design),
                },
                context=context,
                state=state,
                collection_type="code",
            )

            result = {
                "implementation_code": implementation_result,
                "architecture_informed": bool(architecture_design),
                "context_used": len(context_items),
                "implementation_model": "z-ai/glm-4.6",
                "language": "python",  # Could be detected from requirements
                "files_generated": [],  # Could be extracted from AI response
            }

            self.logger.info("Implementation node completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Implementation node failed: {e}")
            raise


class DebugNode(BaseNode):
    """
    Debug workflow node for error analysis and resolution.

    Analyzes problems, identifies root causes,
    and provides systematic debugging approaches.
    """

    def __init__(self) -> None:
        super().__init__("debug")

    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute debug workflow node.

        Args:
            state: Current workflow state
            context: Workflow execution context

        Returns:
            Debug analysis and resolution steps
        """
        self.logger.info(f"Starting debug analysis for: {state.initial_request[:100]}...")

        try:
            # Get relevant debugging context
            context_items = await self._get_relevant_context(
                f"debug error {state.initial_request}", context, state, limit=10
            )

            # Get previous errors from workflow state
            previous_errors = state.errors

            # Prepare debug prompt
            system_prompt = """You are a debugging expert. Analyze the problem and provide systematic solutions. Include:

1. **Problem Analysis**: Break down the issue and symptoms
2. **Root Cause Identification**: Most likely causes
3. **Diagnostic Steps**: Step-by-step troubleshooting approach
4. **Solutions**: Multiple resolution options with pros/cons
5. **Prevention**: How to avoid similar issues
6. **Verification**: How to confirm the fix works

Be methodical, explain technical concepts clearly, and provide actionable steps."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Problem to debug: {state.initial_request}"},
            ]

            # Add previous errors if available
            if previous_errors:
                error_context = "\n".join([f"- {error['error']}" for error in previous_errors[-3:]])
                messages.insert(
                    1,
                    {
                        "role": "system",
                        "content": f"Previous errors and attempts:\n{error_context}",
                    },
                )

            # Add debugging context if available
            if context_items:
                context_text = "\n".join([f"- {item['text']}" for item in context_items[:5]])
                messages.insert(
                    -1,
                    {
                        "role": "system",
                        "content": f"Relevant debugging solutions and patterns:\n{context_text}",
                    },
                )

            # Call AI for debug analysis
            debug_result = await self._call_ai(
                messages=messages,
                model="z-ai/glm-4.6",  # Good balance of cost and capability
                context=context,
                state=state,
                temperature=0.3,  # Lower temperature for analytical debugging
                max_tokens=4000,
            )

            # Store debug analysis in memory
            await self._store_memory(
                content=debug_result,
                metadata={
                    "type": "debug",
                    "problem": state.initial_request,
                    "previous_errors": len(previous_errors),
                },
                context=context,
                state=state,
                collection_type="chats",
            )

            result = {
                "debug_analysis": debug_result,
                "previous_errors_considered": len(previous_errors),
                "context_used": len(context_items),
                "debug_model": "z-ai/glm-4.6",
                "solutions_provided": [],  # Could be extracted from AI response
                "verification_steps": [],  # Could be extracted from AI response
            }

            self.logger.info("Debug node completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Debug node failed: {e}")
            raise


class MemoryIngestionNode(BaseNode):
    """
    Memory ingestion node for storing workflow results.

    Takes all workflow results and stores them in
    vector memory for future retrieval and learning.
    """

    def __init__(self) -> None:
        super().__init__("memory_ingestion")

    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute memory ingestion workflow node.

        Args:
            state: Current workflow state
            context: Workflow execution context

        Returns:
            Memory ingestion results and statistics
        """
        self.logger.info("Starting memory ingestion for workflow results")

        try:
            ingestion_stats: Dict[str, Any] = {
                "items_stored": 0,
                "collections_updated": set(),
                "errors": [],
            }

            # Store research results
            research_result = state.get_result("research")
            if research_result:
                success = await self._store_memory(
                    content=research_result.get("research_findings", ""),
                    metadata={
                        "type": "research",
                        "workflow_id": str(state.workflow_id),
                        "confidence": research_result.get("confidence_score", 0.0),
                    },
                    context=context,
                    state=state,
                    collection_type="chats",
                )
                if success:
                    ingestion_stats["items_stored"] += 1
                    ingestion_stats["collections_updated"].add("chats")
                else:
                    ingestion_stats["errors"].append("Failed to store research results")

            # Store architecture design
            architecture_result = state.get_result("architect")
            if architecture_result:
                success = await self._store_memory(
                    content=architecture_result.get("architecture_design", ""),
                    metadata={
                        "type": "architecture",
                        "workflow_id": str(state.workflow_id),
                        "research_informed": architecture_result.get("research_informed", False),
                    },
                    context=context,
                    state=state,
                    collection_type="projects" if state.project_id else "chats",
                )
                if success:
                    ingestion_stats["items_stored"] += 1
                    ingestion_stats["collections_updated"].add(
                        "projects" if state.project_id else "chats"
                    )
                else:
                    ingestion_stats["errors"].append("Failed to store architecture design")

            # Store implementation code
            implementation_result = state.get_result("implement")
            if implementation_result:
                success = await self._store_memory(
                    content=implementation_result.get("implementation_code", ""),
                    metadata={
                        "type": "implementation",
                        "workflow_id": str(state.workflow_id),
                        "language": implementation_result.get("language", "unknown"),
                        "architecture_informed": implementation_result.get(
                            "architecture_informed", False
                        ),
                    },
                    context=context,
                    state=state,
                    collection_type="code",
                )
                if success:
                    ingestion_stats["items_stored"] += 1
                    ingestion_stats["collections_updated"].add("code")
                else:
                    ingestion_stats["errors"].append("Failed to store implementation code")

            # Store debug analysis
            debug_result = state.get_result("debug")
            if debug_result:
                success = await self._store_memory(
                    content=debug_result.get("debug_analysis", ""),
                    metadata={
                        "type": "debug",
                        "workflow_id": str(state.workflow_id),
                        "previous_errors": debug_result.get("previous_errors_considered", 0),
                    },
                    context=context,
                    state=state,
                    collection_type="chats",
                )
                if success:
                    ingestion_stats["items_stored"] += 1
                    ingestion_stats["collections_updated"].add("chats")
                else:
                    ingestion_stats["errors"].append("Failed to store debug analysis")

            result = {
                "ingestion_complete": True,
                "items_stored": ingestion_stats["items_stored"],
                "collections_updated": list(ingestion_stats["collections_updated"]),
                "errors": ingestion_stats["errors"],
                "memory_efficiency": ingestion_stats["items_stored"] / max(1, len(state.results)),
            }

            self.logger.info(
                f"Memory ingestion completed: {ingestion_stats['items_stored']} items stored"
            )
            return result

        except Exception as e:
            self.logger.error(f"Memory ingestion node failed: {e}")
            raise


__all__ = [
    "BaseNode",
    "AnalyzeIdeaNode",
    "MarketResearchNode",
    "CompetitiveAnalysisNode",
    "TechnicalFeasibilityNode",
    "SynthesizeResearchNode",
    "ResearchNodeException",
    "ExtractRequirementsNode",
    "DefineFeaturesNode",
    "SetMetricsNode",
    "GeneratePRDNode",
    "ReviewFormatNode",
    "PRDNodeException",
    "ResearchNode",
    "ArchitectNode",
    "ImplementNode",
    "DebugNode",
    "MemoryIngestionNode",
]
