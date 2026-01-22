"""IT Glue Documents tools for MCP.

Documents in IT Glue are files and text content that can be attached to
organizations and other resources. This includes SOPs, runbooks, and
uploaded files.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


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
    ) -> str:
        """List documents from IT Glue.

        Args:
            organization_id: Filter by organization ID
            name: Filter by document name (partial match)
            document_folder_id: Filter by folder ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

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

        result = {
            "documents": [_format_document(d) for d in documents],
            "total_count": meta.get("total-count", len(documents)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

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
    ) -> str:
        """Search for documents by name.

        Args:
            query: Search query string
            organization_id: Optional organization filter
            limit: Maximum number of results (default 10, max 100)

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

        result = {
            "query": query,
            "documents": [_format_document(d) for d in documents],
            "count": len(documents),
        }

        return json.dumps(result, indent=2)

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
    ) -> str:
        """Get all documents for a specific organization.

        Args:
            organization_id: The organization ID
            folder_id: Optional folder filter
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

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

        result = {
            "organization_id": organization_id,
            "documents": [_format_document(d) for d in documents],
            "total_count": meta.get("total-count", len(documents)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Document Folders
    # =========================================================================

    @mcp.tool()
    async def list_document_folders(
        organization_id: int | None = None,
        parent_folder_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List document folders from IT Glue.

        Args:
            organization_id: Filter by organization ID
            parent_folder_id: Filter by parent folder ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

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

        result = {
            "document_folders": [_format_document_folder(f) for f in folders],
            "total_count": meta.get("total-count", len(folders)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

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
