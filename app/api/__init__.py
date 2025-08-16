"""API package for Nuclei AI Template Generator"""

from .v1 import router as v1_router
from .middlewares import TokenAuthMiddleware

__all__ = [
    "v1_router",
    "TokenAuthMiddleware",
]