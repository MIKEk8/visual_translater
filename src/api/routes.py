"""
API routes configuration for Screen Translator v2.0.
Defines REST API endpoints and route handlers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from src.utils.logger import logger


class HTTPMethod(Enum):
    """HTTP methods for API routes."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


@dataclass
class RouteConfig:
    """Configuration for an API route."""

    path: str
    method: HTTPMethod
    handler: str  # Handler method name
    description: str
    parameters: Optional[List[Dict[str, Any]]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = False
    rate_limited: bool = True


class APIRoutes:
    """API routes configuration and management."""

    def __init__(self):
        """Initialize API routes configuration."""
        self.routes: List[RouteConfig] = []
        self._define_routes()

        logger.debug(f"API routes initialized: {len(self.routes)} routes")

    def _define_routes(self) -> None:
        """Define all API routes."""

        # Health and status routes
        self.routes.extend(
            [
                RouteConfig(
                    path="/",
                    method=HTTPMethod.GET,
                    handler="_handle_health_check",
                    description="Basic health check endpoint",
                    rate_limited=False,
                ),
                RouteConfig(
                    path="/health",
                    method=HTTPMethod.GET,
                    handler="_handle_health_check",
                    description="Detailed health check endpoint",
                    rate_limited=False,
                ),
                RouteConfig(
                    path="/api",
                    method=HTTPMethod.GET,
                    handler="_handle_api_info",
                    description="API information and documentation",
                    rate_limited=False,
                ),
                RouteConfig(
                    path="/api/status",
                    method=HTTPMethod.GET,
                    handler="_handle_api_status",
                    description="API server status and metrics",
                    parameters=[],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "running": {"type": "boolean"},
                                    "active_requests": {"type": "integer"},
                                    "total_requests": {"type": "integer"},
                                    "uptime": {"type": "number"},
                                    "services": {
                                        "type": "object",
                                        "properties": {
                                            "translation": {"type": "boolean"},
                                            "ocr": {"type": "boolean"},
                                            "plugins": {"type": "boolean"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                ),
            ]
        )

        # Translation routes
        self.routes.extend(
            [
                RouteConfig(
                    path="/api/translate",
                    method=HTTPMethod.POST,
                    handler="_handle_translate",
                    description="Translate text from source to target language",
                    parameters=[
                        {
                            "name": "text",
                            "type": "string",
                            "required": True,
                            "description": "Text to translate",
                        },
                        {
                            "name": "source_language",
                            "type": "string",
                            "required": False,
                            "default": "auto",
                            "description": "Source language code (auto for auto-detection)",
                        },
                        {
                            "name": "target_language",
                            "type": "string",
                            "required": False,
                            "default": "en",
                            "description": "Target language code",
                        },
                    ],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "original_text": {"type": "string"},
                                    "translated_text": {"type": "string"},
                                    "source_language": {"type": "string"},
                                    "target_language": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "timestamp": {"type": "string"},
                                    "cached": {"type": "boolean"},
                                },
                            },
                        },
                    },
                ),
                RouteConfig(
                    path="/api/translate/batch",
                    method=HTTPMethod.POST,
                    handler="_handle_translate_batch",
                    description="Translate multiple texts in batch",
                    parameters=[
                        {
                            "name": "texts",
                            "type": "array",
                            "items": {"type": "string"},
                            "required": True,
                            "description": "Array of texts to translate",
                        },
                        {
                            "name": "source_language",
                            "type": "string",
                            "required": False,
                            "default": "auto",
                        },
                        {
                            "name": "target_language",
                            "type": "string",
                            "required": False,
                            "default": "en",
                        },
                    ],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "results": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "original_text": {"type": "string"},
                                                "translated_text": {"type": "string"},
                                                "success": {"type": "boolean"},
                                            },
                                        },
                                    },
                                    "total": {"type": "integer"},
                                    "successful": {"type": "integer"},
                                },
                            },
                        },
                    },
                ),
            ]
        )

        # OCR routes
        self.routes.extend(
            [
                RouteConfig(
                    path="/api/ocr",
                    method=HTTPMethod.POST,
                    handler="_handle_ocr",
                    description="Extract text from image using OCR",
                    parameters=[
                        {
                            "name": "image_data",
                            "type": "string",
                            "format": "base64",
                            "required": True,
                            "description": "Base64 encoded image data (JSON) or binary image (multipart)",
                        },
                        {
                            "name": "languages",
                            "type": "array",
                            "items": {"type": "string"},
                            "required": False,
                            "default": ["eng"],
                            "description": "OCR languages to use",
                        },
                    ],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "language": {"type": "string"},
                                },
                            },
                        },
                    },
                ),
                RouteConfig(
                    path="/api/ocr/image",
                    method=HTTPMethod.POST,
                    handler="_handle_ocr_image",
                    description="Extract text from uploaded image file",
                    parameters=[
                        {
                            "name": "image",
                            "type": "file",
                            "required": True,
                            "description": "Image file to process",
                        }
                    ],
                ),
            ]
        )

        # Combined OCR + Translation routes
        self.routes.extend(
            [
                RouteConfig(
                    path="/api/ocr-translate",
                    method=HTTPMethod.POST,
                    handler="_handle_ocr_translate",
                    description="Extract text from image and translate it",
                    parameters=[
                        {
                            "name": "image_data",
                            "type": "string",
                            "format": "base64",
                            "required": True,
                            "description": "Base64 encoded image data",
                        },
                        {
                            "name": "target_language",
                            "type": "string",
                            "required": False,
                            "default": "en",
                        },
                        {
                            "name": "source_language",
                            "type": "string",
                            "required": False,
                            "default": "auto",
                        },
                    ],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "ocr": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"},
                                            "confidence": {"type": "number"},
                                        },
                                    },
                                    "translation": {
                                        "type": "object",
                                        "properties": {
                                            "original_text": {"type": "string"},
                                            "translated_text": {"type": "string"},
                                            "source_language": {"type": "string"},
                                            "target_language": {"type": "string"},
                                            "confidence": {"type": "number"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                )
            ]
        )

        # Plugin routes
        self.routes.extend(
            [
                RouteConfig(
                    path="/api/plugins",
                    method=HTTPMethod.GET,
                    handler="_handle_get_plugins",
                    description="Get list of available plugins",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "plugins": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "version": {"type": "string"},
                                                "description": {"type": "string"},
                                                "type": {"type": "string"},
                                                "enabled": {"type": "boolean"},
                                                "initialized": {"type": "boolean"},
                                            },
                                        },
                                    },
                                    "total": {"type": "integer"},
                                },
                            },
                        },
                    },
                ),
                RouteConfig(
                    path="/api/plugins/{plugin_type}",
                    method=HTTPMethod.GET,
                    handler="_handle_get_plugins_by_type",
                    description="Get plugins filtered by type",
                    parameters=[
                        {
                            "name": "plugin_type",
                            "type": "string",
                            "in": "path",
                            "required": True,
                            "description": "Plugin type (ocr, translation, tts, etc.)",
                        }
                    ],
                ),
            ]
        )

        # Language routes
        self.routes.extend(
            [
                RouteConfig(
                    path="/api/languages",
                    method=HTTPMethod.GET,
                    handler="_handle_get_languages",
                    description="Get supported languages",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {
                                "type": "object",
                                "properties": {
                                    "languages": {"type": "array", "items": {"type": "string"}},
                                    "total": {"type": "integer"},
                                },
                            },
                        },
                    },
                ),
                RouteConfig(
                    path="/api/languages/supported",
                    method=HTTPMethod.GET,
                    handler="_handle_get_supported_languages",
                    description="Get detailed supported languages information",
                ),
            ]
        )

    def get_routes(self) -> List[RouteConfig]:
        """Get all configured routes."""
        return self.routes

    def get_routes_by_method(self, method: HTTPMethod) -> List[RouteConfig]:
        """Get routes filtered by HTTP method."""
        return [route for route in self.routes if route.method == method]

    def get_route_by_path(
        self, path: str, method: Optional[HTTPMethod] = None
    ) -> Optional[RouteConfig]:
        """Get route by path and optionally method."""
        for route in self.routes:
            if route.path == path:
                if method is None or route.method == method:
                    return route
        return None

    def _get_openapi_base_spec(self) -> Dict[str, Any]:
        """Get base OpenAPI specification structure."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Screen Translator API",
                "version": "2.0.0",
                "description": "REST API for Screen Translator services",
            },
            "servers": [
                {"url": "http://localhost:8080", "description": "Local development server"}
            ],
            "paths": {},
        }

    def _create_operation_response_schema(self, route_response_schema) -> Dict[str, Any]:
        """Create response schema for operation."""
        return {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": route_response_schema
                        or {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "data": {"type": "object"},
                            },
                        }
                    }
                },
            },
            "400": {"description": "Bad request"},
            "500": {"description": "Internal server error"},
        }

    def _create_base_operation(self, route) -> Dict[str, Any]:
        """Create base operation structure."""
        return {
            "summary": route.description,
            "operationId": route.handler.lstrip("_"),
            "responses": self._create_operation_response_schema(route.response_schema),
        }

    def _process_route_parameters(self, route, method: str, operation: Dict[str, Any]) -> None:
        """Process route parameters and add to operation."""
        if route.parameters:
            operation["parameters"] = []
            request_body_params = []

            for param in route.parameters:
                if param.get("in") == "path":
                    operation["parameters"].append(
                        {
                            "name": param["name"],
                            "in": "path",
                            "required": param.get("required", True),
                            "schema": {"type": param["type"]},
                            "description": param.get("description", ""),
                        }
                    )
                elif method in ["post", "put", "patch"]:
                    request_body_params.append(param)
                else:
                    operation["parameters"].append(
                        {
                            "name": param["name"],
                            "in": "query",
                            "required": param.get("required", False),
                            "schema": {"type": param["type"]},
                            "description": param.get("description", ""),
                        }
                    )

            if request_body_params:
                self._add_request_body(operation, request_body_params)

        # Add security if required
        if route.auth_required:
            operation["security"] = [{"ApiKeyAuth": []}]

    def _add_request_body(self, operation: Dict[str, Any], request_body_params: list) -> None:
        """Add request body to operation."""
        properties = {}
        required = []

        for param in request_body_params:
            properties[param["name"]] = {"type": param["type"]}
            if param.get("format"):
                properties[param["name"]]["format"] = param["format"]
            if param.get("items"):
                properties[param["name"]]["items"] = param["items"]
            if param.get("default") is not None:
                properties[param["name"]]["default"] = param["default"]

            if param.get("required", False):
                required.append(param["name"])

        operation["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": properties,
                        "required": required if required else None,
                    }
                }
            }
        }

    def get_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI specification for all routes."""
        spec = self._get_openapi_base_spec()

        for route in self.routes:
            path = route.path
            method = route.method.value.lower()

            if path not in spec["paths"]:
                spec["paths"][path] = {}

            operation = self._create_base_operation(route)

            self._process_route_parameters(route, method, operation)
            spec["paths"][path][method] = operation

        # Add security schemes
        spec["components"] = {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        }

        return spec

    def validate_route_config(self, route: RouteConfig) -> List[str]:
        """Validate route configuration and return any errors."""
        errors = []

        if not route.path:
            errors.append("Route path is required")

        if not route.handler:
            errors.append("Route handler is required")

        if not route.description:
            errors.append("Route description is required")

        # Validate path parameters
        if route.parameters:
            path_params = []
            for param in route.parameters:
                if param.get("in") == "path":
                    path_params.append(param["name"])

            # Check if all path parameters are in the route path
            import re

            path_param_pattern = r"\{([^}]+)\}"
            route_path_params = re.findall(path_param_pattern, route.path)

            for param in path_params:
                if param not in route_path_params:
                    errors.append(f"Path parameter '{param}' not found in route path")

        return errors
