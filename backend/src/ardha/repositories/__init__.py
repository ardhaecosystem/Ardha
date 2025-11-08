"""
Repository layer for data access abstraction.

This module exports all repository classes that implement the Repository
Pattern for database operations. Repositories provide a clean interface
between the service layer and SQLAlchemy models.
"""

from ardha.repositories.user_repository import UserRepository

__all__ = ["UserRepository"]