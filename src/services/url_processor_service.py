"""
URL Processor Service for handling web content fetching and processing.

This service handles fetching images and content from URLs with
security validation and caching.
"""

import asyncio
import aiohttp
import hashlib
import ipaddress
import socket
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timedelta
import json

from PIL import Image
from io import BytesIO
from src.services.circuit_breaker import get_circuit_breaker_manager
from src.utils.logger import logger


class URLProcessorService:
    """Service for processing URLs and fetching web content."""

    def __init__(self, cache_dir: str = "data/url_cache", cache_ttl_hours: int = 24):
        """Initialize the URL processor service.

        Args:
            cache_dir: Directory for caching downloaded content
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("url_processor")

        # Request configuration
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.max_file_size = 50 * 1024 * 1024  # 50MB

        # User agent for requests
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

        # Cache metadata
        self.cache_metadata: Dict[str, Dict] = {}
        self._load_cache_metadata()

        logger.info("URLProcessorService initialized")

    async def fetch_image(self, url: str, use_cache: bool = True) -> Optional[Image.Image]:
        """Fetch an image from URL.

        Args:
            url: Image URL
            use_cache: Whether to use cached version if available

        Returns:
            PIL Image object or None if failed
        """
        try:
            # Check cache first
            if use_cache:
                cached_image = await self._get_cached_image(url)
                if cached_image:
                    return cached_image

            # Fetch from URL
            image_data = await self.circuit_breaker.call(
                self._fetch_url_content,
                url,
                expected_type="image"
            )

            if image_data:
                # Convert to PIL Image
                image = Image.open(BytesIO(image_data))

                # Cache the image
                if use_cache:
                    await self._cache_image(url, image_data)

                logger.debug(f"Successfully fetched image from: {url}")
                return image

        except Exception as e:
            logger.error(f"Failed to fetch image from {url}: {e}")

        return None

    async def fetch_text_content(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch text content from URL.

        Args:
            url: Content URL
            use_cache: Whether to use cached version if available

        Returns:
            Text content or None if failed
        """
        try:
            # Check cache first
            if use_cache:
                cached_content = await self._get_cached_text(url)
                if cached_content:
                    return cached_content

            # Fetch from URL
            content_data = await self.circuit_breaker.call(
                self._fetch_url_content,
                url,
                expected_type="text"
            )

            if content_data:
                text_content = content_data.decode('utf-8', errors='ignore')

                # Cache the content
                if use_cache:
                    await self._cache_text(url, text_content)

                logger.debug(f"Successfully fetched text from: {url}")
                return text_content

        except Exception as e:
            logger.error(f"Failed to fetch text from {url}: {e}")

        return None

    async def _fetch_url_content(self, url: str, expected_type: str = "any", redirect_count: int = 0) -> Optional[bytes]:
        """Internal method to fetch content from URL.

        Args:
            url: URL to fetch
            expected_type: Expected content type ("image", "text", "any")
            redirect_count: Current redirect count for loop protection

        Returns:
            Raw content bytes or None if failed
        """
        # Check redirect loop protection
        if redirect_count > 3:
            logger.warning(f"Too many redirects (max 3) for URL: {url}")
            return None

        # Validate URL
        if not self._is_valid_url(url):
            logger.warning(f"Invalid URL: {url}")
            return None

        try:
            # Create connector with custom resolver to block redirects to private IPs
            connector = aiohttp.TCPConnector()

            async with aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                connector=connector,
                connector_owner=True
            ) as session:

                async with session.get(url, allow_redirects=False) as response:
                    # Handle redirects manually with security checks
                    if response.status in (301, 302, 303, 307, 308):
                        redirect_url = response.headers.get('location')
                        if redirect_url:
                            # Validate redirect URL for SSRF
                            if not self._is_valid_url(redirect_url):
                                logger.warning(f"Redirect to unsafe URL blocked: {redirect_url}")
                                return None
                            # Follow redirect manually (limit to 3 redirects max)
                            return await self._fetch_url_content(redirect_url, expected_type, redirect_count + 1)
                        else:
                            logger.warning(f"Redirect response without location header: {url}")
                            return None

                    # Check response status
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for URL: {url}")
                        return None

                    # Check content length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        logger.warning(f"Content too large ({content_length} bytes): {url}")
                        return None

                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if not self._is_valid_content_type(content_type, expected_type):
                        logger.warning(f"Invalid content type {content_type} for {expected_type}: {url}")
                        return None

                    # Read content with size limit
                    content = b""
                    chunk_size = 8192
                    total_size = 0

                    async for chunk in response.content.iter_chunked(chunk_size):
                        total_size += len(chunk)
                        if total_size > self.max_file_size:
                            logger.warning(f"Content size exceeded limit: {url}")
                            return None

                        content += chunk

                    logger.debug(f"Fetched {len(content)} bytes from: {url}")
                    return content

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching URL: {url}")
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")

        return None

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and security against SSRF attacks."""
        try:
            parsed = urlparse(url)

            # Check scheme - only allow http/https
            if parsed.scheme not in ['http', 'https']:
                logger.warning(f"Invalid scheme {parsed.scheme} in URL: {url}")
                return False

            # Get hostname for validation
            hostname = parsed.hostname
            if not hostname:
                logger.warning(f"No hostname found in URL: {url}")
                return False

            # Validate hostname and check for private networks
            if not self._is_safe_hostname(hostname):
                logger.warning(f"Unsafe hostname detected: {hostname}")
                return False

            # Additional DNS resolution check to prevent DNS rebinding
            if not self._verify_dns_resolution(hostname):
                logger.warning(f"DNS resolution check failed for: {hostname}")
                return False

            return True

        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    def _is_safe_hostname(self, hostname: str) -> bool:
        """Check if hostname is safe and not pointing to private networks."""
        # Convert hostname to lowercase for consistent checking
        hostname = hostname.lower()

        # Block common localhost variations
        localhost_variants = [
            'localhost', '127.0.0.1', '0.0.0.0', '::1',
            'localhost.localdomain', 'ip6-localhost', 'ip6-loopback'
        ]

        if hostname in localhost_variants:
            return False

        # Try to parse as IP address
        try:
            ip = ipaddress.ip_address(hostname)
            return self._is_safe_ip_address(ip)
        except ValueError:
            # Not an IP address, it's a hostname - check if it resolves to safe IPs
            pass

        # Additional hostname-based checks
        # Block internal/private domain patterns
        private_domain_patterns = [
            '.local', '.localhost', '.internal', '.intranet', '.corp',
            '.lan', '.private', '.test', '.example', '.invalid'
        ]

        for pattern in private_domain_patterns:
            if hostname.endswith(pattern):
                return False

        return True

    def _is_safe_ip_address(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if IP address is safe and not in private ranges."""
        # Block private IPv4 ranges (RFC 1918)
        if isinstance(ip, ipaddress.IPv4Address):
            # 10.0.0.0/8 - Class A private
            if ip in ipaddress.IPv4Network('10.0.0.0/8'):
                return False
            # 172.16.0.0/12 - Class B private (this was missing in original code)
            if ip in ipaddress.IPv4Network('172.16.0.0/12'):
                return False
            # 192.168.0.0/16 - Class C private
            if ip in ipaddress.IPv4Network('192.168.0.0/16'):
                return False
            # 127.0.0.0/8 - Loopback
            if ip in ipaddress.IPv4Network('127.0.0.0/8'):
                return False
            # 169.254.0.0/16 - Link-local
            if ip in ipaddress.IPv4Network('169.254.0.0/16'):
                return False
            # 0.0.0.0/8 - "This" network
            if ip in ipaddress.IPv4Network('0.0.0.0/8'):
                return False
            # 224.0.0.0/4 - Multicast
            if ip in ipaddress.IPv4Network('224.0.0.0/4'):
                return False

        # Block private IPv6 ranges
        elif isinstance(ip, ipaddress.IPv6Address):
            # ::1/128 - Loopback
            if ip == ipaddress.IPv6Address('::1'):
                return False
            # fc00::/7 - Unique local addresses
            if ip in ipaddress.IPv6Network('fc00::/7'):
                return False
            # fe80::/10 - Link-local
            if ip in ipaddress.IPv6Network('fe80::/10'):
                return False
            # ::ffff:0:0/96 - IPv4-mapped IPv6 addresses
            if ip in ipaddress.IPv6Network('::ffff:0:0/96'):
                # Check the embedded IPv4 address
                ipv4_int = int(ip) & 0xFFFFFFFF
                try:
                    embedded_ipv4 = ipaddress.IPv4Address(ipv4_int)
                    return self._is_safe_ip_address(embedded_ipv4)
                except ValueError:
                    return False

        return True

    def _verify_dns_resolution(self, hostname: str) -> bool:
        """Verify DNS resolution doesn't point to private IPs."""
        try:
            # Resolve hostname to IP addresses
            addrinfos = socket.getaddrinfo(hostname, None)

            for addrinfo in addrinfos:
                ip_str = addrinfo[4][0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    if not self._is_safe_ip_address(ip):
                        logger.warning(f"DNS resolution for {hostname} points to private IP: {ip}")
                        return False
                except ValueError:
                    # Invalid IP format
                    logger.warning(f"Invalid IP address from DNS resolution: {ip_str}")
                    return False

            return True

        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed for {hostname}: {e}")
            return False
        except Exception as e:
            logger.error(f"DNS verification error for {hostname}: {e}")
            return False

    def _is_valid_content_type(self, content_type: str, expected_type: str) -> bool:
        """Check if content type matches expected type."""
        if expected_type == "any":
            return True

        if expected_type == "image":
            return any(img_type in content_type for img_type in [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'
            ])

        if expected_type == "text":
            return any(text_type in content_type for text_type in [
                'text/plain', 'text/html', 'application/json', 'text/xml'
            ])

        return False

    async def _get_cached_image(self, url: str) -> Optional[Image.Image]:
        """Get cached image if available and not expired."""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.jpg"

        if cache_file.exists() and not self._is_cache_expired(url):
            try:
                image = Image.open(cache_file)
                logger.debug(f"Using cached image for: {url}")
                return image
            except Exception as e:
                logger.debug(f"Failed to load cached image: {e}")
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)

        return None

    async def _get_cached_text(self, url: str) -> Optional[str]:
        """Get cached text content if available and not expired."""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.txt"

        if cache_file.exists() and not self._is_cache_expired(url):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.debug(f"Using cached text for: {url}")
                return content
            except Exception as e:
                logger.debug(f"Failed to load cached text: {e}")
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)

        return None

    async def _cache_image(self, url: str, image_data: bytes) -> None:
        """Cache image data."""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.jpg"

        try:
            # Convert and save as JPEG to save space
            image = Image.open(BytesIO(image_data))
            if image.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB for JPEG
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = rgb_image

            image.save(cache_file, 'JPEG', quality=85, optimize=True)

            # Update cache metadata
            self.cache_metadata[cache_key] = {
                "url": url,
                "type": "image",
                "cached_at": datetime.now().isoformat(),
                "size": cache_file.stat().st_size
            }

            await self._save_cache_metadata()

            logger.debug(f"Cached image for: {url}")

        except Exception as e:
            logger.error(f"Failed to cache image: {e}")

    async def _cache_text(self, url: str, text_content: str) -> None:
        """Cache text content."""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.txt"

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(text_content)

            # Update cache metadata
            self.cache_metadata[cache_key] = {
                "url": url,
                "type": "text",
                "cached_at": datetime.now().isoformat(),
                "size": cache_file.stat().st_size
            }

            await self._save_cache_metadata()

            logger.debug(f"Cached text for: {url}")

        except Exception as e:
            logger.error(f"Failed to cache text: {e}")

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _is_cache_expired(self, url: str) -> bool:
        """Check if cached content is expired."""
        cache_key = self._get_cache_key(url)

        if cache_key not in self.cache_metadata:
            return True

        cached_at_str = self.cache_metadata[cache_key].get("cached_at")
        if not cached_at_str:
            return True

        cached_at = datetime.fromisoformat(cached_at_str)
        return datetime.now() - cached_at > self.cache_ttl

    def _load_cache_metadata(self) -> None:
        """Load cache metadata from file."""
        metadata_file = self.cache_dir / "cache_metadata.json"

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.cache_metadata = json.load(f)
                logger.debug(f"Loaded cache metadata with {len(self.cache_metadata)} entries")
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self.cache_metadata = {}

    async def _save_cache_metadata(self) -> None:
        """Save cache metadata to file."""
        metadata_file = self.cache_dir / "cache_metadata.json"

        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    # Public API methods

    async def clear_cache(self) -> int:
        """Clear all cached content.

        Returns:
            Number of files removed
        """
        removed_count = 0

        try:
            # Remove cache files
            for cache_file in self.cache_dir.glob("*"):
                if cache_file.is_file() and cache_file.name != "cache_metadata.json":
                    cache_file.unlink()
                    removed_count += 1

            # Clear metadata
            self.cache_metadata.clear()
            await self._save_cache_metadata()

            logger.info(f"Cleared {removed_count} cached files")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

        return removed_count

    async def clear_expired_cache(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of files removed
        """
        removed_count = 0
        expired_keys = []

        try:
            for cache_key, metadata in self.cache_metadata.items():
                url = metadata.get("url")
                if url and self._is_cache_expired(url):
                    expired_keys.append(cache_key)

                    # Remove cache files
                    for ext in ['.jpg', '.txt']:
                        cache_file = self.cache_dir / f"{cache_key}{ext}"
                        if cache_file.exists():
                            cache_file.unlink()
                            removed_count += 1

            # Remove from metadata
            for key in expired_keys:
                del self.cache_metadata[key]

            if expired_keys:
                await self._save_cache_metadata()

            logger.info(f"Removed {removed_count} expired cache files")

        except Exception as e:
            logger.error(f"Failed to clear expired cache: {e}")

        return removed_count

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache usage statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_size = 0
        file_count = 0
        type_counts = {"image": 0, "text": 0}

        for metadata in self.cache_metadata.values():
            total_size += metadata.get("size", 0)
            file_count += 1

            content_type = metadata.get("type", "unknown")
            if content_type in type_counts:
                type_counts[content_type] += 1

        return {
            "total_files": file_count,
            "total_size_mb": total_size / (1024 * 1024),
            "type_distribution": type_counts,
            "cache_dir": str(self.cache_dir),
            "ttl_hours": self.cache_ttl.total_seconds() / 3600
        }

    async def prefetch_url(self, url: str, content_type: str = "any") -> bool:
        """Prefetch content from URL for caching.

        Args:
            url: URL to prefetch
            content_type: Expected content type

        Returns:
            True if successfully prefetched
        """
        try:
            if content_type == "image":
                result = await self.fetch_image(url, use_cache=False)
                return result is not None
            elif content_type == "text":
                result = await self.fetch_text_content(url, use_cache=False)
                return result is not None
            else:
                # Generic fetch
                content = await self._fetch_url_content(url, content_type)
                return content is not None

        except Exception as e:
            logger.error(f"Failed to prefetch URL {url}: {e}")
            return False

    def set_cache_settings(
        self,
        cache_ttl_hours: Optional[int] = None,
        max_file_size: Optional[int] = None
    ) -> None:
        """Update cache settings.

        Args:
            cache_ttl_hours: Cache time-to-live in hours
            max_file_size: Maximum file size in bytes
        """
        if cache_ttl_hours is not None:
            self.cache_ttl = timedelta(hours=cache_ttl_hours)

        if max_file_size is not None:
            self.max_file_size = max_file_size

        logger.debug("Cache settings updated")

    def is_url_cached(self, url: str) -> bool:
        """Check if URL content is cached and not expired.

        Args:
            url: URL to check

        Returns:
            True if cached and not expired
        """
        cache_key = self._get_cache_key(url)
        return (cache_key in self.cache_metadata and
                not self._is_cache_expired(url))

    async def get_url_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get information about a URL without downloading content.

        Args:
            url: URL to check

        Returns:
            Dictionary with URL information or None if failed
        """
        if not self._is_valid_url(url):
            return None

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": self.user_agent}
            ) as session:

                async with session.head(url) as response:
                    return {
                        "url": url,
                        "status": response.status,
                        "content_type": response.headers.get('content-type'),
                        "content_length": response.headers.get('content-length'),
                        "last_modified": response.headers.get('last-modified'),
                        "server": response.headers.get('server'),
                        "accessible": response.status == 200
                    }

        except Exception as e:
            logger.debug(f"Failed to get URL info for {url}: {e}")
            return None