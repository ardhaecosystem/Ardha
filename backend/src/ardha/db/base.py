"""
Database base configuration for Alembic auto-discovery.

Import all SQLAlchemy models here to ensure they are registered
with the Base metadata for Alembic migrations.
"""

from ardha.models.ai_usage import AIUsage  # noqa: F401
from ardha.models.base import Base
from ardha.models.chat import Chat  # noqa: F401
from ardha.models.file import File  # noqa: F401
from ardha.models.git_commit import GitCommit  # noqa: F401
from ardha.models.github_integration import GitHubIntegration, PullRequest  # noqa: F401
from ardha.models.github_webhook import GitHubWebhookDelivery  # noqa: F401
from ardha.models.memory import Memory  # noqa: F401
from ardha.models.message import Message  # noqa: F401
from ardha.models.milestone import Milestone  # noqa: F401
from ardha.models.openspec import OpenSpecProposal  # noqa: F401
from ardha.models.project import Project  # noqa: F401
from ardha.models.project_member import ProjectMember  # noqa: F401
from ardha.models.task import Task  # noqa: F401
from ardha.models.task_activity import TaskActivity  # noqa: F401
from ardha.models.task_dependency import TaskDependency  # noqa: F401
from ardha.models.task_tag import TaskTag  # noqa: F401
from ardha.models.user import User  # noqa: F401
from ardha.models.workflow_execution import WorkflowExecution  # noqa: F401

# All models imported for Alembic auto-discovery

__all__ = ["Base"]
