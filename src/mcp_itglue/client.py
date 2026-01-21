"""IT Glue API client with async HTTP support."""

from typing import Any

import httpx

from .config import Settings, get_settings, logger


class ITGlueError(Exception):
    """Base exception for IT Glue API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ITGlueAuthError(ITGlueError):
    """Authentication error."""

    pass


class ITGlueNotFoundError(ITGlueError):
    """Resource not found error."""

    pass


class ITGlueRateLimitError(ITGlueError):
    """Rate limit exceeded error."""

    pass


class ITGlueClient:
    """Async client for IT Glue API."""

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

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle HTTP error responses."""
        status = response.status_code

        try:
            error_data = response.json()
            message = str(error_data.get("errors", [{"detail": response.text}]))
        except Exception:
            message = response.text or f"HTTP {status} error"

        if status == 401:
            raise ITGlueAuthError(f"Authentication failed: {message}", status)
        elif status == 403:
            raise ITGlueAuthError(f"Access forbidden: {message}", status)
        elif status == 404:
            raise ITGlueNotFoundError(f"Resource not found: {message}", status)
        elif status == 429:
            raise ITGlueRateLimitError(
                "Rate limit exceeded. Maximum 3000 requests per 5 minutes.", status
            )
        else:
            raise ITGlueError(f"API error ({status}): {message}", status)

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
            ITGlueError: On API errors
        """
        if not self.settings.is_configured():
            raise ITGlueAuthError(
                "IT Glue API key not configured. Set ITGLUE_API_KEY environment variable."
            )

        client = await self._get_client()

        logger.debug(f"IT Glue API request: {method} {endpoint}")

        response = await client.request(
            method=method,
            url=endpoint,
            params=params,
            json=json_data,
        )

        if response.status_code >= 400:
            self._handle_error(response)

        # Handle empty responses (e.g., 204 No Content)
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", endpoint, params=params)

    async def post(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a POST request."""
        return await self.request("POST", endpoint, json_data=data)

    async def patch(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a PATCH request."""
        return await self.request("PATCH", endpoint, json_data=data)

    async def delete(self, endpoint: str) -> dict[str, Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", endpoint)

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
        params = params or {}
        page_size = page_size or self.settings.default_page_size
        params["page[size]"] = min(page_size, self.settings.max_page_size)
        params["page[number]"] = 1

        all_data = []
        pages_fetched = 0

        while True:
            response = await self.get(endpoint, params)
            data = response.get("data", [])

            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)

            pages_fetched += 1

            # Check if we should stop
            if max_pages and pages_fetched >= max_pages:
                break

            # Check if there are more pages
            meta = response.get("meta", {})
            total_count = meta.get("total-count", 0)

            if len(all_data) >= total_count:
                break

            params["page[number]"] += 1

        return all_data


# Global client instance
_client: ITGlueClient | None = None


def get_client() -> ITGlueClient:
    """Get the global IT Glue client instance."""
    global _client
    if _client is None:
        _client = ITGlueClient()
    return _client
