"""
Database base configuration for Alembic auto-discovery.

Import all SQLAlchemy models here to ensure they are registered
with the Base metadata for Alembic migrations.
"""

from ardha.models.base import Base
from ardha.models.user import User  # Import for Alembic auto-discovery
from ardha.models.project import Project  # Import for Alembic auto-discovery
from ardha.models.project_member import ProjectMember  # Import for Alembic auto-discovery

# Import all models here for Alembic auto-discovery
# As new models are created, import them here:
# from ardha.models.task import Task

__all__ = ["Base"]