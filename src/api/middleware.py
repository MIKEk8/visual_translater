"""
Middleware components for Screen Translator API.

This module provides middleware for request processing, logging, and error handling.
"""

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import logger


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure and log request processing time."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and measure timing."""
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log request details
        logger.info(
            f"API Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle uncaught exceptions."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle exceptions."""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled exception in API: {str(e)}", exc_info=True)
            return Response(
                content="Internal server error",
                status_code=500,
                media_type="text/plain",
            )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate request content."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request size and content type."""
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            max_size = 10 * 1024 * 1024  # 10MB limit
            if content_length > max_size:
                return Response(
                    content="Request too large",
                    status_code=413,
                    media_type="text/plain",
                )

        # Process the request
        response = await call_next(request)
        return response


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application.

    Args:
        app: FastAPI application instance
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware (order matters - executed in reverse order)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(TimingMiddleware)


async def log_request_info(request: Request) -> None:
    """
    Log detailed request information for debugging.

    Args:
        request: FastAPI request object
    """
    logger.debug(
        f"Request info - "
        f"Method: {request.method}, "
        f"URL: {request.url}, "
        f"Headers: {dict(request.headers)}, "
        f"Client: {request.client}"
    )


async def add_security_headers(response: Response) -> None:
    """
    Add security headers to response.

    Args:
        response: FastAPI response object
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
