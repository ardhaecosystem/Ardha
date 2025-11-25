"""
Validation test script for FormulaService and RollupService.

This script tests the core functionality of both services including:
- Formula parsing and evaluation
- Mathematical, string, logical, and date functions
- Rollup aggregation functions
- Error handling

Run with: poetry run python test_formula_rollup_services.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ardha.core.exceptions import FormulaEvaluationError
from ardha.services.formula_service import FormulaService
from ardha.services.rollup_service import RollupService


class TestFormulaService:
    """Test suite for FormulaService."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.service = None

    async def setup(self):
        """Setup test service with mocked database."""
        mock_db = AsyncMock()
        self.service = FormulaService(mock_db)
        print("✓ FormulaService initialized")

    async def test_formula_parsing(self):
        """Test formula parsing functionality."""
        print("\n=== Testing Formula Parsing ===")

        # Test simple number
        parsed = await self.service.parse_formula("42")
        assert parsed["type"] == "literal"
        assert parsed["value"] == 42
        print("✓ Parse number literal")

        # Test string
        parsed = await self.service.parse_formula('"hello"')
        assert parsed["type"] == "literal"
        assert parsed["value"] == "hello"
        print("✓ Parse string literal")

        # Test boolean
        parsed = await self.service.parse_formula("true")
        assert parsed["type"] == "literal"
        assert parsed["value"] is True
        print("✓ Parse boolean literal")

        # Test function call
        parsed = await self.service.parse_formula("add(1, 2)")
        assert parsed["type"] == "function"
        assert parsed["name"] == "add"
        assert len(parsed["arguments"]) == 2
        print("✓ Parse function call")

        # Test nested function
        parsed = await self.service.parse_formula("multiply(add(2, 3), 4)")
        assert parsed["type"] == "function"
        assert parsed["name"] == "multiply"
        print("✓ Parse nested function")

        self.passed += 5

    async def test_mathematical_functions(self):
        """Test mathematical functions."""
        print("\n=== Testing Mathematical Functions ===")

        tests = [
            ("add(10, 5)", 15, "Addition"),
            ("subtract(10, 5)", 5, "Subtraction"),
            ("multiply(10, 5)", 50, "Multiplication"),
            ("divide(10, 5)", 2, "Division"),
            ("pow(2, 3)", 8, "Power"),
            ("sqrt(16)", 4, "Square root"),
            ("abs(-5)", 5, "Absolute value"),
            ("round(3.7, 0)", 4, "Round"),
            ("ceil(3.2)", 4, "Ceiling"),
            ("floor(3.8)", 3, "Floor"),
            ("min(5, 2, 8)", 2, "Minimum"),
            ("max(5, 2, 8)", 8, "Maximum"),
            ("sum(1, 2, 3, 4)", 10, "Sum"),
        ]

        for formula, expected, name in tests:
            try:
                # Mock entry_repo for evaluation (won't need it for pure math)
                self.service.entry_repo = AsyncMock()
                result = await self.service._evaluate_expression(formula, uuid4(), set())
                assert result == expected, f"{name} failed: expected {expected}, got {result}"
                print(f"✓ {name}: {formula} = {result}")
                self.passed += 1
            except Exception as e:
                print(f"✗ {name} failed: {e}")
                self.failed += 1

    async def test_string_functions(self):
        """Test string functions."""
        print("\n=== Testing String Functions ===")

        tests = [
            ("concat('Hello', ' ', 'World')", "Hello World", "Concatenation"),
            ("length('Hello')", 5, "Length"),
            ("upper('hello')", "HELLO", "Uppercase"),
            ("lower('HELLO')", "hello", "Lowercase"),
            ("replace('Hello World', 'World', 'Python')", "Hello Python", "Replace"),
            ("substring('Hello', 1, 3)", "ell", "Substring"),
            ("contains('Hello World', 'World')", True, "Contains"),
        ]

        for formula, expected, name in tests:
            try:
                self.service.entry_repo = AsyncMock()
                result = await self.service._evaluate_expression(formula, uuid4(), set())
                assert result == expected, f"{name} failed: expected {expected}, got {result}"
                print(f"✓ {name}: {formula} = {result}")
                self.passed += 1
            except Exception as e:
                print(f"✗ {name} failed: {e}")
                self.failed += 1

    async def test_logical_functions(self):
        """Test logical functions."""
        print("\n=== Testing Logical Functions ===")

        tests = [
            ("if(true, 'yes', 'no')", "yes", "If true"),
            ("if(false, 'yes', 'no')", "no", "If false"),
            ("and(true, true)", True, "AND true"),
            ("and(true, false)", False, "AND false"),
            ("or(false, true)", True, "OR true"),
            ("or(false, false)", False, "OR false"),
            ("not(true)", False, "NOT true"),
            ("not(false)", True, "NOT false"),
            ("empty('')", True, "Empty string"),
        ]

        for formula, expected, name in tests:
            try:
                self.service.entry_repo = AsyncMock()
                result = await self.service._evaluate_expression(formula, uuid4(), set())
                assert result == expected, f"{name} failed: expected {expected}, got {result}"
                print(f"✓ {name}: {formula} = {result}")
                self.passed += 1
            except Exception as e:
                print(f"✗ {name} failed: {e}")
                self.failed += 1

    async def test_date_functions(self):
        """Test date functions."""
        print("\n=== Testing Date Functions ===")

        # Test now()
        result = self.service._fn_now()
        assert isinstance(result, datetime)
        print(f"✓ now() returns datetime: {result}")
        self.passed += 1

        # Test date arithmetic
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        result = self.service._fn_date_add(base_date, 5, "days")
        assert result == datetime(2024, 1, 6, 12, 0, 0)
        print(f"✓ date_add: {base_date} + 5 days = {result}")
        self.passed += 1

        result = self.service._fn_date_subtract(base_date, 3, "days")
        assert result == datetime(2023, 12, 29, 12, 0, 0)
        print(f"✓ date_subtract: {base_date} - 3 days = {result}")
        self.passed += 1

        # Test date diff
        date1 = datetime(2024, 1, 10)
        date2 = datetime(2024, 1, 1)
        result = self.service._fn_date_diff(date1, date2, "days")
        assert result == 9
        print(f"✓ date_diff: {date1} - {date2} = {result} days")
        self.passed += 1

        # Test date formatting
        result = self.service._fn_format_date(base_date, "%Y-%m-%d")
        assert result == "2024-01-01"
        print(f"✓ format_date: {base_date} -> {result}")
        self.passed += 1

        # Test date extraction
        assert self.service._fn_year(base_date) == 2024
        assert self.service._fn_month(base_date) == 1
        assert self.service._fn_day(base_date) == 1
        print(f"✓ Date extraction: year={2024}, month={1}, day={1}")
        self.passed += 1

    async def test_syntax_validation(self):
        """Test formula syntax validation."""
        print("\n=== Testing Syntax Validation ===")

        # Valid formulas
        valid, error = await self.service.validate_formula_syntax("add(1, 2)")
        assert valid is True
        print("✓ Valid formula accepted: add(1, 2)")
        self.passed += 1

        valid, error = await self.service.validate_formula_syntax("concat('a', 'b', 'c')")
        assert valid is True
        print("✓ Valid formula accepted: concat(...)")
        self.passed += 1

        # Invalid function
        valid, error = await self.service.validate_formula_syntax("unknown_func(1)")
        assert valid is False
        assert "Unknown function" in error
        print(f"✓ Invalid function rejected: {error}")
        self.passed += 1

    async def test_error_handling(self):
        """Test error handling."""
        print("\n=== Testing Error Handling ===")

        # Division by zero
        try:
            self.service.entry_repo = AsyncMock()
            await self.service._evaluate_expression("divide(10, 0)", uuid4(), set())
            print("✗ Division by zero should raise error")
            self.failed += 1
        except FormulaEvaluationError as e:
            assert "Division by zero" in str(e)
            print(f"✓ Division by zero handled: {e}")
            self.passed += 1

        # Square root of negative
        try:
            self.service._fn_sqrt(-4)
            print("✗ Negative square root should raise error")
            self.failed += 1
        except FormulaEvaluationError as e:
            assert "negative" in str(e).lower()
            print(f"✓ Negative square root handled: {e}")
            self.passed += 1

        # Min with no arguments
        try:
            self.service._fn_min()
            print("✗ min() with no args should raise error")
            self.failed += 1
        except FormulaEvaluationError as e:
            print(f"✓ min() with no args handled: {e}")
            self.passed += 1

    async def run_all(self):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("FORMULA SERVICE TEST SUITE")
        print("=" * 60)

        await self.setup()
        await self.test_formula_parsing()
        await self.test_mathematical_functions()
        await self.test_string_functions()
        await self.test_logical_functions()
        await self.test_date_functions()
        await self.test_syntax_validation()
        await self.test_error_handling()

        print("\n" + "=" * 60)
        print(f"Formula Service Results: {self.passed} passed, {self.failed} failed")
        print("=" * 60)

        return self.failed == 0


class TestRollupService:
    """Test suite for RollupService."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.service = None

    async def setup(self):
        """Setup test service with mocked database."""
        mock_db = AsyncMock()
        self.service = RollupService(mock_db)
        print("✓ RollupService initialized")

    async def test_aggregation_functions(self):
        """Test rollup aggregation functions."""
        print("\n=== Testing Aggregation Functions ===")

        # Test data
        numeric_values = [10, 20, 30, 40, 50]
        mixed_values = [10, None, 20, "", 30]
        string_values = ["a", "b", "c", "a"]

        tests = [
            ("count", numeric_values, 5, "Count all"),
            ("count_values", mixed_values, 3, "Count non-empty"),
            ("count_unique_values", string_values, 3, "Count unique"),
            ("count_empty", mixed_values, 2, "Count empty"),
            ("count_not_empty", mixed_values, 3, "Count not empty"),
            ("sum", numeric_values, 150, "Sum"),
            ("average", numeric_values, 30, "Average"),
            ("median", numeric_values, 30, "Median"),
            ("min", numeric_values, 10, "Minimum"),
            ("max", numeric_values, 50, "Maximum"),
            ("range", numeric_values, 40, "Range"),
            ("show_original", numeric_values, numeric_values, "Show original"),
        ]

        for function, values, expected, name in tests:
            try:
                result = await self.service.apply_rollup_function(function, values)
                assert result == expected, f"{name} failed: expected {expected}, got {result}"
                print(f"✓ {name}: {function}({len(values)} values) = {result}")
                self.passed += 1
            except Exception as e:
                print(f"✗ {name} failed: {e}")
                self.failed += 1

    async def test_percentage_functions(self):
        """Test percentage rollup functions."""
        print("\n=== Testing Percentage Functions ===")

        mixed_values = [10, None, 20, "", 30, 40]  # 2 empty, 4 non-empty

        # Test percent_empty
        result = await self.service.apply_rollup_function("percent_empty", mixed_values)
        expected = (2 / 6) * 100
        assert abs(result - expected) < 0.01
        print(f"✓ percent_empty: {result:.2f}%")
        self.passed += 1

        # Test percent_not_empty
        result = await self.service.apply_rollup_function("percent_not_empty", mixed_values)
        expected = (4 / 6) * 100
        assert abs(result - expected) < 0.01
        print(f"✓ percent_not_empty: {result:.2f}%")
        self.passed += 1

    async def test_value_extraction(self):
        """Test value extraction from JSON formats."""
        print("\n=== Testing Value Extraction ===")

        # Test number extraction
        value = {"number": 42}
        result = self.service._extract_value_from_json(value)
        assert result == 42
        print(f"✓ Extract number: {value} -> {result}")
        self.passed += 1

        # Test text extraction
        value = {"text": "Hello"}
        result = self.service._extract_value_from_json(value)
        assert result == "Hello"
        print(f"✓ Extract text: {value} -> {result}")
        self.passed += 1

        # Test select extraction
        value = {"select": {"name": "High", "color": "#ff0000"}}
        result = self.service._extract_value_from_json(value)
        assert result == "High"
        print(f"✓ Extract select: {value} -> {result}")
        self.passed += 1

        # Test formula result extraction
        value = {"formula": {"result": 123.45}}
        result = self.service._extract_value_from_json(value)
        assert result == 123.45
        print(f"✓ Extract formula result: {value} -> {result}")
        self.passed += 1

    async def test_numeric_conversion(self):
        """Test numeric value conversion."""
        print("\n=== Testing Numeric Conversion ===")

        # Mixed types
        values = [10, "20", 30.5, None, "not a number", True]
        result = self.service._convert_to_numbers(values)

        # Should extract: 10, 20, 30.5, skip None, skip "not a number", skip True
        assert len(result) == 3
        assert 10.0 in result
        assert 20.0 in result
        assert 30.5 in result
        print(f"✓ Convert mixed values: {values} -> {result}")
        self.passed += 1

    async def test_empty_result_handling(self):
        """Test empty result handling."""
        print("\n=== Testing Empty Result Handling ===")

        # Count returns 0
        result = self.service._get_empty_rollup_result("count")
        assert result["value"] == 0
        assert result["type"] == "number"
        print(f"✓ Empty count: {result}")
        self.passed += 1

        # Min returns None
        result = self.service._get_empty_rollup_result("min")
        assert result["value"] is None
        assert result["type"] == "number"
        print(f"✓ Empty min: {result}")
        self.passed += 1

        # Show original returns empty array
        result = self.service._get_empty_rollup_result("show_original")
        assert result["value"] == []
        assert result["type"] == "array"
        print(f"✓ Empty show_original: {result}")
        self.passed += 1

    async def test_config_validation(self):
        """Test rollup configuration validation."""
        print("\n=== Testing Config Validation ===")

        # Valid config
        config = {
            "relation_property_id": str(uuid4()),
            "target_property_id": str(uuid4()),
            "function": "sum",
        }
        valid, error = await self.service.validate_rollup_config(config)
        assert valid is True
        print("✓ Valid config accepted")
        self.passed += 1

        # Missing field
        config = {"relation_property_id": str(uuid4())}
        valid, error = await self.service.validate_rollup_config(config)
        assert valid is False
        assert "Missing required field" in error
        print(f"✓ Invalid config rejected: {error}")
        self.passed += 1

        # Unknown function
        config = {
            "relation_property_id": str(uuid4()),
            "target_property_id": str(uuid4()),
            "function": "unknown_func",
        }
        valid, error = await self.service.validate_rollup_config(config)
        assert valid is False
        assert "Unknown rollup function" in error
        print(f"✓ Unknown function rejected: {error}")
        self.passed += 1

    async def run_all(self):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("ROLLUP SERVICE TEST SUITE")
        print("=" * 60)

        await self.setup()
        await self.test_aggregation_functions()
        await self.test_percentage_functions()
        await self.test_value_extraction()
        await self.test_numeric_conversion()
        await self.test_empty_result_handling()
        await self.test_config_validation()

        print("\n" + "=" * 60)
        print(f"Rollup Service Results: {self.passed} passed, {self.failed} failed")
        print("=" * 60)

        return self.failed == 0


async def main():
    """Run all test suites."""
    print("\n" + "=" * 60)
    print("FORMULA & ROLLUP SERVICES VALIDATION")
    print("=" * 60)

    # Run formula service tests
    formula_tests = TestFormulaService()
    formula_success = await formula_tests.run_all()

    # Run rollup service tests
    rollup_tests = TestRollupService()
    rollup_success = await rollup_tests.run_all()

    # Final summary
    total_passed = formula_tests.passed + rollup_tests.passed
    total_failed = formula_tests.failed + rollup_tests.failed

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    print(f"Success Rate: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
    print("=" * 60)

    if formula_success and rollup_success:
        print("\n🎉 ALL TESTS PASSED! Services are ready for production.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
