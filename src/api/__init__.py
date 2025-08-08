"""
Web API module for Screen Translator v2.0.
Provides REST API interface for remote translation services.
"""

from .auth import APIAuthenticator
from .middleware import APIMiddleware
from .rate_limiter import RateLimiter
from .routes import APIRoutes
from .web_server import WebAPIServer

__all__ = ["WebAPIServer", "APIRoutes", "APIMiddleware", "APIAuthenticator", "RateLimiter"]
