"""IT Glue API client with async HTTP support, rate limiting, and retry logic."""

import asyncio
from typing import Any, AsyncIterator

import httpx

from .config import Settings, get_settings, logger


# =============================================================================
# Error Taxonomy
# =============================================================================


class ITGlueError(Exception):
    """Base exception for IT Glue API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        errors: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []

    def __str__(self) -> str:
        base = super().__str__()
        if self.errors:
            details = "; ".join(
                e.get("detail", str(e)) for e in self.errors if isinstance(e, dict)
            )
            return f"{base} - Details: {details}"
        return base


class ITGlueAuthError(ITGlueError):
    """Authentication or authorization error (401/403)."""

    pass


class ITGlueNotFoundError(ITGlueError):
    """Resource not found (404)."""

    pass


class ITGlueValidationError(ITGlueError):
    """Request validation failed (400/422)."""

    pass


class ITGlueConflictError(ITGlueError):
    """Resource conflict (409)."""

    pass


class ITGlueRateLimitError(ITGlueError):
    """Rate limit exceeded (429). Includes retry_after hint if available."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        retry_after: float | None = None,
        errors: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message, status_code, errors)
        self.retry_after = retry_after


class ITGlueServerError(ITGlueError):
    """Server-side error (5xx)."""

    pass


# =============================================================================
# Client Implementation
# =============================================================================


class ITGlueClient:
    """Async client for IT Glue API with retry logic and rate limit handling."""

    # Retry configuration
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
    BASE_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 60.0  # seconds

    def __init__(self, settings: Settings | None = None):
        """Initialize the IT Glue client.

        Args:
            settings: Optional settings override. Uses environment settings by default.
        """
        self.settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Get default headers for IT Glue API requests."""
        return {
            "x-api-key": self.settings.api_key,
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.api_url,
                headers=self.headers,
                timeout=self.settings.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _parse_error(self, response: httpx.Response) -> tuple[str, list[dict[str, Any]]]:
        """Parse error response to extract message and structured errors."""
        errors: list[dict[str, Any]] = []
        message = f"HTTP {response.status_code}"

        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                errors = error_data.get("errors", [])
                if errors:
                    # Build message from first error
                    first_error = errors[0] if errors else {}
                    title = first_error.get("title", "")
                    detail = first_error.get("detail", "")
                    message = f"{title}: {detail}" if title else detail or message
                else:
                    message = error_data.get("message", message)
        except Exception:
            message = response.text or message

        return message, errors

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise appropriate exception for HTTP error responses."""
        status = response.status_code
        message, errors = self._parse_error(response)

        if status == 400:
            raise ITGlueValidationError(f"Bad request: {message}", status, errors)
        elif status == 401:
            raise ITGlueAuthError(f"Authentication failed: {message}", status, errors)
        elif status == 403:
            raise ITGlueAuthError(f"Access forbidden: {message}", status, errors)
        elif status == 404:
            raise ITGlueNotFoundError(f"Resource not found: {message}", status, errors)
        elif status == 409:
            raise ITGlueConflictError(f"Resource conflict: {message}", status, errors)
        elif status == 422:
            raise ITGlueValidationError(f"Validation failed: {message}", status, errors)
        elif status == 429:
            retry_after = None
            if "Retry-After" in response.headers:
                try:
                    retry_after = float(response.headers["Retry-After"])
                except ValueError:
                    pass
            raise ITGlueRateLimitError(
                "Rate limit exceeded (max 3000 requests per 5 minutes)",
                status,
                retry_after,
                errors,
            )
        elif status >= 500:
            raise ITGlueServerError(f"Server error: {message}", status, errors)
        else:
            raise ITGlueError(f"API error: {message}", status, errors)

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make request with automatic retry for transient failures."""
        client = await self._get_client()
        last_exception: Exception | None = None

        for attempt in range(self.settings.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json_data,
                )

                # Success or non-retryable error
                if response.status_code not in self.RETRY_STATUS_CODES:
                    return response

                # Retryable error - check if we should retry
                if attempt >= self.settings.max_retries:
                    return response

                # Calculate delay
                if response.status_code == 429:
                    # Use Retry-After header if available
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = min(float(retry_after), self.MAX_RETRY_DELAY)
                        except ValueError:
                            delay = self._calculate_backoff(attempt)
                    else:
                        delay = self._calculate_backoff(attempt)
                else:
                    delay = self._calculate_backoff(attempt)

                logger.warning(
                    f"Request failed with {response.status_code}, "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.settings.max_retries + 1})"
                )
                await asyncio.sleep(delay)

            except httpx.TransportError as e:
                last_exception = e
                if attempt >= self.settings.max_retries:
                    raise ITGlueError(f"Network error after {attempt + 1} attempts: {e}")

                delay = self._calculate_backoff(attempt)
                logger.warning(
                    f"Network error: {e}, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{self.settings.max_retries + 1})"
                )
                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        if last_exception:
            raise ITGlueError(f"Request failed: {last_exception}")
        raise ITGlueError("Request failed after all retries")

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.BASE_RETRY_DELAY * (2**attempt)
        return min(delay, self.MAX_RETRY_DELAY)

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request to IT Glue.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data

        Returns:
            Parsed JSON response

        Raises:
            ITGlueError: On API errors (after retries exhausted)
        """
        if not self.settings.is_configured():
            raise ITGlueAuthError(
                "IT Glue API key not configured. Set ITGLUE_API_KEY environment variable."
            )

        logger.debug(f"IT Glue API request: {method} {endpoint}")

        response = await self._request_with_retry(method, endpoint, params, json_data)

        if response.status_code >= 400:
            self._raise_for_status(response)

        # Handle empty responses (e.g., 204 No Content)
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request."""
        return await self.request("POST", endpoint, json_data=data)

    async def patch(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a PATCH request."""
        return await self.request("PATCH", endpoint, json_data=data)

    async def delete(
        self, endpoint: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", endpoint, json_data=data)

    # =========================================================================
    # Pagination Helpers
    # =========================================================================

    async def get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        page_size: int | None = None,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get all results from a paginated endpoint.

        Args:
            endpoint: API endpoint path
            params: Additional query parameters
            page_size: Results per page (default from settings)
            max_pages: Maximum pages to fetch (None for all)

        Returns:
            List of all resource objects
        """
        results = []
        async for item in self.iter_paginated(endpoint, params, page_size, max_pages):
            results.append(item)
        return results

    async def iter_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        page_size: int | None = None,
        max_pages: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Iterate over all results from a paginated endpoint.

        Yields results one at a time, useful for processing large datasets
        without loading everything into memory.

        Args:
            endpoint: API endpoint path
            params: Additional query parameters
            page_size: Results per page (default from settings)
            max_pages: Maximum pages to fetch (None for all)

        Yields:
            Individual resource objects
        """
        params = dict(params) if params else {}
        page_size = page_size or self.settings.default_page_size
        params["page[size]"] = min(page_size, self.settings.max_page_size)
        params["page[number]"] = 1

        total_yielded = 0
        pages_fetched = 0

        while True:
            response = await self.get(endpoint, params)
            data = response.get("data", [])

            if isinstance(data, list):
                for item in data:
                    yield item
                    total_yielded += 1
            else:
                yield data
                total_yielded += 1

            pages_fetched += 1

            # Check if we should stop
            if max_pages and pages_fetched >= max_pages:
                break

            # Check if there are more pages
            meta = response.get("meta", {})
            total_count = meta.get("total-count", 0)

            if total_yielded >= total_count:
                break

            params["page[number]"] += 1

    async def get_all(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience method to get ALL results from an endpoint.

        Uses maximum page size for efficiency. Be cautious with large datasets.

        Args:
            endpoint: API endpoint path
            params: Additional query parameters

        Returns:
            List of all resource objects
        """
        return await self.get_paginated(
            endpoint,
            params,
            page_size=self.settings.max_page_size,
            max_pages=None,
        )


# =============================================================================
# Global Client Instance
# =============================================================================

_client: ITGlueClient | None = None


def get_client() -> ITGlueClient:
    """Get the global IT Glue client instance."""
    global _client
    if _client is None:
        _client = ITGlueClient()
    return _client


def reset_client() -> None:
    """Reset the global client (useful for testing)."""
    global _client
    _client = None
