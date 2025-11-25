"""
Workflow execution tracking service.

This module provides functionality to track, monitor,
and analyze workflow executions for performance and debugging.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from .memory import get_memory_service
from .state import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowTrackingService:
    """
    Service for tracking and monitoring workflow executions.

    Handles:
    - Execution lifecycle tracking
    - Performance metrics collection
    - Error analysis and reporting
    - Execution history and analytics
    """

    def __init__(self):
        """Initialize workflow tracking service."""
        self.logger = logger
        self.memory_service = get_memory_service()

        # In-memory tracking for active executions
        self.active_executions: Dict[UUID, Dict[str, Any]] = {}

        # Performance metrics cache
        self.metrics_cache: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_duration": 0.0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "last_updated": datetime.utcnow(),
        }

        self.logger.info("Workflow tracking service initialized")

    async def start_execution_tracking(
        self,
        execution_id: UUID,
        workflow_type: str,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        initial_request: Optional[str] = None,
    ) -> bool:
        """
        Start tracking a workflow execution.

        Args:
            execution_id: Unique execution identifier
            workflow_type: Type of workflow being executed
            user_id: User executing the workflow
            project_id: Optional project identifier
            initial_request: Initial request/prompt

        Returns:
            True if tracking started successfully
        """
        try:
            # Create tracking record
            tracking_record = {
                "execution_id": execution_id,
                "workflow_type": workflow_type,
                "user_id": user_id,
                "project_id": project_id,
                "initial_request": initial_request,
                "status": WorkflowStatus.PENDING,
                "started_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "events": [
                    {
                        "type": "execution_started",
                        "timestamp": datetime.utcnow(),
                        "data": {
                            "workflow_type": workflow_type,
                            "user_id": str(user_id),
                        },
                    }
                ],
                "metrics": {
                    "duration_ms": 0,
                    "cost": 0.0,
                    "tokens": 0,
                    "ai_calls": 0,
                    "retries": 0,
                },
            }

            # Store in active tracking
            self.active_executions[execution_id] = tracking_record

            # Update metrics
            self.metrics_cache["total_executions"] += 1
            self.metrics_cache["last_updated"] = datetime.utcnow()

            self.logger.info(f"Started tracking execution: {execution_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start execution tracking: {e}")
            return False

    async def update_execution_status(
        self,
        execution_id: UUID,
        status: WorkflowStatus,
        current_node: Optional[str] = None,
        error: Optional[str] = None,
        metrics_update: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update execution status and metrics.

        Args:
            execution_id: Execution identifier
            status: New workflow status
            current_node: Currently executing node
            error: Optional error message
            metrics_update: Optional metrics to update

        Returns:
            True if update successful
        """
        try:
            if execution_id not in self.active_executions:
                self.logger.warning(f"Execution not found in tracking: {execution_id}")
                return False

            tracking_record = self.active_executions[execution_id]

            # Update status
            old_status = tracking_record["status"]
            tracking_record["status"] = status
            tracking_record["last_activity"] = datetime.utcnow()

            # Add status change event
            event = {
                "type": "status_changed",
                "timestamp": datetime.utcnow(),
                "data": {
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "current_node": current_node,
                },
            }

            if error:
                event["data"]["error"] = error
                tracking_record["events"].append(event)

            # Update current node
            if current_node:
                tracking_record["current_node"] = current_node

            # Update metrics if provided
            if metrics_update:
                for key, value in metrics_update.items():
                    if key in tracking_record["metrics"]:
                        tracking_record["metrics"][key] = value

            # Handle completion
            if status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            ]:
                tracking_record["completed_at"] = datetime.utcnow()

                # Calculate final metrics
                if tracking_record["started_at"]:
                    duration = tracking_record["completed_at"] - tracking_record["started_at"]
                    tracking_record["metrics"]["duration_ms"] = int(duration.total_seconds() * 1000)

                # Update global metrics
                await self._update_global_metrics(execution_id, status)

                # Move to history (remove from active)
                # In production, this would be stored in database
                del self.active_executions[execution_id]

            self.logger.info(f"Updated execution status: {execution_id} -> {status.value}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update execution status: {e}")
            return False

    async def add_execution_event(
        self,
        execution_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        node_name: Optional[str] = None,
    ) -> bool:
        """
        Add an event to execution tracking.

        Args:
            execution_id: Execution identifier
            event_type: Type of event
            data: Event data
            node_name: Optional node name associated with event

        Returns:
            True if event added successfully
        """
        try:
            if execution_id not in self.active_executions:
                self.logger.warning(f"Execution not found in tracking: {execution_id}")
                return False

            tracking_record = self.active_executions[execution_id]

            # Create event
            event = {
                "type": event_type,
                "timestamp": datetime.utcnow(),
                "data": data,
            }

            if node_name:
                event["node_name"] = node_name

            tracking_record["events"].append(event)
            tracking_record["last_activity"] = datetime.utcnow()

            self.logger.info(f"Added event to execution {execution_id}: {event_type}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add execution event: {e}")
            return False

    async def get_execution_tracking(
        self,
        execution_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get tracking information for execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Tracking record or None if not found
        """
        try:
            # Check active executions first
            if execution_id in self.active_executions:
                return self.active_executions[execution_id]

            # Search in memory for completed executions
            results = await self.memory_service.search_workflows(
                query=str(execution_id),
                limit=1,
            )

            if results:
                return results[0]

            return None

        except Exception as e:
            self.logger.error(f"Failed to get execution tracking: {e}")
            return None

    async def get_user_executions(
        self,
        user_id: UUID,
        limit: int = 50,
        status_filter: Optional[WorkflowStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get executions for a user.

        Args:
            user_id: User identifier
            limit: Maximum results to return
            status_filter: Optional status filter

        Returns:
            List of execution tracking records
        """
        try:
            # Get active executions for user
            active_executions = []
            for execution_id, tracking_record in self.active_executions.items():
                if tracking_record["user_id"] == user_id:
                    if status_filter is None or tracking_record["status"] == status_filter:
                        active_executions.append(tracking_record)

            # Get completed executions from memory
            completed_executions = await self.memory_service.search_workflows(
                query=f"user:{user_id}",
                user_id=user_id,
                limit=limit - len(active_executions),
            )

            # Combine and sort by last activity
            all_executions = active_executions + completed_executions
            all_executions.sort(key=lambda x: x.get("last_activity", datetime.min), reverse=True)

            return all_executions[:limit]

        except Exception as e:
            self.logger.error(f"Failed to get user executions: {e}")
            return []

    async def get_execution_metrics(
        self,
        execution_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed metrics for execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Execution metrics or None if not found
        """
        try:
            tracking_record = await self.get_execution_tracking(execution_id)
            if not tracking_record:
                return None

            # Calculate additional metrics
            metrics = tracking_record["metrics"].copy()

            # Event-based metrics
            events = tracking_record.get("events", [])
            metrics["total_events"] = len(events)
            metrics["node_transitions"] = len([e for e in events if e["type"] == "status_changed"])
            metrics["error_events"] = len([e for e in events if e["type"] == "error"])

            # Performance metrics
            if tracking_record.get("started_at") and tracking_record.get("completed_at"):
                duration = tracking_record["completed_at"] - tracking_record["started_at"]
                metrics["duration_seconds"] = duration.total_seconds()
                metrics["duration_formatted"] = str(duration)

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get execution metrics: {e}")
            return None

    async def get_global_metrics(self) -> Dict[str, Any]:
        """
        Get global workflow execution metrics.

        Returns:
            Global metrics dictionary
        """
        try:
            # Update cache if stale (older than 5 minutes)
            if datetime.utcnow() - self.metrics_cache["last_updated"] > timedelta(minutes=5):
                await self._refresh_global_metrics()

            return self.metrics_cache.copy()

        except Exception as e:
            self.logger.error(f"Failed to get global metrics: {e}")
            return {}

    async def analyze_performance(
        self,
        workflow_type: Optional[str] = None,
        time_range_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Analyze workflow performance trends.

        Args:
            workflow_type: Optional workflow type filter
            time_range_hours: Time range in hours

        Returns:
            Performance analysis results
        """
        try:
            # Get recent executions
            since_time = datetime.utcnow() - timedelta(hours=time_range_hours)

            # Search for recent workflows
            query = f"since:{since_time.isoformat()}"
            if workflow_type:
                query += f" workflow_type:{workflow_type}"

            recent_executions = await self.memory_service.search_workflows(
                query=query,
                limit=100,
            )

            if not recent_executions:
                return {"message": "No recent executions found"}

            # Analyze performance
            analysis = {
                "time_range_hours": time_range_hours,
                "total_executions": len(recent_executions),
                "workflow_types": {},
                "success_rate": 0.0,
                "average_duration": 0.0,
                "average_cost": 0.0,
                "error_patterns": {},
                "performance_trends": [],
            }

            # Count by workflow type
            for execution in recent_executions:
                w_type = execution.get("workflow_type", "unknown")
                analysis["workflow_types"][w_type] = analysis["workflow_types"].get(w_type, 0) + 1

            # Calculate success rate
            successful = sum(1 for e in recent_executions if e.get("status") == "completed")
            analysis["success_rate"] = (
                (successful / len(recent_executions)) * 100 if recent_executions else 0
            )

            # Calculate averages
            durations = []
            costs = []
            for execution in recent_executions:
                if execution.get("metrics", {}).get("duration_ms"):
                    durations.append(
                        execution["metrics"]["duration_ms"] / 1000
                    )  # Convert to seconds
                if execution.get("metrics", {}).get("cost"):
                    costs.append(execution["metrics"]["cost"])

            if durations:
                analysis["average_duration"] = sum(durations) / len(durations)
            if costs:
                analysis["average_cost"] = sum(costs) / len(costs)

            # Analyze errors
            errors = []
            for execution in recent_executions:
                execution_errors = execution.get("errors", [])
                errors.extend(execution_errors)

            error_counts = {}
            for error in errors:
                error_msg = error.get("error", "unknown")
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1

            # Get top 5 errors
            analysis["error_patterns"] = dict(
                sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            )

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze performance: {e}")
            return {"error": str(e)}

    async def _update_global_metrics(
        self,
        execution_id: UUID,
        final_status: WorkflowStatus,
    ) -> None:
        """Update global metrics based on execution completion."""
        try:
            if execution_id not in self.active_executions:
                return

            tracking_record = self.active_executions[execution_id]
            metrics = tracking_record["metrics"]

            # Update counters
            if final_status == WorkflowStatus.COMPLETED:
                self.metrics_cache["successful_executions"] += 1
            elif final_status == WorkflowStatus.FAILED:
                self.metrics_cache["failed_executions"] += 1

            # Update totals
            self.metrics_cache["total_cost"] += metrics.get("cost", 0.0)
            self.metrics_cache["total_tokens"] += metrics.get("tokens", 0)

            # Update average duration
            if metrics.get("duration_ms"):
                total_duration = self.metrics_cache["average_duration"] * (
                    self.metrics_cache["total_executions"] - 1
                )
                total_duration += metrics["duration_ms"] / 1000  # Convert to seconds
                self.metrics_cache["average_duration"] = (
                    total_duration / self.metrics_cache["total_executions"]
                )

            self.metrics_cache["last_updated"] = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"Failed to update global metrics: {e}")

    async def _refresh_global_metrics(self) -> None:
        """Refresh global metrics from memory."""
        try:
            # This would typically query a database for historical metrics
            # For now, keep current cached values
            self.metrics_cache["last_updated"] = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"Failed to refresh global metrics: {e}")


# Global tracking service instance
_tracking_service: Optional[WorkflowTrackingService] = None


def get_workflow_tracking_service() -> WorkflowTrackingService:
    """
    Get cached workflow tracking service instance.

    Returns:
        WorkflowTrackingService instance
    """
    global _tracking_service
    if _tracking_service is None:
        _tracking_service = WorkflowTrackingService()
    return _tracking_service
