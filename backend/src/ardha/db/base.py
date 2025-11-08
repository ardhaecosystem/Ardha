"""
Database base configuration for Alembic auto-discovery.

Import all SQLAlchemy models here to ensure they are registered
with the Base metadata for Alembic migrations.
"""

from ardha.models.base import Base
from ardha.models.project import Project  # Import for Alembic auto-discovery
from ardha.models.project_member import ProjectMember  # Import for Alembic auto-discovery
from ardha.models.task import Task  # Import for Alembic auto-discovery
from ardha.models.task_activity import TaskActivity  # Import for Alembic auto-discovery
from ardha.models.task_dependency import TaskDependency  # Import for Alembic auto-discovery
from ardha.models.task_tag import TaskTag  # Import for Alembic auto-discovery
from ardha.models.user import User  # Import for Alembic auto-discovery

# All models imported for Alembic auto-discovery

__all__ = ["Base"]