"""
Repository layer for data access abstraction.

This module exports all repository classes that implement the Repository
Pattern for database operations. Repositories provide a clean interface
between the service layer and SQLAlchemy models.
"""

from ardha.repositories.ai_usage_repository import AIUsageRepository
from ardha.repositories.chat_repository import ChatRepository
from ardha.repositories.database_entry_repository import DatabaseEntryRepository
from ardha.repositories.database_property_repository import DatabasePropertyRepository
from ardha.repositories.database_repository import DatabaseRepository
from ardha.repositories.file import FileRepository
from ardha.repositories.git_commit import GitCommitRepository
from ardha.repositories.github_integration import GitHubIntegrationRepository
from ardha.repositories.message_repository import MessageRepository
from ardha.repositories.milestone_repository import MilestoneRepository
from ardha.repositories.notification_preference_repository import NotificationPreferenceRepository
from ardha.repositories.notification_repository import NotificationRepository
from ardha.repositories.openspec import OpenSpecRepository
from ardha.repositories.project_repository import ProjectRepository
from ardha.repositories.pull_request import PullRequestRepository
from ardha.repositories.task_repository import TaskRepository
from ardha.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "ProjectRepository",
    "TaskRepository",
    "MilestoneRepository",
    "ChatRepository",
    "MessageRepository",
    "AIUsageRepository",
    "OpenSpecRepository",
    "FileRepository",
    "GitCommitRepository",
    "GitHubIntegrationRepository",
    "PullRequestRepository",
    "DatabaseRepository",
    "DatabasePropertyRepository",
    "DatabaseEntryRepository",
    "NotificationRepository",
    "NotificationPreferenceRepository",
]
