"""API package for Nuclei AI Template Generator"""

from .v1.endpoints import router
from .middlewares import TokenAuthMiddleware

__all__ = [
    "router",
    "TokenAuthMiddleware",
]