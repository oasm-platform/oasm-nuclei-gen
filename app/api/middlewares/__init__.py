"""API middlewares for Nuclei AI Template Generator"""

from .auth import TokenAuthMiddleware

__all__ = [
    "TokenAuthMiddleware",
]