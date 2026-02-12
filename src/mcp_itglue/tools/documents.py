"""IT Glue Documents tools for MCP.

Documents in IT Glue are files and text content that can be attached to
organizations and other resources. This includes SOPs, runbooks, and
uploaded files.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client
from .output import format_list_output, format_search_output


def _format_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Format a document object for display."""
    attrs = doc.get("attributes", {})
    return {
        "id": doc.get("id"),
        "organization_id": attrs.get("organization-id"),
        "name": attrs.get("name"),
        "content": attrs.get("content"),
        "public": attrs.get("public"),
        "document_folder_id": attrs.get("document-folder-id"),
        "resource_type": attrs.get("resource-type"),
        "resource_id": attrs.get("resource-id"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def _format_document_folder(folder: dict[str, Any]) -> dict[str, Any]:
    """Format a document folder object for display."""
    attrs = folder.get("attributes", {})
    return {
        "id": folder.get("id"),
        "organization_id": attrs.get("organization-id"),
        "name": attrs.get("name"),
        "parent_folder_id": attrs.get("parent-folder-id"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_document_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register document-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_documents(
        organization_id: int | None = None,
        name: str | None = None,
        document_folder_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List documents from IT Glue.

        Args:
            organization_id: Filter by organization ID
            name: Filter by document name (partial match)
            document_folder_id: Filter by folder ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of documents
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if name:
            params["filter[name]"] = name
        if document_folder_id:
            params["filter[document_folder_id]"] = document_folder_id

        # Use nested endpoint if organization_id is provided
        if organization_id:
            endpoint = f"/organizations/{organization_id}/relationships/documents"
        else:
            endpoint = "/documents"

        response = await client.get(endpoint, params)
        documents = response.get("data", [])
        meta = response.get("meta", {})

        return format_list_output(
            items=[_format_document(d) for d in documents],
            entity_type="document",
            list_key="documents",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(documents)),
                "page": page,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_document(document_id: int) -> str:
        """Get a specific document by ID.

        Args:
            document_id: The document ID

        Returns:
            JSON string with document details including content
        """
        response = await client.get(f"/documents/{document_id}")
        doc = response.get("data", {})

        return json.dumps(_format_document(doc), indent=2)

    @mcp.tool()
    async def search_documents(
        query: str,
        organization_id: int | None = None,
        limit: int = 10,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """Search for documents by name.

        Args:
            query: Search query string
            organization_id: Optional organization filter
            limit: Maximum number of results (default 10, max 100)
            output_format: Output format - "full", "compact" (default), or "summary"
            save_to_file: If True, saves full results to a temp file for jq processing

        Returns:
            JSON string with matching documents
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/documents", params)
        documents = response.get("data", [])

        return format_search_output(
            items=[_format_document(d) for d in documents],
            entity_type="document",
            list_key="documents",
            query=query,
            output_format=output_format,
            save_to_file=save_to_file,
        )

    @mcp.tool()
    async def create_document(
        organization_id: int,
        name: str,
        content: str,
        document_folder_id: int | None = None,
        public: bool = False,
    ) -> str:
        """Create a new document in IT Glue.

        Args:
            organization_id: Organization ID (required)
            name: Document name/title (required)
            content: Document content as HTML (required)
            document_folder_id: Optional folder ID to place document in
            public: Whether the document is publicly visible (default False)

        Returns:
            JSON string with the created document
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "name": name,
            "content": content,
            "public": public,
        }

        if document_folder_id:
            attributes["document-folder-id"] = document_folder_id

        data = {
            "data": {
                "type": "documents",
                "attributes": attributes,
            }
        }

        response = await client.post("/documents", data)
        doc = response.get("data", {})

        return json.dumps(_format_document(doc), indent=2)

    @mcp.tool()
    async def delete_document(document_id: int) -> str:
        """Delete a document from IT Glue.

        Args:
            document_id: The document ID to delete

        Returns:
            JSON string with deletion confirmation
        """
        # IT Glue uses bulk delete pattern for documents
        data = {
            "data": [
                {"type": "documents", "attributes": {"id": document_id}}
            ]
        }
        await client.delete("/documents", data)

        return json.dumps({
            "success": True,
            "message": f"Document {document_id} deleted successfully",
        }, indent=2)

    @mcp.tool()
    async def update_document(
        document_id: int,
        name: str | None = None,
        content: str | None = None,
        document_folder_id: int | None = None,
        public: bool | None = None,
    ) -> str:
        """Update an existing document.

        Args:
            document_id: The document ID
            name: New document name
            content: New document content
            document_folder_id: New folder ID
            public: New public visibility status

        Returns:
            JSON string with the updated document
        """
        attributes: dict[str, Any] = {}

        if name:
            attributes["name"] = name
        if content is not None:
            attributes["content"] = content
        if document_folder_id is not None:
            attributes["document-folder-id"] = document_folder_id
        if public is not None:
            attributes["public"] = public

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "documents",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/documents/{document_id}", data)
        doc = response.get("data", {})

        return json.dumps(_format_document(doc), indent=2)

    @mcp.tool()
    async def get_organization_documents(
        organization_id: int,
        folder_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """Get all documents for a specific organization.

        Args:
            organization_id: The organization ID
            folder_id: Optional folder filter
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with the organization's documents
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if folder_id:
            params["filter[document_folder_id]"] = folder_id

        response = await client.get(
            f"/organizations/{organization_id}/relationships/documents", params
        )
        documents = response.get("data", [])
        meta = response.get("meta", {})

        return format_list_output(
            items=[_format_document(d) for d in documents],
            entity_type="document",
            list_key="documents",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "organization_id": organization_id,
                "total_count": meta.get("total-count", len(documents)),
                "page": page,
                "page_size": page_size,
            },
        )

    # =========================================================================
    # Document Folders
    # =========================================================================

    @mcp.tool()
    async def list_document_folders(
        organization_id: int | None = None,
        parent_folder_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List document folders from IT Glue.

        Args:
            organization_id: Filter by organization ID
            parent_folder_id: Filter by parent folder ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of document folders
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if parent_folder_id:
            params["filter[parent_folder_id]"] = parent_folder_id

        response = await client.get("/document_folders", params)
        folders = response.get("data", [])
        meta = response.get("meta", {})

        return format_list_output(
            items=[_format_document_folder(f) for f in folders],
            entity_type="document_folder",
            list_key="document_folders",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(folders)),
                "page": page,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_document_folder(folder_id: int) -> str:
        """Get a specific document folder by ID.

        Args:
            folder_id: The document folder ID

        Returns:
            JSON string with folder details
        """
        response = await client.get(f"/document_folders/{folder_id}")
        folder = response.get("data", {})

        return json.dumps(_format_document_folder(folder), indent=2)


# =============================================================================
# Session-Authenticated Document Tools
# =============================================================================
# These tools use session authentication (cookies + XSRF token) captured from
# browser sessions. Required because:
# 1. API key authentication doesn't persist document content
# 2. JWT authentication also doesn't work for content - IT Glue uses a
#    completely different internal API for document content
#
# The internal API endpoint is: /{org_id}/docs/{doc_id}/versions/
# This uses session cookies and XSRF tokens, not Bearer tokens.


def register_jwt_document_tools(mcp: FastMCP) -> None:
    """Register session-authenticated document tools with the MCP server.

    These tools use session authentication (cookies + XSRF token) captured
    from authenticated browser sessions. This is required for document
    content operations because IT Glue's public API (both API key and JWT)
    doesn't persist document content.

    The internal API uses a sections-based content model where documents
    can have multiple sections of different types (Text, Heading, Step, etc.).

    Args:
        mcp: The FastMCP server instance
    """
    from ..session_client import get_session_client, SessionClientError
    from ..session_auth import (
        get_cached_session,
        clear_session_cache,
        set_keep_browser_open as session_set_keep_browser_open,
        get_keep_browser_open as session_get_keep_browser_open,
        is_browser_open as session_is_browser_open,
        close_browser as session_close_browser,
    )

    @mcp.tool()
    async def session_status() -> str:
        """Check the status of the cached session for document operations.

        Returns information about the currently cached session including
        tenant subdomain and age.

        Note: This checks for cached session data but cannot validate
        server-side session state. If operations fail with auth errors,
        run capture_session.sh to re-authenticate.

        Returns:
            JSON string with session status
        """
        session = get_cached_session()

        if session is None:
            return json.dumps({
                "valid": False,
                "message": "No cached session. Run capture_session.sh to authenticate.",
            }, indent=2)

        # Check age - sessions older than 4 hours might be expired
        age_hours = session.age_seconds / 3600
        warning = None
        if age_hours > 4:
            warning = f"Session is {age_hours:.1f} hours old and may have expired. If operations fail, run capture_session.sh to re-authenticate."

        result = {
            "valid": True,
            "tenant_subdomain": session.tenant_subdomain,
            "base_url": session.base_url,
            "age_seconds": session.age_seconds,
            "age_minutes": session.age_seconds // 60,
            "age_hours": round(age_hours, 1),
            "has_xsrf_token": bool(session.xsrf_token),
            "cookie_count": len(session.cookies),
        }

        if warning:
            result["warning"] = warning

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def session_clear() -> str:
        """Clear the cached session for document operations.

        Use this if you need to re-authenticate or if the session
        is causing issues.

        Returns:
            Confirmation message
        """
        clear_session_cache()
        return json.dumps({
            "success": True,
            "message": "Session cache cleared. Run capture_session.sh to re-authenticate.",
        }, indent=2)

    @mcp.tool()
    async def session_browser_keep_open(enabled: bool) -> str:
        """Enable or disable browser persistence for session authentication.

        When enabled (True), the Chromium browser window stays open after
        capturing session data. This is useful when you have multiple document
        operations - you only need to log in once per session.

        When disabled (False, the default), the browser closes automatically
        after each session capture.

        Note: This is separate from jwt_browser_keep_open which controls
        the Chromium browser for JWT/checklist operations.

        Args:
            enabled: True to keep browser open after auth, False to close it

        Returns:
            Confirmation of the new setting
        """
        session_set_keep_browser_open(enabled)
        return json.dumps({
            "success": True,
            "keep_browser_open": enabled,
            "message": f"Session browser will {'stay open' if enabled else 'close'} after authentication.",
            "hint": "Use session_browser_close to manually close the browser when done." if enabled else None,
        }, indent=2)

    @mcp.tool()
    async def session_browser_status() -> str:
        """Check the current session browser persistence status.

        Returns information about:
        - Whether browser persistence is enabled for session auth
        - Whether a Chromium browser is currently open

        Returns:
            JSON string with browser status
        """
        browser_open = session_is_browser_open()
        keep_open = session_get_keep_browser_open()

        return json.dumps({
            "keep_browser_open_enabled": keep_open,
            "browser_currently_open": browser_open,
            "browser_type": "Chromium",
            "message": (
                "Chromium browser is open and will stay open for subsequent operations."
                if browser_open and keep_open else
                "Chromium browser is open but will close after next operation."
                if browser_open and not keep_open else
                "No Chromium browser currently open. Browser persistence is enabled."
                if not browser_open and keep_open else
                "No Chromium browser currently open. Browser will close after each auth."
            ),
        }, indent=2)

    @mcp.tool()
    async def session_browser_close() -> str:
        """Close the persistent Chromium browser if it's open.

        Use this to manually close the browser when you're done with
        document operations that require session authentication.
        Only needed when browser persistence is enabled.

        Returns:
            Confirmation message
        """
        was_open = session_is_browser_open()
        await session_close_browser()
        return json.dumps({
            "success": True,
            "was_open": was_open,
            "message": "Chromium browser closed." if was_open else "No Chromium browser was open.",
        }, indent=2)

    @mcp.tool()
    async def create_document_jwt(
        organization_id: int,
        name: str,
        content: str,
        document_folder_id: int | None = None,
        public: bool = False,
    ) -> str:
        """Create a new document with content using session authentication.

        This tool uses session authentication (cookies + XSRF token from browser)
        to create documents with content. This is REQUIRED because IT Glue's
        public API doesn't persist document content.

        Two-step process:
        1. Creates document shell via JWT/API
        2. Adds content via internal web API

        If no valid session is cached, this will return an error asking you
        to run the session capture script.

        Args:
            organization_id: Organization ID (required)
            name: Document name/title (required)
            content: Document content as HTML (required)
            document_folder_id: Optional folder ID to place document in
            public: Whether the document is publicly visible (default False)

        Returns:
            JSON string with the created document
        """
        session_client = get_session_client()

        try:
            result = await session_client.create_document_with_content(
                organization_id=organization_id,
                name=name,
                content=content,
                document_folder_id=document_folder_id,
                public=public,
            )

            # Format the result
            formatted = {
                "id": result.get("id"),
                "organization_id": organization_id,
                "name": name,
                "content": content,
                "public": public,
                "document_folder_id": document_folder_id,
            }

            return json.dumps(formatted, indent=2)

        except SessionClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "Run capture_session.sh to authenticate, then retry.",
            }, indent=2)

    @mcp.tool()
    async def upload_file_to_itglue(
        organization_id: int,
        file_path: str,
        filename: str | None = None,
    ) -> str:
        """Upload a file to IT Glue Documents (GlueFiles).

        This uploads a file to an organization's Documents section using
        session authentication. Supports any file type.

        If no valid session is cached, this will return an error asking you
        to run the session capture script.

        Args:
            organization_id: Organization ID to upload to (required)
            file_path: Local path to the file to upload (required)
            filename: Override filename (optional, defaults to original filename)

        Returns:
            JSON string with upload result
        """
        import os
        from pathlib import Path

        session_client = get_session_client()

        # Read the file
        path = Path(file_path)
        if not path.exists():
            return json.dumps({
                "error": f"File not found: {file_path}",
            }, indent=2)

        try:
            file_content = path.read_bytes()
            actual_filename = filename or path.name

            result = await session_client.upload_file_to_organization(
                organization_id=organization_id,
                file_content=file_content,
                filename=actual_filename,
            )

            return json.dumps({
                "success": True,
                "filename": actual_filename,
                "organization_id": organization_id,
                "size_bytes": len(file_content),
                "response": result,
            }, indent=2)

        except SessionClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "Run capture_session.sh to authenticate, then retry.",
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "error": str(e),
            }, indent=2)

    @mcp.tool()
    async def update_document_jwt(
        organization_id: int,
        document_id: int,
        name: str,
        content: str,
        public: bool = False,
    ) -> str:
        """Update an existing document's content using session authentication.

        This tool uses session authentication (cookies + XSRF token from browser)
        to update document content. This is REQUIRED because IT Glue's public
        API doesn't persist document content.

        If no valid session is cached, this will return an error asking you
        to run the session capture script.

        Args:
            organization_id: Organization ID (required - needed for internal API)
            document_id: The document ID (required)
            name: Document name (required - needed for update)
            content: New document content as HTML (required)
            public: Whether the document is publicly visible (default False)

        Returns:
            JSON string with the updated document
        """
        session_client = get_session_client()

        try:
            await session_client.update_document_content(
                organization_id=organization_id,
                document_id=document_id,
                name=name,
                content=content,
                publish=True,
                public=public,
            )

            return json.dumps({
                "success": True,
                "id": document_id,
                "organization_id": organization_id,
                "name": name,
                "content": content,
                "public": public,
            }, indent=2)

        except SessionClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "Run capture_session.sh to authenticate, then retry.",
            }, indent=2)

    @mcp.tool()
    async def upload_file_to_itglue(
        organization_id: int,
        file_path: str,
        filename: str | None = None,
    ) -> str:
        """Upload a file to IT Glue Documents (GlueFiles).

        This uploads a file to an organization's Documents section using
        session authentication. Supports any file type.

        If no valid session is cached, this will return an error asking you
        to run the session capture script.

        Args:
            organization_id: Organization ID to upload to (required)
            file_path: Local path to the file to upload (required)
            filename: Override filename (optional, defaults to original filename)

        Returns:
            JSON string with upload result
        """
        import os
        from pathlib import Path

        session_client = get_session_client()

        # Read the file
        path = Path(file_path)
        if not path.exists():
            return json.dumps({
                "error": f"File not found: {file_path}",
            }, indent=2)

        try:
            file_content = path.read_bytes()
            actual_filename = filename or path.name

            result = await session_client.upload_file_to_organization(
                organization_id=organization_id,
                file_content=file_content,
                filename=actual_filename,
            )

            return json.dumps({
                "success": True,
                "filename": actual_filename,
                "organization_id": organization_id,
                "size_bytes": len(file_content),
                "response": result,
            }, indent=2)

        except SessionClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "Run capture_session.sh to authenticate, then retry.",
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "error": str(e),
            }, indent=2)
