"""
Rollup evaluation service for Notion-style database rollups.

This module provides rollup calculation capabilities for aggregating values
from related database entries, supporting various aggregation functions like
count, sum, average, median, min, max, and more.
"""

import logging
import statistics
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.exceptions import RollupCalculationError
from ardha.repositories.database_entry_repository import DatabaseEntryRepository
from ardha.repositories.database_property_repository import DatabasePropertyRepository

logger = logging.getLogger(__name__)


class RollupService:
    """
    Service for calculating rollup properties in Notion-style databases.

    Rollup properties aggregate values from related entries through
    relation properties, supporting various aggregation functions.

    Attributes:
        db: SQLAlchemy async session for database operations
        entry_repo: DatabaseEntryRepository for data access
        property_repo: DatabasePropertyRepository for property metadata
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize RollupService with database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.entry_repo = DatabaseEntryRepository(db)
        self.property_repo = DatabasePropertyRepository(db)

    async def calculate_rollup(
        self,
        entry_id: UUID,
        rollup_config: Dict,
        property_id: UUID,
    ) -> Dict[str, Any]:
        """
        Calculate a rollup property value by aggregating related entry values.

        Rollup configuration format:
        {
            "relation_property_id": UUID,  # Property containing relations
            "target_property_id": UUID,     # Property to aggregate from related entries
            "function": str                 # Aggregation function name
        }

        Args:
            entry_id: UUID of the database entry
            rollup_config: Rollup configuration dictionary
            property_id: UUID of the rollup property being calculated

        Returns:
            Dictionary with 'value' and 'type' keys:
                - {"value": result, "type": "number"}
                - {"value": result, "type": "array"}
                - {"value": result, "type": "string"}

        Raises:
            RollupCalculationError: If calculation fails
        """
        try:
            # Validate config
            if not rollup_config or not isinstance(rollup_config, dict):
                raise RollupCalculationError(
                    "Invalid rollup config: must be a dictionary",
                    rollup_config=rollup_config,
                    property_id=str(property_id),
                )

            relation_property_id = rollup_config.get("relation_property_id")
            target_property_id = rollup_config.get("target_property_id")
            function = rollup_config.get("function")

            if not relation_property_id or not target_property_id or not function:
                raise RollupCalculationError(
                    "Rollup config must include relation_property_id, "
                    "target_property_id, and function",
                    rollup_config=rollup_config,
                    property_id=str(property_id),
                )

            # Ensure function is string
            if not isinstance(function, str):
                raise RollupCalculationError(
                    "Function must be a string",
                    rollup_config=rollup_config,
                    property_id=str(property_id),
                )

            # Convert to UUID if strings, validate if already UUID
            if isinstance(relation_property_id, str):
                relation_property_id = UUID(relation_property_id)
            elif not isinstance(relation_property_id, UUID):
                raise RollupCalculationError(
                    "relation_property_id must be UUID or string",
                    rollup_config=rollup_config,
                    property_id=str(property_id),
                )

            if isinstance(target_property_id, str):
                target_property_id = UUID(target_property_id)
            elif not isinstance(target_property_id, UUID):
                raise RollupCalculationError(
                    "target_property_id must be UUID or string",
                    rollup_config=rollup_config,
                    property_id=str(property_id),
                )

            # Get related entries (now type-safe)
            related_entry_ids = await self.get_related_entries(entry_id, relation_property_id)

            if not related_entry_ids:
                # No related entries - return appropriate empty value
                return self._get_empty_rollup_result(function)

            # Get target property values from related entries
            values = await self.get_property_values_from_entries(
                related_entry_ids, target_property_id
            )

            # Apply rollup function
            result = await self.apply_rollup_function(function, values)

            # Determine result type
            result_type = self._determine_result_type(function)

            logger.debug(
                f"Calculated rollup for entry {entry_id}, property {property_id}: "
                f"{result} (function: {function}, {len(values)} values)"
            )

            return {"value": result, "type": result_type}

        except RollupCalculationError:
            raise
        except Exception as e:
            logger.error(f"Error calculating rollup for entry {entry_id}: {e}", exc_info=True)
            raise RollupCalculationError(
                f"Rollup calculation failed: {str(e)}",
                rollup_config=rollup_config,
                property_id=str(property_id),
            )

    async def get_related_entries(
        self,
        entry_id: UUID,
        relation_property_id: UUID,
    ) -> List[UUID]:
        """
        Get entry IDs from a relation property value.

        Args:
            entry_id: UUID of the entry containing the relation
            relation_property_id: UUID of the relation property

        Returns:
            List of related entry UUIDs

        Raises:
            RollupCalculationError: If relation property not found or invalid
        """
        try:
            # Get the relation property value
            value = await self.entry_repo.get_value(entry_id, relation_property_id)

            if not value:
                return []

            # Extract entry IDs from relation value
            # Format: {"relations": [{"id": UUID}, {"id": UUID}]}
            if isinstance(value, dict) and "relations" in value:
                relations = value["relations"]
                if isinstance(relations, list):
                    entry_ids = []
                    for rel in relations:
                        if isinstance(rel, dict) and "id" in rel:
                            entry_ids.append(
                                UUID(rel["id"]) if isinstance(rel["id"], str) else rel["id"]
                            )
                    return entry_ids

            return []

        except Exception as e:
            logger.error(f"Error getting related entries: {e}", exc_info=True)
            raise RollupCalculationError(f"Failed to get related entries: {str(e)}")

    async def get_property_values_from_entries(
        self,
        entry_ids: List[UUID],
        property_id: UUID,
    ) -> List[Any]:
        """
        Get specific property values from multiple entries.

        Filters out None values and extracts actual values from property JSON format.

        Args:
            entry_ids: List of entry UUIDs to get values from
            property_id: UUID of the property to get values for

        Returns:
            List of property values (non-empty only)

        Raises:
            RollupCalculationError: If value retrieval fails
        """
        try:
            values = []

            for entry_id in entry_ids:
                value = await self.entry_repo.get_value(entry_id, property_id)

                if value is None:
                    continue

                # Extract actual value based on property type format
                extracted_value = self._extract_value_from_json(value)

                if extracted_value is not None:
                    values.append(extracted_value)

            return values

        except Exception as e:
            logger.error(f"Error getting property values from entries: {e}", exc_info=True)
            raise RollupCalculationError(f"Failed to get property values: {str(e)}")

    def _extract_value_from_json(self, value: Any) -> Any:
        """
        Extract actual value from property JSON format.

        Args:
            value: Property value in JSON format

        Returns:
            Extracted actual value
        """
        if not isinstance(value, dict):
            return value

        # Extract based on known property formats
        if "number" in value:
            return value["number"]
        elif "text" in value:
            return value["text"]
        elif "checkbox" in value:
            return value["checkbox"]
        elif "select" in value:
            select_val = value["select"]
            return select_val.get("name") if isinstance(select_val, dict) else select_val
        elif "date" in value:
            return value["date"]
        elif "formula" in value:
            formula_val = value["formula"]
            if isinstance(formula_val, dict) and "result" in formula_val:
                return formula_val["result"]
            return formula_val

        # Return full value if no specific extraction matched
        return value

    async def apply_rollup_function(
        self,
        function: str,
        values: List[Any],
    ) -> Any:
        """
        Apply the specified rollup aggregation function.

        Args:
            function: Rollup function name
            values: List of values to aggregate

        Returns:
            Aggregated result value

        Raises:
            RollupCalculationError: If function unknown or calculation fails
        """
        try:
            function_lower = function.lower()

            # Count functions
            if function_lower == "count":
                return len(values)

            if function_lower == "count_values":
                # Count non-empty values
                return sum(1 for v in values if v is not None and v != "")

            if function_lower == "count_unique_values":
                # Count distinct values
                unique = set()
                for v in values:
                    if v is not None:
                        # Handle unhashable types
                        if isinstance(v, (list, dict)):
                            unique.add(str(v))
                        else:
                            unique.add(v)
                return len(unique)

            if function_lower == "count_empty":
                return sum(1 for v in values if v is None or v == "")

            if function_lower == "count_not_empty":
                return sum(1 for v in values if v is not None and v != "")

            if function_lower == "percent_empty":
                if len(values) == 0:
                    return 0.0
                empty_count = sum(1 for v in values if v is None or v == "")
                return (empty_count / len(values)) * 100

            if function_lower == "percent_not_empty":
                if len(values) == 0:
                    return 0.0
                non_empty_count = sum(1 for v in values if v is not None and v != "")
                return (non_empty_count / len(values)) * 100

            # Numeric aggregation functions - require numeric values
            numeric_values = self._convert_to_numbers(values)

            if function_lower == "sum":
                return sum(numeric_values) if numeric_values else 0

            if function_lower == "average":
                return statistics.mean(numeric_values) if numeric_values else 0

            if function_lower == "median":
                return statistics.median(numeric_values) if numeric_values else 0

            if function_lower == "min":
                return min(numeric_values) if numeric_values else None

            if function_lower == "max":
                return max(numeric_values) if numeric_values else None

            if function_lower == "range":
                if numeric_values:
                    return max(numeric_values) - min(numeric_values)
                return 0

            if function_lower == "show_original":
                # Return values as array
                return values

            raise RollupCalculationError(f"Unknown rollup function: {function}")

        except RollupCalculationError:
            raise
        except Exception as e:
            logger.error(f"Error applying rollup function {function}: {e}", exc_info=True)
            raise RollupCalculationError(f"Failed to apply function {function}: {str(e)}")

    def _convert_to_numbers(self, values: List[Any]) -> List[float]:
        """
        Convert values to numbers, filtering out non-numeric values.

        Args:
            values: List of values to convert

        Returns:
            List of numeric values
        """
        numbers = []

        for v in values:
            if v is None:
                continue

            # Explicitly exclude booleans (bool is subclass of int)
            if isinstance(v, bool):
                continue

            try:
                if isinstance(v, (int, float)):
                    numbers.append(float(v))
                elif isinstance(v, str):
                    # Try to parse string as number
                    try:
                        numbers.append(float(v))
                    except ValueError:
                        # Not a numeric string, skip
                        continue
            except (ValueError, TypeError):
                # Skip values that can't be converted
                continue

        return numbers

    def _get_empty_rollup_result(self, function: str) -> Dict[str, Any]:
        """
        Get appropriate empty result for a rollup function.

        Args:
            function: Rollup function name

        Returns:
            Dictionary with 'value' and 'type' for empty result
        """
        function_lower = function.lower()

        # Count functions return 0
        if function_lower in [
            "count",
            "count_values",
            "count_unique_values",
            "count_empty",
            "count_not_empty",
            "sum",
        ]:
            return {"value": 0, "type": "number"}

        # Percent functions return 0.0
        if function_lower in ["percent_empty", "percent_not_empty"]:
            return {"value": 0.0, "type": "number"}

        # Average returns 0
        if function_lower == "average":
            return {"value": 0, "type": "number"}

        # Median returns 0
        if function_lower == "median":
            return {"value": 0, "type": "number"}

        # Min/max return None
        if function_lower in ["min", "max"]:
            return {"value": None, "type": "number"}

        # Range returns 0
        if function_lower == "range":
            return {"value": 0, "type": "number"}

        # Show original returns empty array
        if function_lower == "show_original":
            return {"value": [], "type": "array"}

        # Default to None
        return {"value": None, "type": "string"}

    def _determine_result_type(self, function: str) -> str:
        """
        Determine the result type for a rollup function.

        Args:
            function: Rollup function name

        Returns:
            Result type: "number", "array", or "string"
        """
        function_lower = function.lower()

        if function_lower == "show_original":
            return "array"

        # Most aggregation functions return numbers
        if function_lower in [
            "count",
            "count_values",
            "count_unique_values",
            "count_empty",
            "count_not_empty",
            "percent_empty",
            "percent_not_empty",
            "sum",
            "average",
            "median",
            "min",
            "max",
            "range",
        ]:
            return "number"

        return "string"

    async def recalculate_entry_rollups(self, entry_id: UUID) -> int:
        """
        Recalculate all rollup properties for an entry.

        Args:
            entry_id: UUID of entry to recalculate

        Returns:
            Count of rollups recalculated

        Raises:
            RollupCalculationError: If recalculation fails
        """
        try:
            entry = await self.entry_repo.get_by_id(entry_id)
            if not entry:
                raise RollupCalculationError(f"Entry {entry_id} not found")

            # Get all rollup properties for this database
            rollup_props = await self.property_repo.get_rollup_properties(entry.database_id)

            if not rollup_props:
                return 0

            count = 0

            for prop in rollup_props:
                if prop.config:
                    result = await self.calculate_rollup(entry_id, prop.config, prop.id)

                    # Store computed value
                    rollup_value = {"rollup": result}
                    await self.entry_repo.set_value(
                        entry_id, prop.id, rollup_value, entry.created_by_user_id
                    )
                    count += 1

            logger.info(f"Recalculated {count} rollups for entry {entry_id}")
            return count

        except Exception as e:
            logger.error(f"Error recalculating entry rollups: {e}", exc_info=True)
            raise RollupCalculationError(f"Failed to recalculate rollups: {str(e)}")

    async def recalculate_database_rollups(self, database_id: UUID) -> int:
        """
        Recalculate all rollups for all entries in a database.

        Batch processes entries for performance.

        Args:
            database_id: UUID of database

        Returns:
            Total count of rollups recalculated

        Raises:
            RollupCalculationError: If recalculation fails
        """
        try:
            # Get all entries in batches
            total_count = 0
            offset = 0
            batch_size = 50

            while True:
                entries = await self.entry_repo.get_by_database(
                    database_id, limit=batch_size, offset=offset
                )

                if not entries:
                    break

                for entry in entries:
                    count = await self.recalculate_entry_rollups(entry.id)
                    total_count += count

                offset += batch_size

            logger.info(f"Recalculated {total_count} rollups for database {database_id}")
            return total_count

        except Exception as e:
            logger.error(f"Error recalculating database rollups: {e}", exc_info=True)
            raise RollupCalculationError(f"Failed to recalculate database rollups: {str(e)}")

    async def get_rollup_dependencies(
        self,
        database_id: UUID,
        property_id: UUID,
    ) -> Tuple[UUID, UUID]:
        """
        Get the relation and target property IDs for a rollup.

        Used for dependency tracking and update triggering.

        Args:
            database_id: UUID of database containing the property
            property_id: UUID of the rollup property

        Returns:
            Tuple of (relation_property_id, target_property_id)

        Raises:
            RollupCalculationError: If property not found or not a rollup
        """
        try:
            property_obj = await self.property_repo.get_by_id(property_id)

            if not property_obj:
                raise RollupCalculationError(f"Property {property_id} not found")

            if property_obj.property_type != "rollup":
                raise RollupCalculationError(f"Property {property_id} is not a rollup property")

            if not property_obj.config:
                raise RollupCalculationError(f"Rollup property {property_id} has no config")

            relation_property_id = property_obj.config.get("relation_property_id")
            target_property_id = property_obj.config.get("target_property_id")

            if not relation_property_id or not target_property_id:
                raise RollupCalculationError(
                    f"Rollup config missing required fields for property {property_id}"
                )

            # Convert to UUID if strings
            if isinstance(relation_property_id, str):
                relation_property_id = UUID(relation_property_id)
            if isinstance(target_property_id, str):
                target_property_id = UUID(target_property_id)

            return (relation_property_id, target_property_id)

        except RollupCalculationError:
            raise
        except Exception as e:
            logger.error(f"Error getting rollup dependencies: {e}", exc_info=True)
            raise RollupCalculationError(f"Failed to get rollup dependencies: {str(e)}")

    async def validate_rollup_config(self, rollup_config: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate rollup configuration.

        Args:
            rollup_config: Rollup configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not rollup_config or not isinstance(rollup_config, dict):
                return (False, "Rollup config must be a dictionary")

            # Check required fields
            relation_property_id = rollup_config.get("relation_property_id")
            target_property_id = rollup_config.get("target_property_id")
            function = rollup_config.get("function")

            if not relation_property_id:
                return (False, "Missing required field: relation_property_id")

            if not target_property_id:
                return (False, "Missing required field: target_property_id")

            if not function:
                return (False, "Missing required field: function")

            # Validate function name
            valid_functions = {
                "count",
                "count_values",
                "count_unique_values",
                "count_empty",
                "count_not_empty",
                "percent_empty",
                "percent_not_empty",
                "sum",
                "average",
                "median",
                "min",
                "max",
                "range",
                "show_original",
            }

            if function.lower() not in valid_functions:
                return (False, f"Unknown rollup function: {function}")

            # Validate UUIDs
            try:
                if isinstance(relation_property_id, str):
                    UUID(relation_property_id)
                if isinstance(target_property_id, str):
                    UUID(target_property_id)
            except ValueError as e:
                return (False, f"Invalid UUID in config: {str(e)}")

            return (True, None)

        except Exception as e:
            return (False, f"Validation error: {str(e)}")
