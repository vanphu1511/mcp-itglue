"""Session-based HTTP client for IT Glue internal APIs.

This client uses session cookies and XSRF tokens for the internal
web API endpoints that aren't accessible via the public API.

Currently used for:
- Document content operations (/{org_id}/docs/{doc_id}/versions/)

For public API operations, use the regular ITGlueClient (API key)
or ITGlueJWTClient (JWT token) instead.
"""

import httpx
import time
from typing import Any

from .config import logger
from .session_auth import get_session, get_cached_session, ITGlueSession


class SessionClientError(Exception):
    """Error from session-authenticated API call."""
    
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ITGlueSessionClient:
    """
    HTTP client for IT Glue internal web APIs using session authentication.
    
    This client is specifically for operations that require the internal
    web API (like document content updates). For most operations, use
    the regular API key-based ITGlueClient or JWT-based ITGlueJWTClient.
    
    Usage:
        client = ITGlueSessionClient()
        
        # This will prompt for browser auth if no cached session
        result = await client.update_document_content(
            organization_id=123,
            document_id=456,
            name="My Doc",
            content="<p>Hello world</p>",
        )
    """
    
    def __init__(self):
        self._session: ITGlueSession | None = None
        self._http_client: httpx.AsyncClient | None = None
    
    async def _ensure_session(self, auto_refresh: bool = True) -> ITGlueSession:
        """Ensure we have a valid session."""
        if self._session is not None:
            return self._session
        
        # Try loading from cache
        cached = get_cached_session()
        if cached is not None:
            self._session = cached
            return self._session
        
        if not auto_refresh:
            raise SessionClientError(
                "No valid session available. "
                "Run capture_session.sh to authenticate."
            )
        
        logger.info("No valid session, initiating browser authentication...")
        self._session = await get_session()
        return self._session

    def has_valid_session(self) -> bool:
        """
        Check if we have cached session data.
        
        Note: This doesn't validate server-side - the session could still
        be expired on IT Glue's end. Operations will fail with auth errors
        if the session has expired.
        
        Returns:
            True if we have cached session data, False otherwise
        """
        cached = get_cached_session()
        return cached is not None and bool(cached.xsrf_token)
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with session cookies."""
        session = await self._ensure_session()
        
        if self._http_client is None or self._http_client.is_closed:
            # Convert Playwright cookies to httpx format
            cookies = httpx.Cookies()
            for cookie in session.cookies:
                cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain", ""),
                    path=cookie.get("path", "/"),
                )
            
            self._http_client = httpx.AsyncClient(
                base_url=session.base_url,
                cookies=cookies,
                timeout=30.0,
            )
        
        return self._http_client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
    
    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        auto_refresh: bool = True,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to the internal web API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., "/{org_id}/docs/{doc_id}/versions/")
            json_data: JSON body data
            auto_refresh: Auto-capture session if needed
        
        Returns:
            Parsed JSON response
        """
        session = await self._ensure_session(auto_refresh)
        client = await self._get_http_client()
        
        headers = {
            "X-XSRF-TOKEN": session.xsrf_token,
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain",
        }
        
        logger.debug(f"Session API request: {method} {endpoint}")
        
        response = await client.request(
            method=method,
            url=endpoint,
            headers=headers,
            json=json_data,
        )
        
        if response.status_code >= 400:
            error_body = None
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            
            raise SessionClientError(
                f"API error {response.status_code}: {error_body}",
                status_code=response.status_code,
                response_body=error_body,
            )
        
        if response.status_code == 204 or not response.content:
            return {}
        
        return response.json()
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        auto_refresh: bool = True,
    ) -> dict[str, Any]:
        """
        Upload a file to IT Glue.
        
        This uploads a file to the /attachments endpoint, which creates
        it as a GlueFile in the Documents section.
        
        Args:
            file_content: Raw file bytes
            filename: Name of the file (e.g., "report.pdf")
            content_type: MIME type (e.g., "application/pdf", "text/markdown")
            auto_refresh: Auto-capture session if needed
        
        Returns:
            Upload response data
        """
        import mimetypes
        
        session = await self._ensure_session(auto_refresh)
        client = await self._get_http_client()
        
        # Auto-detect content type if not specified
        if content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type:
                content_type = guessed_type
        
        # Build multipart form data
        files = {
            "attachment[attachment]": (filename, file_content, content_type)
        }
        
        headers = {
            "X-XSRF-TOKEN": session.xsrf_token,
            "Accept": "application/json, text/plain, */*",
        }
        
        logger.info(f"Uploading file: {filename} ({content_type}, {len(file_content)} bytes)")
        
        response = await client.post(
            "/attachments",
            headers=headers,
            files=files,
        )
        
        if response.status_code >= 400:
            error_body = None
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            
            raise SessionClientError(
                f"Upload error {response.status_code}: {error_body}",
                status_code=response.status_code,
                response_body=error_body,
            )
        
        if response.status_code == 204 or not response.content:
            return {"success": True, "filename": filename}
        
        return response.json()

    async def upload_file_to_organization(
        self,
        organization_id: int,
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        auto_refresh: bool = True,
    ) -> dict[str, Any]:
        """
        Upload a file to a specific organization's Documents.
        
        Args:
            organization_id: Target organization ID
            file_content: Raw file bytes
            filename: Name of the file
            content_type: MIME type
            auto_refresh: Auto-capture session if needed
        
        Returns:
            Upload response data
        """
        import mimetypes
        
        session = await self._ensure_session(auto_refresh)
        client = await self._get_http_client()
        
        # Auto-detect content type
        if content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type:
                content_type = guessed_type
        
        # Build multipart form data with organization context
        files = {
            "attachment[attachment]": (filename, file_content, content_type)
        }
        
        data = {
            "attachment[organization_id]": str(organization_id),
        }
        
        headers = {
            "X-XSRF-TOKEN": session.xsrf_token,
            "Accept": "application/json, text/plain, */*",
        }
        
        logger.info(f"Uploading file to org {organization_id}: {filename} ({content_type}, {len(file_content)} bytes)")
        
        response = await client.post(
            "/attachments",
            headers=headers,
            files=files,
            data=data,
        )
        
        if response.status_code >= 400:
            error_body = None
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            
            raise SessionClientError(
                f"Upload error {response.status_code}: {error_body}",
                status_code=response.status_code,
                response_body=error_body,
            )
        
        if response.status_code == 204 or not response.content:
            return {"success": True, "filename": filename, "organization_id": organization_id}
        
        return response.json()

    # =========================================================================
    # Document Content Operations
    # =========================================================================
    
    async def update_document_content(
        self,
        organization_id: int,
        document_id: int,
        name: str,
        content: str,
        publish: bool = True,
        public: bool = False,
    ) -> dict[str, Any]:
        """
        Update document content using the internal web API.
        
        This creates a single text section with the provided content.
        For more complex documents with multiple sections, use
        update_document_sections() instead.
        
        Args:
            organization_id: Organization ID
            document_id: Document ID
            name: Document name/title
            content: HTML content for the document body
            publish: Whether to publish the document (True) or save as draft
            public: Whether the document is publicly visible
        
        Returns:
            API response data
        """
        # IT Glue uses a sections-based content model
        # For simple content, we create a single Text section
        sections = [
            {
                "resourceType": "Document::Text",
                "sort": 0,
                "content": content,
                "dirty": True,
            }
        ]
        
        return await self.update_document_sections(
            organization_id=organization_id,
            document_id=document_id,
            name=name,
            sections=sections,
            publish=publish,
            public=public,
        )
    
    async def update_document_sections(
        self,
        organization_id: int,
        document_id: int,
        name: str,
        sections: list[dict[str, Any]],
        publish: bool = True,
        public: bool = False,
    ) -> dict[str, Any]:
        """
        Update document with multiple sections using the internal web API.
        
        IT Glue documents can have different section types:
        - Document::Text - Plain text/HTML content
        - Document::Heading - Section heading (has 'level' attribute)
        - Document::Step - Numbered step (has 'number', 'duration' attributes)
        - Document::Gallery - Image gallery
        
        Args:
            organization_id: Organization ID
            document_id: Document ID
            name: Document name/title
            sections: List of section objects
            publish: Whether to publish (True) or save as draft
            public: Whether publicly visible
        
        Returns:
            API response data
        """
        data = {
            "force": True,
            "updatedAt": int(time.time()),
            "name": name,
            "sections": sections,
            "id": document_id,
            "public": public,
            "version": "draft" if not publish else None,
        }
        
        if publish:
            data["publish"] = True
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        endpoint = f"/{organization_id}/docs/{document_id}/versions/"
        
        return await self.request("PUT", endpoint, json_data=data)
    
    async def create_document_with_content(
        self,
        organization_id: int,
        name: str,
        content: str,
        document_folder_id: int | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new document with content.
        
        This is a two-step process:
        1. Create empty document via public API (using JWT client)
        2. Update content via internal web API
        
        Args:
            organization_id: Organization ID
            name: Document name/title
            content: HTML content
            document_folder_id: Optional folder ID
            public: Whether publicly visible
        
        Returns:
            Created document with content
        """
        # Step 1: Create document shell via JWT client
        from .jwt_client import get_jwt_client
        
        jwt_client = get_jwt_client()
        doc_result = await jwt_client.create_document(
            organization_id=organization_id,
            name=name,
            content="",  # Empty - will add via internal API
            document_folder_id=document_folder_id,
            public=public,
        )
        
        document_id = int(doc_result.get("id", 0))
        if not document_id:
            raise SessionClientError("Failed to create document - no ID returned")
        
        # Step 2: Add content via internal API
        await self.update_document_content(
            organization_id=organization_id,
            document_id=document_id,
            name=name,
            content=content,
            publish=True,
            public=public,
        )
        
        # Return the document info
        doc_result["content"] = content
        return doc_result


# =============================================================================
# Global Client Instance
# =============================================================================

_session_client: ITGlueSessionClient | None = None


def get_session_client() -> ITGlueSessionClient:
    """Get the global session client instance."""
    global _session_client
    if _session_client is None:
        _session_client = ITGlueSessionClient()
    return _session_client


def reset_session_client() -> None:
    """Reset the global session client."""
    global _session_client
    _session_client = None
