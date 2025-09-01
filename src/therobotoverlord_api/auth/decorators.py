"""Authentication decorators for marking public endpoints."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Request


def public_endpoint(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark an endpoint as public (no authentication required)."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    # Mark the function as public
    wrapper.__public_endpoint__ = True  # type: ignore[attr-defined]
    return wrapper


def visitor_readable(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark an endpoint as visitor readable (public for GET requests)."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    # Mark the function as visitor readable
    wrapper.__visitor_readable__ = True  # type: ignore[attr-defined]
    return wrapper


def is_public_endpoint(request: Request) -> bool:
    """Check if the current endpoint is marked as public."""
    if not hasattr(request, "route") or not request.route:
        return False

    endpoint = getattr(request.route, "endpoint", None)
    if not endpoint:
        return False

    # Check for public endpoint marker on the endpoint function
    if hasattr(endpoint, "__public_endpoint__"):
        return getattr(endpoint, "__public_endpoint__", False)

    # Check if endpoint has a wrapped function (FastAPI sometimes wraps functions)
    if hasattr(endpoint, "__wrapped__"):
        return getattr(endpoint.__wrapped__, "__public_endpoint__", False)

    return False


def is_visitor_readable(request: Request) -> bool:
    """Check if the current endpoint is marked as visitor readable."""
    if not hasattr(request, "route") or not request.route:
        return False

    endpoint = getattr(request.route, "endpoint", None)
    if not endpoint:
        return False

    # Check for visitor readable marker on the endpoint function
    if hasattr(endpoint, "__visitor_readable__"):
        return getattr(endpoint, "__visitor_readable__", False)

    # Check if endpoint has a wrapped function (FastAPI sometimes wraps functions)
    if hasattr(endpoint, "__wrapped__"):
        return getattr(endpoint.__wrapped__, "__visitor_readable__", False)

    return False
