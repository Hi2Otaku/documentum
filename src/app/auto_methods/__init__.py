"""Auto method registry for automated workflow activities.

Provides a decorator-based registry for registering and discovering
auto methods that can be executed by the Workflow Agent.
"""
from collections.abc import Awaitable, Callable
from typing import Any

from app.auto_methods.context import ActivityContext

# Module-level registry: method_name -> async callable
_registry: dict[str, Callable[[ActivityContext], Awaitable[dict[str, Any] | None]]] = {}


def auto_method(name: str):
    """Decorator to register an async function as an auto method.

    Usage:
        @auto_method("send_email")
        async def send_email(ctx: ActivityContext) -> dict | None:
            ...
    """
    def decorator(func: Callable[[ActivityContext], Awaitable[dict[str, Any] | None]]):
        _registry[name] = func
        return func
    return decorator


def get_auto_method(name: str) -> Callable[[ActivityContext], Awaitable[dict[str, Any] | None]] | None:
    """Return the auto method callable for the given name, or None if not found."""
    return _registry.get(name)


def list_auto_methods() -> list[str]:
    """Return a list of all registered auto method names."""
    return list(_registry.keys())


# Trigger registration of built-in methods
import app.auto_methods.builtin  # noqa: F401, E402
