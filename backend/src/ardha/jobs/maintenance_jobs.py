"""
Maintenance and backup background jobs.

This module provides Celery tasks for system maintenance including
session cleanup and database backups.
"""

import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from redis.asyncio import Redis

from ardha.core.celery_app import celery_app
from ardha.core.config import get_settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="maintenance.cleanup_old_sessions",
    queue="cleanup",
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
async def cleanup_old_sessions() -> Dict[str, Any]:
    """
    Clean up old session data and temporary cache entries.

    Cleans:
    - Redis cache entries older than 7 days
    - Orphaned cache keys (no associated user)
    - Temporary data and expired tokens

    Returns:
        Dict with cleanup statistics
    """
    logger.info("Starting old session cleanup")

    try:
        settings = get_settings()

        # Connect to Redis
        redis_client = Redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
        )

        try:
            # Get all cache keys
            cursor = 0
            deleted_count = 0
            checked_count = 0
            patterns_cleaned = {
                "embedding": 0,
                "chat": 0,
                "session": 0,
                "temp": 0,
            }

            # Scan for different key patterns
            key_patterns = [
                "embedding:*",  # Embedding cache
                "chat:*",  # Chat cache
                "session:*",  # Session data
                "temp:*",  # Temporary data
            ]

            for pattern in key_patterns:
                cursor = 0
                pattern_type = pattern.split(":")[0]

                while True:
                    # Scan in batches
                    cursor, keys = await redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100,
                    )

                    for key in keys:
                        checked_count += 1

                        # Get key TTL
                        ttl = await redis_client.ttl(key)

                        # Delete keys with no TTL or expired
                        # (TTL -1 means no expiration, -2 means key doesn't exist)
                        if ttl == -1:
                            # Key has no expiration, check if it's old
                            # For embedding cache, keep 24 hours (already set)
                            # For other keys, delete if no TTL
                            if pattern_type != "embedding":
                                await redis_client.delete(key)
                                deleted_count += 1
                                patterns_cleaned[pattern_type] += 1
                                logger.debug(f"Deleted key without TTL: {key}")

                        elif ttl == -2:
                            # Key doesn't exist anymore (race condition)
                            continue

                    # Break if we've scanned all keys
                    if cursor == 0:
                        break

            # Also clean up truly old session-like data
            # Look for keys older than 7 days (604800 seconds)
            seven_days_ago = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

            # Clean old temporary keys specifically
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor,
                    match="temp:*",
                    count=100,
                )

                for key in keys:
                    # Try to get key creation time from key name if available
                    # Format: temp:operation:timestamp:uuid
                    try:
                        parts = key.split(":")
                        if len(parts) >= 3 and parts[2].isdigit():
                            key_timestamp = int(parts[2])
                            if key_timestamp < seven_days_ago:
                                await redis_client.delete(key)
                                deleted_count += 1
                                patterns_cleaned["temp"] += 1
                    except (ValueError, IndexError):
                        # Skip if can't parse timestamp
                        pass

                if cursor == 0:
                    break

            logger.info(
                f"Session cleanup complete: checked {checked_count} keys, "
                f"deleted {deleted_count} keys"
            )

            return {
                "success": True,
                "cleaned_at": datetime.now(timezone.utc).isoformat(),
                "statistics": {
                    "keys_checked": checked_count,
                    "keys_deleted": deleted_count,
                    "by_pattern": patterns_cleaned,
                },
            }

        finally:
            await redis_client.close()

    except Exception as e:
        logger.error(f"Error cleaning up old sessions: {e}")
        raise


@celery_app.task(
    name="maintenance.backup_database",
    queue="maintenance",
    time_limit=1800,  # 30 minutes (backups can take time)
    soft_time_limit=1740,  # 29 minutes
)
def backup_database() -> Dict[str, Any]:
    """
    Create PostgreSQL database backup.

    Creates compressed backup using pg_dump and stores with timestamp.
    Automatically rotates backups to keep last 30 days.

    Returns:
        Dict with backup information

    Note:
        This is a synchronous function because subprocess is used.
    """
    logger.info("Starting database backup")

    try:
        settings = get_settings()

        # Parse database URL
        # Format: postgresql+asyncpg://user:password@host:port/database
        db_url = settings.database.url

        # Extract components
        # Remove scheme
        url_parts = db_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")

        # Split user:password@host:port/database
        if "@" in url_parts:
            auth_part, host_part = url_parts.split("@", 1)
            if ":" in auth_part:
                db_user, db_password = auth_part.split(":", 1)
            else:
                db_user = auth_part
                db_password = ""
        else:
            # No auth in URL
            db_user = "postgres"
            db_password = ""
            host_part = url_parts

        # Split host:port/database
        if "/" in host_part:
            host_port_part, db_name = host_part.split("/", 1)
        else:
            host_port_part = host_part
            db_name = "ardha"

        # Split host:port
        if ":" in host_port_part:
            db_host, db_port = host_port_part.split(":", 1)
        else:
            db_host = host_port_part
            db_port = "5432"

        # Create backup directory if it doesn't exist
        backup_dir = Path("/backups")
        backup_dir.mkdir(exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"ardha_backup_{timestamp}.sql"
        compressed_file = backup_dir / f"ardha_backup_{timestamp}.sql.gz"

        # Build pg_dump command
        # Use --clean to include DROP statements
        # Use --if-exists to avoid errors on restore
        pg_dump_cmd = [
            "pg_dump",
            "--host",
            db_host,
            "--port",
            db_port,
            "--username",
            db_user,
            "--dbname",
            db_name,
            "--clean",
            "--if-exists",
            "--create",
            "--file",
            str(backup_file),
        ]

        # Set password environment variable
        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = db_password

        logger.info(f"Creating database backup: {backup_file}")

        # Execute pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=1200,  # 20 minutes timeout
        )

        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr,
                "backup_file": None,
            }

        # Compress backup
        logger.info(f"Compressing backup: {compressed_file}")
        gzip_cmd = ["gzip", str(backup_file)]

        result = subprocess.run(
            gzip_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout
        )

        if result.returncode != 0:
            logger.error(f"gzip failed: {result.stderr}")
            # Keep uncompressed backup
            backup_path = backup_file
        else:
            backup_path = compressed_file

        # Get backup file size
        backup_size = backup_path.stat().st_size
        backup_size_mb = backup_size / (1024 * 1024)

        logger.info(f"Backup created successfully: {backup_path} " f"({backup_size_mb:.2f} MB)")

        # Rotate old backups (keep last 30 days)
        cleanup_old_backups(backup_dir, days_to_keep=30)

        return {
            "success": True,
            "backup_file": str(backup_path),
            "backup_size_mb": round(backup_size_mb, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": db_name,
        }

    except subprocess.TimeoutExpired as e:
        logger.error(f"Database backup timeout: {e}")
        return {
            "success": False,
            "error": "Backup operation timed out",
        }
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        raise


def cleanup_old_backups(backup_dir: Path, days_to_keep: int = 30) -> int:
    """
    Remove backup files older than specified days.

    Args:
        backup_dir: Directory containing backups
        days_to_keep: Number of days to keep backups

    Returns:
        Number of files deleted
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cutoff_timestamp = cutoff_date.timestamp()

        deleted_count = 0

        # Find all backup files
        for backup_file in backup_dir.glob("ardha_backup_*.sql*"):
            # Get file modification time
            file_mtime = backup_file.stat().st_mtime

            # Delete if older than cutoff
            if file_mtime < cutoff_timestamp:
                logger.info(f"Deleting old backup: {backup_file}")
                backup_file.unlink()
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old backup(s)")

        return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")
        return 0


logger.info("Maintenance jobs configured successfully")
