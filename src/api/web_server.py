import base64

"""
Web API server for Screen Translator v2.0.
Provides HTTP REST API interface for translation services.
"""

import asyncio
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from aiohttp import web
    from aiohttp_cors import ResourceOptions
    from aiohttp_cors import setup as cors_setup

    AIOHTTP_AVAILABLE = True
except ImportError:
    # Fallback to simple HTTP server
    try:
        from http.server import BaseHTTPRequestHandler, HTTPServer  # noqa: F401

        AIOHTTP_AVAILABLE = False
    except ImportError:
        HTTPServer = None
        BaseHTTPRequestHandler = None
        AIOHTTP_AVAILABLE = False

from src.plugins.plugin_manager import PluginManager
from src.services.container import DIContainer
from src.services.ocr_service import OCRService
from src.services.translation_service import TranslationService
from src.utils.logger import logger


@dataclass
class APIConfig:
    """Configuration for the web API server."""

    host: str = "localhost"
    port: int = 8080
    enable_cors: bool = True
    api_key_required: bool = False
    rate_limit_requests: int = 100  # requests per minute
    rate_limit_window: int = 60  # seconds
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    timeout: int = 30  # seconds
    debug: bool = False


@dataclass
class APIResponse:
    """Standard API response format."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class WebAPIServer:
    """Web API server for Screen Translator."""

    def __init__(self, container: DIContainer, config: Optional[APIConfig] = None):
        """
        Initialize web API server.

        Args:
            container: Dependency injection container
            config: API server configuration
        """
        self.container = container
        self.config = config or APIConfig()

        # Services
        self.translation_service: Optional[TranslationService] = None
        self.ocr_service: Optional[OCRService] = None
        self.plugin_manager: Optional[PluginManager] = None

        # Server state
        if AIOHTTP_AVAILABLE:
            self.app: Optional[web.Application] = None
            self.runner: Optional[web.AppRunner] = None
            self.site: Optional[web.TCPSite] = None
        else:
            self.app = None
            self.runner = None
            self.site = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

        # Rate limiting
        self.rate_limiter: Dict[str, List[float]] = {}

        # Request tracking
        self.active_requests = 0
        self.total_requests = 0

        # Initialize services
        self._initialize_services()

        logger.info(f"Web API server initialized on {self.config.host}:{self.config.port}")

    def _initialize_services(self) -> None:
        """Initialize required services from container."""
        try:
            self.translation_service = self.container.get(TranslationService)
            self.ocr_service = self.container.get(OCRService)
            self.plugin_manager = PluginManager()

            logger.debug("API services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize API services: {e}")

    async def start(self) -> bool:
        """
        Start the web API server.

        Returns:
            True if server started successfully
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp not available, cannot start web API server")
            return False

        try:
            # Create aiohttp application
            self.app = web.Application(client_max_size=self.config.max_request_size)

            # Setup middleware
            self._setup_middleware()

            # Setup routes
            self._setup_routes()

            # Setup CORS if enabled
            if self.config.enable_cors:
                self._setup_cors()

            # Create and start runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.config.host, self.config.port)
            await self.site.start()

            self.running = True
            logger.info(f"Web API server started on http://{self.config.host}:{self.config.port}")

            return True

        except Exception as e:
            logger.error(f"Failed to start web API server: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the web API server."""
        self.running = False

        try:
            if self.site:
                await self.site.stop()
                self.site = None

            if self.runner:
                await self.runner.cleanup()
                self.runner = None

            self.app = None

            logger.info("Web API server stopped")

        except Exception as e:
            logger.error(f"Error stopping web API server: {e}")

    def start_in_thread(self) -> bool:
        """
        Start the web API server in a separate thread.

        Returns:
            True if server thread started successfully
        """
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("Web API server thread already running")
            return False

        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self.start())

                # Keep the loop running
                while self.running:
                    loop.run_until_complete(asyncio.sleep(0.1))

            except Exception as e:
                logger.error(f"Web API server thread error: {e}")
            finally:
                loop.run_until_complete(self.stop())
                loop.close()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait a moment for startup
        # TODO: Performance - Consider using asyncio.sleep() for non-blocking delays
        time.sleep(0.5)

        return self.running

    def stop_thread(self) -> None:
        """Stop the web API server thread."""
        self.running = False

        if self.server_thread:
            self.server_thread.join(timeout=5.0)
            self.server_thread = None

    def _setup_middleware(self) -> None:
        """Setup request middleware."""
        if not self.app:
            return

        async def request_logging_middleware(request, handler):
            start_time = time.time()
            self.active_requests += 1
            self.total_requests += 1

            try:
                response = await handler(request)

                duration = time.time() - start_time
                logger.debug(
                    f"API {request.method} {request.path} - {response.status} ({duration:.3f}s)"
                )

                return response

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"API {request.method} {request.path} - ERROR ({duration:.3f}s): {e}")
                raise
            finally:
                self.active_requests -= 1

        async def rate_limiting_middleware(request, handler):
            if not self._check_rate_limit(request):
                return web.json_response(
                    self._create_error_response("Rate limit exceeded"), status=429
                )

            return await handler(request)

        async def auth_middleware(request, handler):
            if self.config.api_key_required:
                if not self._check_api_key(request):
                    return web.json_response(
                        self._create_error_response("Invalid or missing API key"), status=401
                    )

            return await handler(request)

        # Add middleware in reverse order (they wrap each other)
        self.app.middlewares.append(request_logging_middleware)
        self.app.middlewares.append(rate_limiting_middleware)
        self.app.middlewares.append(auth_middleware)

    def _setup_routes(self) -> None:
        """Setup API routes."""
        if not self.app:
            return

        # Health check
        self.app.router.add_get("/", self._handle_health_check)
        self.app.router.add_get("/health", self._handle_health_check)

        # API info
        self.app.router.add_get("/api", self._handle_api_info)
        self.app.router.add_get("/api/status", self._handle_api_status)

        # Translation endpoints
        self.app.router.add_post("/api/translate", self._handle_translate)
        self.app.router.add_post("/api/translate/batch", self._handle_translate_batch)

        # OCR endpoints
        self.app.router.add_post("/api/ocr", self._handle_ocr)
        self.app.router.add_post("/api/ocr/image", self._handle_ocr_image)

        # Combined endpoints
        self.app.router.add_post("/api/ocr-translate", self._handle_ocr_translate)

        # Plugin endpoints
        self.app.router.add_get("/api/plugins", self._handle_get_plugins)
        self.app.router.add_get("/api/plugins/{plugin_type}", self._handle_get_plugins_by_type)

        # Language endpoints
        self.app.router.add_get("/api/languages", self._handle_get_languages)
        self.app.router.add_get("/api/languages/supported", self._handle_get_supported_languages)

    def _setup_cors(self) -> None:
        """Setup CORS configuration."""
        if not self.app:
            return

        try:
            cors = cors_setup(
                self.app,
                defaults={
                    "*": ResourceOptions(
                        allow_credentials=True,
                        expose_headers="*",
                        allow_headers="*",
                        allow_methods="*",
                    )
                },
            )

            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)

        except Exception as e:
            logger.warning(f"Failed to setup CORS: {e}")

    def _check_rate_limit(self, request) -> bool:
        """Check if request is within rate limits."""
        client_ip = request.remote
        current_time = time.time()

        # Clean old requests
        if client_ip in self.rate_limiter:
            self.rate_limiter[client_ip] = [
                req_time
                for req_time in self.rate_limiter[client_ip]
                if current_time - req_time < self.config.rate_limit_window
            ]
        else:
            self.rate_limiter[client_ip] = []

        # Check rate limit
        if len(self.rate_limiter[client_ip]) >= self.config.rate_limit_requests:
            return False

        # Add current request
        self.rate_limiter[client_ip].append(current_time)
        return True

    def _check_api_key(self, request) -> bool:
        """Check API key authentication."""
        # Simple API key check - in production, use proper authentication
        api_key = request.headers.get("X-API-Key") or request.query.get("api_key")

        # For demo purposes, accept any non-empty key
        # In production, validate against stored keys
        return bool(api_key)

    def _create_response(self, data: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
        """Create standard API response."""
        response = APIResponse(success=(error is None), data=data, error=error)
        return asdict(response)

    def _create_error_response(self, error: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Create error response."""
        return self._create_response(error=error, data={"code": code} if code else None)

    # Route handlers
    async def _handle_health_check(self, request) -> web.Response:
        """Handle health check requests."""
        return web.json_response(
            {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "2.0"}
        )

    async def _handle_api_info(self, request) -> web.Response:
        """Handle API info requests."""
        return web.json_response(
            self._create_response(
                {
                    "name": "Screen Translator API",
                    "version": "2.0",
                    "description": "REST API for Screen Translator services",
                    "endpoints": [
                        "/api/translate",
                        "/api/ocr",
                        "/api/ocr-translate",
                        "/api/plugins",
                        "/api/languages",
                    ],
                }
            )
        )

    async def _handle_api_status(self, request) -> web.Response:
        """Handle API status requests."""
        return web.json_response(
            self._create_response(
                {
                    "running": self.running,
                    "active_requests": self.active_requests,
                    "total_requests": self.total_requests,
                    "uptime": time.time() - getattr(self, "_start_time", time.time()),
                    "services": {
                        "translation": self.translation_service is not None,
                        "ocr": self.ocr_service is not None,
                        "plugins": self.plugin_manager is not None,
                    },
                }
            )
        )

    async def _handle_translate(self, request) -> web.Response:
        """Handle text translation requests."""
        try:
            data = await request.json()

            text = data.get("text")
            source_lang = data.get("source_language", "auto")
            target_lang = data.get("target_language", "en")

            if not text:
                return web.json_response(
                    self._create_error_response("Missing 'text' parameter"), status=400
                )

            if not self.translation_service:
                return web.json_response(
                    self._create_error_response("Translation service not available"), status=503
                )

            # Perform translation
            translation = await asyncio.get_event_loop().run_in_executor(
                None, self.translation_service.translate_text, text, source_lang, target_lang
            )

            if translation:
                return web.json_response(
                    self._create_response(
                        {
                            "original_text": translation.original_text,
                            "translated_text": translation.translated_text,
                            "source_language": translation.source_language,
                            "target_language": translation.target_language,
                            "confidence": translation.confidence,
                            "timestamp": translation.timestamp.isoformat(),
                            "cached": translation.cached,
                        }
                    )
                )
            else:
                return web.json_response(
                    self._create_error_response("Translation failed"), status=500
                )

        except Exception as e:
            logger.error(f"Translation API error: {e}")
            return web.json_response(
                self._create_error_response(f"Translation error: {str(e)}"), status=500
            )

    async def _handle_translate_batch(self, request) -> web.Response:
        """Handle batch translation requests."""
        try:
            data = await request.json()

            texts = data.get("texts", [])
            source_lang = data.get("source_language", "auto")
            target_lang = data.get("target_language", "en")

            if not texts or not isinstance(texts, list):
                return web.json_response(
                    self._create_error_response("Missing or invalid 'texts' parameter"), status=400
                )

            if not self.translation_service:
                return web.json_response(
                    self._create_error_response("Translation service not available"), status=503
                )

            # Perform batch translation
            results = []
            for text in texts:
                try:
                    translation = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.translation_service.translate_text,
                        text,
                        source_lang,
                        target_lang,
                    )

                    if translation:
                        results.append(
                            {
                                "original_text": translation.original_text,
                                "translated_text": translation.translated_text,
                                "source_language": translation.source_language,
                                "target_language": translation.target_language,
                                "confidence": translation.confidence,
                                "success": True,
                            }
                        )
                    else:
                        results.append(
                            {"original_text": text, "error": "Translation failed", "success": False}
                        )

                except Exception as e:
                    results.append({"original_text": text, "error": str(e), "success": False})

            return web.json_response(
                self._create_response(
                    {
                        "results": results,
                        "total": len(texts),
                        "successful": sum(1 for r in results if r.get("success")),
                    }
                )
            )

        except Exception as e:
            logger.error(f"Batch translation API error: {e}")
            return web.json_response(
                self._create_error_response(f"Batch translation error: {str(e)}"), status=500
            )

    async def _handle_ocr(self, request) -> web.Response:
        """Handle OCR requests."""
        try:
            # Handle both JSON and multipart requests
            if request.content_type == "application/json":
                data = await request.json()
                image_data = data.get("image_data")
                if isinstance(image_data, str):

                    image_data = base64.b64decode(image_data)
            else:
                # Handle multipart form data
                reader = await request.multipart()
                image_data = None

                async for field in reader:
                    if field.name == "image":
                        # TODO: Performance - Consider async file operations
                        image_data = await field.read()
                        break

            if not image_data:
                return web.json_response(
                    self._create_error_response("Missing image data"), status=400
                )

            if not self.ocr_service:
                return web.json_response(
                    self._create_error_response("OCR service not available"), status=503
                )

            # Perform OCR
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.ocr_service.extract_text, image_data, ["eng"]  # Default to English
            )

            if result:
                text, confidence = result
                return web.json_response(
                    self._create_response(
                        {"text": text, "confidence": confidence, "language": "auto-detected"}
                    )
                )
            else:
                return web.json_response(
                    self._create_error_response("OCR processing failed"), status=500
                )

        except Exception as e:
            logger.error(f"OCR API error: {e}")
            return web.json_response(
                self._create_error_response(f"OCR error: {str(e)}"), status=500
            )

    async def _handle_ocr_image(self, request) -> web.Response:
        """Handle OCR from image file."""
        return await self._handle_ocr(request)

    async def _handle_ocr_translate(self, request) -> web.Response:
        """Handle combined OCR and translation."""
        try:
            # First perform OCR
            ocr_response = await self._handle_ocr(request)

            if ocr_response.status != 200:
                return ocr_response

            # Extract text from OCR response
            ocr_data = await ocr_response.json()
            if not ocr_data.get("success"):
                return ocr_response

            extracted_text = ocr_data["data"]["text"]

            # Get translation parameters
            if request.content_type == "application/json":
                data = await request.json()
            else:
                # For multipart, translation params would be in form fields
                data = {}

            target_lang = data.get("target_language", "en")
            source_lang = data.get("source_language", "auto")

            # Perform translation
            if not self.translation_service:
                return web.json_response(
                    self._create_error_response("Translation service not available"), status=503
                )

            translation = await asyncio.get_event_loop().run_in_executor(
                None,
                self.translation_service.translate_text,
                extracted_text,
                source_lang,
                target_lang,
            )

            if translation:
                return web.json_response(
                    self._create_response(
                        {
                            "ocr": {
                                "text": extracted_text,
                                "confidence": ocr_data["data"]["confidence"],
                            },
                            "translation": {
                                "original_text": translation.original_text,
                                "translated_text": translation.translated_text,
                                "source_language": translation.source_language,
                                "target_language": translation.target_language,
                                "confidence": translation.confidence,
                            },
                        }
                    )
                )
            else:
                return web.json_response(
                    self._create_error_response("Translation failed after OCR"), status=500
                )

        except Exception as e:
            logger.error(f"OCR-Translate API error: {e}")
            return web.json_response(
                self._create_error_response(f"OCR-Translate error: {str(e)}"), status=500
            )

    async def _handle_get_plugins(self, request) -> web.Response:
        """Handle get plugins requests."""
        try:
            if not self.plugin_manager:
                return web.json_response(
                    self._create_error_response("Plugin service not available"), status=503
                )

            plugins = self.plugin_manager.get_available_plugins()

            plugin_data = []
            for plugin in plugins:
                plugin_data.append(
                    {
                        "name": plugin.metadata.name,
                        "version": plugin.metadata.version,
                        "description": plugin.metadata.description,
                        "type": plugin.metadata.plugin_type.value,
                        "enabled": plugin.enabled,
                        "initialized": plugin.initialized,
                    }
                )

            return web.json_response(
                self._create_response({"plugins": plugin_data, "total": len(plugin_data)})
            )

        except Exception as e:
            logger.error(f"Get plugins API error: {e}")
            return web.json_response(
                self._create_error_response(f"Plugin error: {str(e)}"), status=500
            )

    async def _handle_get_plugins_by_type(self, request) -> web.Response:
        """Handle get plugins by type requests."""
        try:
            plugin_type = request.match_info["plugin_type"]

            if not self.plugin_manager:
                return web.json_response(
                    self._create_error_response("Plugin service not available"), status=503
                )

            # Filter plugins by type
            plugins = self.plugin_manager.get_available_plugins()
            filtered_plugins = [
                p for p in plugins if p.metadata.plugin_type.value.lower() == plugin_type.lower()
            ]

            plugin_data = []
            for plugin in filtered_plugins:
                plugin_data.append(
                    {
                        "name": plugin.metadata.name,
                        "version": plugin.metadata.version,
                        "description": plugin.metadata.description,
                        "enabled": plugin.enabled,
                        "initialized": plugin.initialized,
                    }
                )

            return web.json_response(
                self._create_response(
                    {"plugins": plugin_data, "type": plugin_type, "total": len(plugin_data)}
                )
            )

        except Exception as e:
            logger.error(f"Get plugins by type API error: {e}")
            return web.json_response(
                self._create_error_response(f"Plugin error: {str(e)}"), status=500
            )

    async def _handle_get_languages(self, request) -> web.Response:
        """Handle get languages requests."""
        try:
            if not self.translation_service:
                return web.json_response(
                    self._create_error_response("Translation service not available"), status=503
                )

            # Get supported languages from translation service
            languages = self.translation_service.get_supported_languages()

            return web.json_response(
                self._create_response({"languages": languages, "total": len(languages)})
            )

        except Exception as e:
            logger.error(f"Get languages API error: {e}")
            return web.json_response(
                self._create_error_response(f"Languages error: {str(e)}"), status=500
            )

    async def _handle_get_supported_languages(self, request) -> web.Response:
        """Handle get supported languages requests."""
        return await self._handle_get_languages(request)
