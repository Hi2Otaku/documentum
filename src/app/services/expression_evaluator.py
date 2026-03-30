"""AST-based expression evaluator with whitelist sandbox.

Parses condition expressions using ast.parse(), validates the AST tree
contains only allowed node types, then evaluates safely.
Used for routing condition expressions on flows.
"""
import ast
from typing import Any

ALLOWED_NODES: set[type] = {
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Not,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.UnaryOp, ast.USub, ast.UAdd,
    ast.Constant, ast.Name, ast.Load,
    ast.Tuple,
}


def validate_expression(expr: str) -> None:
    """Raise ValueError if expression uses disallowed AST constructs.

    Allowed: comparisons, boolean ops, arithmetic, string/number literals,
    variable names. Rejected: function calls, attribute access, imports,
    subscripts, comprehensions.
    """
    if not expr or not expr.strip():
        raise ValueError("Expression cannot be empty")
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            raise ValueError(
                f"Disallowed expression node: {type(node).__name__}. "
                f"Only comparisons, boolean ops, arithmetic, literals, and variable names are allowed."
            )


def evaluate_expression(expr: str, variables: dict[str, Any]) -> bool:
    """Evaluate a validated expression against process variables.

    Returns True if the expression evaluates to a truthy value, False otherwise.
    Raises ValueError if the expression contains disallowed constructs.
    Raises NameError if a variable referenced in the expression is not in the variables dict.
    """
    validate_expression(expr)
    code = compile(ast.parse(expr.strip(), mode="eval"), "<expr>", "eval")
    result = eval(code, {"__builtins__": {}}, variables)
    return bool(result)
