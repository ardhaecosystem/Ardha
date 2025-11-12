"""
Database models for workflow execution tracking.

This module defines SQLAlchemy models for persisting
workflow definitions, executions, and steps to the database.
"""

from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Numeric,
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ..models.base import BaseModel, SoftDeleteMixin
from .state import WorkflowStatus, WorkflowType, NodeStatus

if TYPE_CHECKING:
    from ..models.user import User
    from ..models.project import Project


class Workflow(BaseModel, SoftDeleteMixin):
    """
    Workflow definition model.
    
    Stores workflow templates and configurations that can be
    executed multiple times with different inputs.
    """
    
    __tablename__ = "workflows"
    
    # Primary identification
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Classification
    workflow_type: Mapped[WorkflowType] = mapped_column(
        SQLEnum(WorkflowType),
        nullable=False,
        index=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    
    # Configuration
    node_sequence: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    default_parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # Metadata
    tags: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workflows",
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="workflows",
    )
    executions: Mapped[list["WorkflowExecution"]] = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name='{self.name}', type={self.workflow_type})>"


class WorkflowExecution(BaseModel, SoftDeleteMixin):
    """
    Workflow execution instance model.
    
    Tracks individual executions of workflows with their
    state, results, and resource usage.
    """
    
    __tablename__ = "workflow_executions"
    
    # Primary identification
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    
    # Relationships
    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # Execution data
    initial_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    context: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    # Status tracking
    status: Mapped[WorkflowStatus] = mapped_column(
        SQLEnum(WorkflowStatus),
        nullable=False,
        default=WorkflowStatus.PENDING,
        index=True,
    )
    current_node: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    completed_nodes: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    failed_nodes: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    # Results and artifacts
    results: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    artifacts: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    # Resource usage
    ai_calls: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    token_usage: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    total_cost: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=0.0,
    )
    
    # Error handling
    errors: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="executions",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workflow_executions",
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="workflow_executions",
    )
    steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep",
        back_populates="execution",
        cascade="all, delete-orphan",
    )
    
    @hybrid_property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @hybrid_property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if not self.completed_nodes and not self.failed_nodes:
            return 0.0
        
        completed_count = len(self.completed_nodes) if isinstance(self.completed_nodes, list) else 0
        failed_count = len(self.failed_nodes) if isinstance(self.failed_nodes, list) else 0
        total_processed = completed_count + failed_count
        
        if total_processed == 0:
            return 0.0
        
        return (completed_count / total_processed) * 100.0
    
    def __repr__(self) -> str:
        return f"<WorkflowExecution(id={self.id}, status={self.status}, cost=${self.total_cost})>"


class WorkflowStep(BaseModel, SoftDeleteMixin):
    """
    Individual workflow step execution model.
    
    Tracks execution of individual nodes within a workflow
    with detailed timing and resource usage.
    """
    
    __tablename__ = "workflow_steps"
    
    # Primary identification
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    
    # Relationships
    execution_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Step information
    node_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # Status tracking
    status: Mapped[NodeStatus] = mapped_column(
        SQLEnum(NodeStatus),
        nullable=False,
        default=NodeStatus.PENDING,
        index=True,
    )
    
    # Input/Output data
    input_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    output_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    # Execution details
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Resource usage
    ai_calls_made: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    cost_incurred: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=0.0,
    )
    
    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution",
        back_populates="steps",
    )
    
    @hybrid_property
    def duration_seconds(self) -> Optional[float]:
        """Calculate step duration in seconds."""
        if self.duration_ms:
            return self.duration_ms / 1000.0
        return None
    
    def __repr__(self) -> str:
        return f"<WorkflowStep(id={self.id}, node={self.node_name}, status={self.status})>"