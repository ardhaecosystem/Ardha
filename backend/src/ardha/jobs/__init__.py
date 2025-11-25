"""Background job modules."""

# NEW: Cost and analytics jobs
from ardha.jobs.cost_jobs import (
    analyze_ai_usage_patterns,
    calculate_project_analytics,
    generate_daily_cost_report,
)

# NEW: Git and task jobs
from ardha.jobs.git_jobs import ingest_commit_to_memory

# NEW: Maintenance and backup jobs
from ardha.jobs.maintenance_jobs import backup_database, cleanup_old_sessions
from ardha.jobs.memory_cleanup import (
    archive_old_memories,
    cleanup_expired_memories,
    cleanup_old_links,
    cleanup_orphaned_vectors,
    optimize_qdrant_collections,
)
from ardha.jobs.memory_jobs import (
    build_memory_relationships,
    ingest_chat_memories,
    ingest_workflow_memory,
    optimize_memory_importance,
    process_pending_embeddings,
)
from ardha.jobs.task_jobs import calculate_team_velocity, send_overdue_task_reminders

__all__ = [
    # Memory jobs
    "ingest_chat_memories",
    "ingest_workflow_memory",
    "process_pending_embeddings",
    "build_memory_relationships",
    "optimize_memory_importance",
    # Cleanup jobs
    "cleanup_expired_memories",
    "archive_old_memories",
    "cleanup_orphaned_vectors",
    "optimize_qdrant_collections",
    "cleanup_old_links",
    # NEW: Git jobs
    "ingest_commit_to_memory",
    # NEW: Task jobs
    "calculate_team_velocity",
    "send_overdue_task_reminders",
    # NEW: Cost and analytics jobs
    "generate_daily_cost_report",
    "analyze_ai_usage_patterns",
    "calculate_project_analytics",
    # NEW: Maintenance and backup jobs
    "cleanup_old_sessions",
    "backup_database",
]
