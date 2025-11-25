"""
Formula evaluation service for Notion-style database formulas.

This module provides formula evaluation capabilities for computed properties
in databases, supporting mathematical operations, string functions, date
functions, logical operations, and property references.
"""

import logging
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.exceptions import (
    CircularReferenceError,
    FormulaEvaluationError,
    InvalidFormulaError,
)
from ardha.repositories.database_entry_repository import DatabaseEntryRepository

logger = logging.getLogger(__name__)


class FormulaService:
    """
    Service for evaluating formula properties in Notion-style databases.

    Supports mathematical operations, string functions, date functions,
    logical operations, and property references with circular dependency
    detection.

    Attributes:
        db: SQLAlchemy async session for database operations
        entry_repo: DatabaseEntryRepository for data access
        function_registry: Mapping of function names to implementations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize FormulaService with database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.entry_repo = DatabaseEntryRepository(db)
        self._setup_function_registry()

    def _setup_function_registry(self) -> None:
        """Setup registry mapping function names to implementations."""
        self.function_registry = {
            # Mathematical functions
            "add": self._fn_add,
            "subtract": self._fn_subtract,
            "multiply": self._fn_multiply,
            "divide": self._fn_divide,
            "pow": self._fn_pow,
            "sqrt": self._fn_sqrt,
            "abs": self._fn_abs,
            "round": self._fn_round,
            "ceil": self._fn_ceil,
            "floor": self._fn_floor,
            "min": self._fn_min,
            "max": self._fn_max,
            "sum": self._fn_sum,
            # String functions
            "concat": self._fn_concat,
            "length": self._fn_length,
            "upper": self._fn_upper,
            "lower": self._fn_lower,
            "replace": self._fn_replace,
            "substring": self._fn_substring,
            "contains": self._fn_contains,
            # Logical functions
            "if": self._fn_if,
            "and": self._fn_and,
            "or": self._fn_or,
            "not": self._fn_not,
            "empty": self._fn_empty,
            # Date functions
            "now": self._fn_now,
            "date_add": self._fn_date_add,
            "date_subtract": self._fn_date_subtract,
            "date_diff": self._fn_date_diff,
            "format_date": self._fn_format_date,
            "year": self._fn_year,
            "month": self._fn_month,
            "day": self._fn_day,
        }

    async def evaluate_formula(
        self,
        entry_id: UUID,
        formula: str,
        property_id: UUID,
        evaluation_chain: Optional[Set[UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a formula expression for a database entry.

        Args:
            entry_id: UUID of the database entry
            formula: Formula expression to evaluate (e.g., "add(prop('Revenue'), 100)")
            property_id: UUID of the formula property being evaluated
            evaluation_chain: Set of property IDs currently being evaluated (for circular detection)

        Returns:
            Dictionary with 'result' and 'error' keys:
                - Success: {"result": value, "error": None}
                - Failure: {"result": None, "error": "error message"}

        Raises:
            CircularReferenceError: If circular dependency detected
            FormulaEvaluationError: If evaluation fails
        """
        if evaluation_chain is None:
            evaluation_chain = set()

        # Check for circular reference
        if property_id in evaluation_chain:
            chain_ids = " -> ".join(str(pid) for pid in evaluation_chain)
            raise CircularReferenceError(
                f"Circular reference detected: {chain_ids} -> {property_id}",
                property_chain=[str(pid) for pid in evaluation_chain] + [str(property_id)],
            )

        # Add current property to chain
        evaluation_chain = evaluation_chain.copy()
        evaluation_chain.add(property_id)

        try:
            # Parse and evaluate the formula
            result = await self._evaluate_expression(formula, entry_id, evaluation_chain)

            logger.debug(
                f"Successfully evaluated formula for entry {entry_id}, "
                f"property {property_id}: {result}"
            )

            return {"result": result, "error": None}

        except CircularReferenceError:
            raise
        except InvalidFormulaError as e:
            logger.warning(f"Invalid formula for property {property_id}: {e}")
            return {"result": None, "error": str(e)}
        except Exception as e:
            logger.error(
                f"Error evaluating formula for entry {entry_id}, " f"property {property_id}: {e}",
                exc_info=True,
            )
            return {"result": None, "error": f"Evaluation error: {str(e)}"}

    async def parse_formula(self, formula: str) -> Dict:
        """
        Parse formula into abstract syntax tree (AST).

        Args:
            formula: Formula expression to parse

        Returns:
            Dictionary representing the parsed formula structure

        Raises:
            InvalidFormulaError: If formula syntax is invalid
        """
        try:
            # Simple recursive descent parser
            formula = formula.strip()

            # Check for function call pattern: name(args)
            func_pattern = r"^([a-z_]+)\((.*)\)$"
            match = re.match(func_pattern, formula, re.IGNORECASE)

            if match:
                func_name = match.group(1).lower()
                args_str = match.group(2)

                # Parse arguments
                args = await self._parse_arguments(args_str)

                return {"type": "function", "name": func_name, "arguments": args}

            # Check for literal values
            # Number
            try:
                num_val = float(formula)
                return {"type": "literal", "value": num_val, "value_type": "number"}
            except ValueError:
                pass

            # String (quoted)
            if (formula.startswith('"') and formula.endswith('"')) or (
                formula.startswith("'") and formula.endswith("'")
            ):
                str_val = formula[1:-1]
                return {"type": "literal", "value": str_val, "value_type": "string"}

            # Boolean
            if formula.lower() == "true":
                return {"type": "literal", "value": True, "value_type": "boolean"}
            if formula.lower() == "false":
                return {"type": "literal", "value": False, "value_type": "boolean"}

            # If nothing matched, treat as string literal
            return {"type": "literal", "value": formula, "value_type": "string"}

        except Exception as e:
            raise InvalidFormulaError(f"Failed to parse formula: {str(e)}", formula=formula)

    async def _parse_arguments(self, args_str: str) -> List[Dict]:
        """
        Parse function arguments from string.

        Handles nested function calls and various argument types.

        Args:
            args_str: Arguments string (e.g., "1, 2, prop('Name')")

        Returns:
            List of parsed argument dictionaries
        """
        args = []
        current_arg = ""
        paren_depth = 0
        in_quotes = False
        quote_char = None

        for char in args_str:
            if char in ('"', "'") and (not in_quotes or char == quote_char):
                in_quotes = not in_quotes
                quote_char = char if in_quotes else None
                current_arg += char
            elif char == "(" and not in_quotes:
                paren_depth += 1
                current_arg += char
            elif char == ")" and not in_quotes:
                paren_depth -= 1
                current_arg += char
            elif char == "," and paren_depth == 0 and not in_quotes:
                # Argument separator
                if current_arg.strip():
                    args.append(await self.parse_formula(current_arg.strip()))
                current_arg = ""
            else:
                current_arg += char

        # Add last argument
        if current_arg.strip():
            args.append(await self.parse_formula(current_arg.strip()))

        return args

    async def _evaluate_expression(
        self,
        formula: str,
        entry_id: UUID,
        evaluation_chain: Set[UUID],
    ) -> Any:
        """
        Evaluate a parsed formula expression.

        Args:
            formula: Formula expression
            entry_id: UUID of entry being evaluated
            evaluation_chain: Set of properties currently being evaluated

        Returns:
            Evaluated result value
        """
        parsed = await self.parse_formula(formula)

        if parsed["type"] == "literal":
            return parsed["value"]

        if parsed["type"] == "function":
            func_name = parsed["name"]
            args = parsed["arguments"]

            # Special handling for prop() function
            if func_name == "prop":
                if not args or len(args) != 1:
                    raise InvalidFormulaError("prop() requires exactly 1 argument", formula=formula)

                property_name = args[0]["value"]
                return await self.resolve_property_reference(
                    entry_id, property_name, evaluation_chain
                )

            # Get function implementation
            func_impl = self.function_registry.get(func_name)
            if not func_impl:
                raise InvalidFormulaError(f"Unknown function: {func_name}", formula=formula)

            # Evaluate arguments recursively
            evaluated_args = []
            for arg in args:
                if arg["type"] == "literal":
                    evaluated_args.append(arg["value"])
                elif arg["type"] == "function":
                    # Reconstruct formula string for recursive evaluation
                    arg_formula = self._reconstruct_formula(arg)
                    result = await self._evaluate_expression(
                        arg_formula, entry_id, evaluation_chain
                    )
                    evaluated_args.append(result)

            # Execute function with evaluated arguments
            return func_impl(*evaluated_args)

        raise InvalidFormulaError(f"Unknown expression type: {parsed['type']}", formula=formula)

    def _reconstruct_formula(self, parsed: Dict) -> str:
        """
        Reconstruct formula string from parsed structure.

        Args:
            parsed: Parsed formula dictionary

        Returns:
            Formula string
        """
        if parsed["type"] == "literal":
            value = parsed["value"]
            if parsed["value_type"] == "string":
                return f"'{value}'"
            return str(value)

        if parsed["type"] == "function":
            func_name = parsed["name"]
            args = ", ".join(self._reconstruct_formula(arg) for arg in parsed["arguments"])
            return f"{func_name}({args})"

        return ""

    async def resolve_property_reference(
        self,
        entry_id: UUID,
        property_name: str,
        evaluation_chain: Set[UUID],
    ) -> Any:
        """
        Resolve a property reference in a formula.

        Gets the property value from the entry, handling computed properties
        (formulas, rollups) by recursively evaluating them.

        Args:
            entry_id: UUID of the entry
            property_name: Name of the property to reference
            evaluation_chain: Set of properties currently being evaluated

        Returns:
            Property value (can be any type)

        Raises:
            FormulaEvaluationError: If property not found or cannot be resolved
            CircularReferenceError: If circular dependency detected
        """
        try:
            # Get entry with values
            entry = await self.entry_repo.get_by_id(entry_id)
            if not entry:
                raise FormulaEvaluationError(f"Entry {entry_id} not found")

            # Find property by name
            property_obj = None
            property_value = None
            for value in entry.values:
                if value.property and value.property.name == property_name:
                    property_obj = value.property
                    property_value = value.value
                    break

            if not property_obj:
                raise FormulaEvaluationError(f"Property '{property_name}' not found in entry")

            # Handle computed properties
            if property_obj.property_type == "formula":
                # Recursively evaluate formula property
                if property_obj.config and "formula" in property_obj.config:
                    formula_expr = property_obj.config["formula"]
                    result = await self.evaluate_formula(
                        entry_id, formula_expr, property_obj.id, evaluation_chain
                    )
                    if result["error"]:
                        raise FormulaEvaluationError(
                            f"Error evaluating referenced formula "
                            f"'{property_name}': {result['error']}"
                        )
                    return result["result"]

            # Extract value based on property type
            if property_value is None:
                return None

            if isinstance(property_value, dict):
                # Extract actual value based on property type
                if "number" in property_value:
                    return property_value["number"]
                elif "text" in property_value:
                    return property_value["text"]
                elif "checkbox" in property_value:
                    return property_value["checkbox"]
                elif "date" in property_value:
                    date_val = property_value["date"]
                    if isinstance(date_val, dict) and "start" in date_val:
                        return datetime.fromisoformat(date_val["start"].replace("Z", "+00:00"))
                    return date_val
                elif "select" in property_value:
                    return (
                        property_value["select"].get("name") if property_value["select"] else None
                    )
                else:
                    return property_value

            return property_value

        except CircularReferenceError:
            raise
        except Exception as e:
            logger.error(
                f"Error resolving property reference '{property_name}': {e}", exc_info=True
            )
            raise FormulaEvaluationError(f"Failed to resolve property '{property_name}': {str(e)}")

    async def validate_formula_syntax(self, formula: str) -> Tuple[bool, Optional[str]]:
        """
        Validate formula syntax without evaluating it.

        Args:
            formula: Formula expression to validate

        Returns:
            Tuple of (is_valid, error_message)
                - (True, None) if valid
                - (False, error_message) if invalid
        """
        try:
            # Try to parse the formula
            parsed = await self.parse_formula(formula)

            # Validate function names
            if parsed["type"] == "function":
                func_name = parsed["name"]
                if func_name not in self.function_registry and func_name != "prop":
                    return (False, f"Unknown function: {func_name}")

                # Recursively validate arguments
                for arg in parsed["arguments"]:
                    if arg["type"] == "function":
                        arg_formula = self._reconstruct_formula(arg)
                        is_valid, error = await self.validate_formula_syntax(arg_formula)
                        if not is_valid:
                            return (False, error)

            return (True, None)

        except InvalidFormulaError as e:
            return (False, str(e))
        except Exception as e:
            return (False, f"Validation error: {str(e)}")

    async def get_formula_dependencies(
        self,
        database_id: UUID,
        property_id: UUID,
    ) -> List[UUID]:
        """
        Find all properties referenced in a formula.

        Builds dependency graph for determining recalculation order.

        Args:
            database_id: UUID of database containing the property
            property_id: UUID of the formula property

        Returns:
            List of property UUIDs referenced by this formula

        Raises:
            FormulaEvaluationError: If property not found or not a formula
        """
        try:
            from ardha.repositories.database_property_repository import DatabasePropertyRepository

            prop_repo = DatabasePropertyRepository(self.db)
            property_obj = await prop_repo.get_by_id(property_id)

            if not property_obj:
                raise FormulaEvaluationError(f"Property {property_id} not found")

            if property_obj.property_type != "formula":
                return []

            if not property_obj.config or "formula" not in property_obj.config:
                return []

            formula = property_obj.config["formula"]

            # Extract all prop() calls to find dependencies
            dependencies = set()
            prop_pattern = r"prop\(['\"]([^'\"]+)['\"]\)"

            for match in re.finditer(prop_pattern, formula):
                property_name = match.group(1)

                # Find property ID by name in this database
                properties = await prop_repo.get_by_database(database_id)
                for prop in properties:
                    if prop.name == property_name:
                        dependencies.add(prop.id)
                        break

            return list(dependencies)

        except Exception as e:
            logger.error(f"Error getting formula dependencies: {e}", exc_info=True)
            raise FormulaEvaluationError(f"Failed to get dependencies: {str(e)}")

    async def recalculate_entry_formulas(self, entry_id: UUID) -> int:
        """
        Recalculate all formula properties for an entry.

        Evaluates formulas in dependency order to ensure correct results.

        Args:
            entry_id: UUID of entry to recalculate

        Returns:
            Count of formulas recalculated

        Raises:
            FormulaEvaluationError: If recalculation fails
        """
        try:
            entry = await self.entry_repo.get_by_id(entry_id)
            if not entry:
                raise FormulaEvaluationError(f"Entry {entry_id} not found")

            # Get all formula properties for this database
            from ardha.repositories.database_property_repository import DatabasePropertyRepository

            prop_repo = DatabasePropertyRepository(self.db)
            properties = await prop_repo.get_by_database(entry.database_id)

            formula_props = [p for p in properties if p.property_type == "formula"]

            if not formula_props:
                return 0

            # Build dependency graph and topological sort
            # For MVP, just evaluate in order (full implementation would use topological sort)
            count = 0

            for prop in formula_props:
                if prop.config and "formula" in prop.config:
                    formula = prop.config["formula"]

                    result = await self.evaluate_formula(entry_id, formula, prop.id)

                    if result["error"] is None:
                        # Store computed value
                        computed_value = {"formula": {"result": result["result"]}}
                        await self.entry_repo.set_value(
                            entry_id, prop.id, computed_value, entry.created_by_user_id
                        )
                        count += 1

            logger.info(f"Recalculated {count} formulas for entry {entry_id}")
            return count

        except Exception as e:
            logger.error(f"Error recalculating entry formulas: {e}", exc_info=True)
            raise FormulaEvaluationError(f"Failed to recalculate formulas: {str(e)}")

    async def recalculate_database_formulas(self, database_id: UUID) -> int:
        """
        Recalculate all formulas for all entries in a database.

        Batch processes entries for performance.

        Args:
            database_id: UUID of database

        Returns:
            Total count of formulas recalculated

        Raises:
            FormulaEvaluationError: If recalculation fails
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
                    count = await self.recalculate_entry_formulas(entry.id)
                    total_count += count

                offset += batch_size

            logger.info(f"Recalculated {total_count} formulas for database {database_id}")
            return total_count

        except Exception as e:
            logger.error(f"Error recalculating database formulas: {e}", exc_info=True)
            raise FormulaEvaluationError(f"Failed to recalculate database formulas: {str(e)}")

    # ============= Mathematical Functions =============

    def _fn_add(self, a: Any, b: Any) -> float:
        """Add two numbers."""
        return float(a) + float(b)

    def _fn_subtract(self, a: Any, b: Any) -> float:
        """Subtract b from a."""
        return float(a) - float(b)

    def _fn_multiply(self, a: Any, b: Any) -> float:
        """Multiply two numbers."""
        return float(a) * float(b)

    def _fn_divide(self, a: Any, b: Any) -> float:
        """Divide a by b."""
        b_float = float(b)
        if b_float == 0:
            raise FormulaEvaluationError("Division by zero")
        return float(a) / b_float

    def _fn_pow(self, a: Any, b: Any) -> float:
        """Raise a to the power of b."""
        return pow(float(a), float(b))

    def _fn_sqrt(self, a: Any) -> float:
        """Calculate square root."""
        val = float(a)
        if val < 0:
            raise FormulaEvaluationError("Cannot calculate square root of negative number")
        return math.sqrt(val)

    def _fn_abs(self, a: Any) -> float:
        """Calculate absolute value."""
        return abs(float(a))

    def _fn_round(self, a: Any, decimals: Any = 0) -> float:
        """Round to specified decimal places."""
        return round(float(a), int(decimals))

    def _fn_ceil(self, a: Any) -> float:
        """Round up to nearest integer."""
        return math.ceil(float(a))

    def _fn_floor(self, a: Any) -> float:
        """Round down to nearest integer."""
        return math.floor(float(a))

    def _fn_min(self, *values: Any) -> float:
        """Return minimum value."""
        if not values:
            raise FormulaEvaluationError("min() requires at least 1 argument")
        return min(float(v) for v in values)

    def _fn_max(self, *values: Any) -> float:
        """Return maximum value."""
        if not values:
            raise FormulaEvaluationError("max() requires at least 1 argument")
        return max(float(v) for v in values)

    def _fn_sum(self, *values: Any) -> float:
        """Calculate sum of values."""
        return sum(float(v) for v in values)

    # ============= String Functions =============

    def _fn_concat(self, *strings: Any) -> str:
        """Concatenate strings."""
        return "".join(str(s) for s in strings)

    def _fn_length(self, string: Any) -> int:
        """Get string length."""
        return len(str(string))

    def _fn_upper(self, string: Any) -> str:
        """Convert to uppercase."""
        return str(string).upper()

    def _fn_lower(self, string: Any) -> str:
        """Convert to lowercase."""
        return str(string).lower()

    def _fn_replace(self, string: Any, find: Any, replace: Any) -> str:
        """Replace occurrences of substring."""
        return str(string).replace(str(find), str(replace))

    def _fn_substring(self, string: Any, start: Any, length: Any = None) -> str:
        """Extract substring."""
        s = str(string)
        start_idx = int(start)

        if length is None:
            return s[start_idx:]

        return s[start_idx : start_idx + int(length)]

    def _fn_contains(self, string: Any, search: Any) -> bool:
        """Check if string contains substring."""
        return str(search) in str(string)

    # ============= Logical Functions =============

    def _fn_if(self, condition: Any, true_value: Any, false_value: Any) -> Any:
        """Conditional expression."""
        return true_value if self._to_bool(condition) else false_value

    def _fn_and(self, *conditions: Any) -> bool:
        """Logical AND."""
        return all(self._to_bool(c) for c in conditions)

    def _fn_or(self, *conditions: Any) -> bool:
        """Logical OR."""
        return any(self._to_bool(c) for c in conditions)

    def _fn_not(self, condition: Any) -> bool:
        """Logical NOT."""
        return not self._to_bool(condition)

    def _fn_empty(self, value: Any) -> bool:
        """Check if value is empty."""
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and not value:
            return True
        return False

    def _to_bool(self, value: Any) -> bool:
        """Convert value to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() not in ("", "false", "0", "no")
        if isinstance(value, (int, float)):
            return value != 0
        return value is not None

    # ============= Date Functions =============

    def _fn_now(self) -> datetime:
        """Get current datetime."""
        return datetime.utcnow()

    def _fn_date_add(self, date: Any, amount: Any, unit: Any = "days") -> datetime:
        """Add time to date."""
        dt = self._to_datetime(date)
        amount_int = int(amount)
        unit_str = str(unit).lower()

        if unit_str == "days":
            return dt + timedelta(days=amount_int)
        elif unit_str == "hours":
            return dt + timedelta(hours=amount_int)
        elif unit_str == "minutes":
            return dt + timedelta(minutes=amount_int)
        elif unit_str == "weeks":
            return dt + timedelta(weeks=amount_int)
        elif unit_str == "months":
            # Approximate: 30 days per month
            return dt + timedelta(days=amount_int * 30)
        elif unit_str == "years":
            # Approximate: 365 days per year
            return dt + timedelta(days=amount_int * 365)
        else:
            raise FormulaEvaluationError(f"Unknown date unit: {unit_str}")

    def _fn_date_subtract(self, date: Any, amount: Any, unit: Any = "days") -> datetime:
        """Subtract time from date."""
        return self._fn_date_add(date, -int(amount), unit)

    def _fn_date_diff(self, date1: Any, date2: Any, unit: Any = "days") -> float:
        """Calculate difference between dates."""
        dt1 = self._to_datetime(date1)
        dt2 = self._to_datetime(date2)
        diff = dt1 - dt2
        unit_str = str(unit).lower()

        if unit_str == "days":
            return diff.total_seconds() / 86400
        elif unit_str == "hours":
            return diff.total_seconds() / 3600
        elif unit_str == "minutes":
            return diff.total_seconds() / 60
        elif unit_str == "seconds":
            return diff.total_seconds()
        elif unit_str == "weeks":
            return diff.total_seconds() / (86400 * 7)
        elif unit_str == "months":
            # Approximate
            return diff.total_seconds() / (86400 * 30)
        elif unit_str == "years":
            # Approximate
            return diff.total_seconds() / (86400 * 365)
        else:
            raise FormulaEvaluationError(f"Unknown date unit: {unit_str}")

    def _fn_format_date(self, date: Any, format_str: Any = "%Y-%m-%d") -> str:
        """Format date as string."""
        dt = self._to_datetime(date)
        return dt.strftime(str(format_str))

    def _fn_year(self, date: Any) -> int:
        """Extract year from date."""
        dt = self._to_datetime(date)
        return dt.year

    def _fn_month(self, date: Any) -> int:
        """Extract month from date."""
        dt = self._to_datetime(date)
        return dt.month

    def _fn_day(self, date: Any) -> int:
        """Extract day from date."""
        dt = self._to_datetime(date)
        return dt.day

    def _to_datetime(self, value: Any) -> datetime:
        """Convert value to datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise FormulaEvaluationError(f"Invalid date format: {value}")
        raise FormulaEvaluationError(f"Cannot convert to datetime: {type(value)}")
