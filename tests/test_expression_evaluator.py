"""Unit tests for AST-based expression evaluator."""
import pytest

from app.services.expression_evaluator import evaluate_expression, validate_expression


class TestValidateExpression:
    def test_valid_comparison(self):
        validate_expression("amount > 100")

    def test_valid_boolean_ops(self):
        validate_expression("amount > 100 and status == 'approved'")

    def test_valid_arithmetic(self):
        validate_expression("x + y > 10")

    def test_valid_string_equality(self):
        validate_expression("department == 'legal'")

    def test_valid_in_operator(self):
        validate_expression("status in ('approved', 'pending')")

    def test_valid_not_operator(self):
        validate_expression("not done")

    def test_valid_complex_boolean(self):
        validate_expression("(a > 1 and b < 2) or c == 3")

    def test_valid_negation(self):
        validate_expression("-x > 0")

    def test_valid_modulo(self):
        validate_expression("x % 2 == 0")

    def test_rejects_function_call(self):
        with pytest.raises(ValueError, match="Disallowed expression node: Call"):
            validate_expression("print('hello')")

    def test_rejects_import(self):
        with pytest.raises(ValueError, match="Disallowed"):
            validate_expression("__import__('os')")

    def test_rejects_attribute_access(self):
        with pytest.raises(ValueError, match="Disallowed expression node: Attribute"):
            validate_expression("os.system")

    def test_rejects_subscript(self):
        with pytest.raises(ValueError, match="Disallowed expression node: Subscript"):
            validate_expression("data['key']")

    def test_rejects_empty_expression(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_expression("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_expression("   ")

    def test_rejects_lambda(self):
        with pytest.raises(ValueError, match="Disallowed"):
            validate_expression("lambda: 1")

    def test_rejects_comprehension(self):
        with pytest.raises(ValueError, match="Disallowed"):
            validate_expression("[x for x in range(10)]")


class TestEvaluateExpression:
    def test_simple_comparison_true(self):
        assert evaluate_expression("amount > 100", {"amount": 200}) is True

    def test_simple_comparison_false(self):
        assert evaluate_expression("amount > 100", {"amount": 50}) is False

    def test_boolean_and(self):
        assert evaluate_expression("x > 5 and y < 10", {"x": 8, "y": 3}) is True

    def test_boolean_and_false(self):
        assert evaluate_expression("x > 5 and y < 10", {"x": 3, "y": 3}) is False

    def test_boolean_or(self):
        assert evaluate_expression("x > 100 or y < 10", {"x": 1, "y": 3}) is True

    def test_boolean_or_false(self):
        assert evaluate_expression("x > 100 or y > 10", {"x": 1, "y": 3}) is False

    def test_string_equality(self):
        assert evaluate_expression("status == 'approved'", {"status": "approved"}) is True

    def test_string_inequality(self):
        assert evaluate_expression("status == 'approved'", {"status": "pending"}) is False

    def test_arithmetic_expression(self):
        assert evaluate_expression("x + y > 10", {"x": 6, "y": 7}) is True

    def test_not_operator(self):
        assert evaluate_expression("not done", {"done": False}) is True

    def test_missing_variable_raises(self):
        with pytest.raises(NameError):
            evaluate_expression("unknown_var > 5", {})

    def test_in_operator(self):
        assert evaluate_expression(
            "status in ('approved', 'pending')", {"status": "pending"}
        ) is True

    def test_in_operator_false(self):
        assert evaluate_expression(
            "status in ('approved', 'pending')", {"status": "rejected"}
        ) is False

    def test_complex_expression(self):
        variables = {"amount": 15000, "department": "legal", "priority": 1}
        assert evaluate_expression(
            "amount > 10000 and department == 'legal'", variables
        ) is True

    def test_returns_bool(self):
        result = evaluate_expression("1 + 1", {})
        assert result is True  # truthy int coerced to bool

    def test_returns_false_for_zero(self):
        result = evaluate_expression("1 - 1", {})
        assert result is False  # zero is falsy

    def test_less_than_or_equal(self):
        assert evaluate_expression("amount <= 1000", {"amount": 500}) is True

    def test_greater_than_or_equal(self):
        assert evaluate_expression("amount >= 1000", {"amount": 1000}) is True

    def test_not_equal(self):
        assert evaluate_expression("status != 'draft'", {"status": "approved"}) is True
