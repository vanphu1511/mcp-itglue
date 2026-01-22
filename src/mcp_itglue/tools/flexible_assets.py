"""IT Glue Flexible Assets tools for MCP.

Flexible Assets are IT Glue's primary custom documentation mechanism,
allowing users to define custom schemas (types) and create instances
that store structured data like server documentation, network diagrams,
vendor contacts, etc.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


def _format_flexible_asset_type(fat: dict[str, Any]) -> dict[str, Any]:
    """Format a flexible asset type object for display."""
    attrs = fat.get("attributes", {})
    return {
        "id": fat.get("id"),
        "name": attrs.get("name"),
        "description": attrs.get("description"),
        "icon": attrs.get("icon"),
        "enabled": attrs.get("enabled"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def _format_flexible_asset_field(field: dict[str, Any]) -> dict[str, Any]:
    """Format a flexible asset field definition."""
    attrs = field.get("attributes", {})
    return {
        "id": field.get("id"),
        "flexible_asset_type_id": attrs.get("flexible-asset-type-id"),
        "name": attrs.get("name"),
        "kind": attrs.get("kind"),
        "hint": attrs.get("hint"),
        "required": attrs.get("required"),
        "options": attrs.get("options"),
        "default_value": attrs.get("default-value"),
        "show_in_list": attrs.get("show-in-list"),
        "use_for_title": attrs.get("use-for-title"),
    }


def _format_flexible_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Format a flexible asset instance for display."""
    attrs = asset.get("attributes", {})
    return {
        "id": asset.get("id"),
        "organization_id": attrs.get("organization-id"),
        "flexible_asset_type_id": attrs.get("flexible-asset-type-id"),
        "name": attrs.get("name"),
        "traits": attrs.get("traits", {}),
        "archived": attrs.get("archived"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_flexible_asset_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register flexible asset tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    # =========================================================================
    # Flexible Asset Types (Schemas)
    # =========================================================================

    @mcp.tool()
    async def list_flexible_asset_types(
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all flexible asset type definitions (schemas).

        Flexible asset types define the structure/schema for custom documentation
        like "Server Documentation", "Network Diagrams", "Vendor Contacts", etc.

        Args:
            enabled: Filter by enabled status
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of flexible asset types
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if enabled is not None:
            params["filter[enabled]"] = str(enabled).lower()

        response = await client.get("/flexible_asset_types", params)
        types = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "flexible_asset_types": [_format_flexible_asset_type(t) for t in types],
            "total_count": meta.get("total-count", len(types)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_flexible_asset_type(type_id: int, include_fields: bool = True) -> str:
        """Get a specific flexible asset type by ID.

        Args:
            type_id: The flexible asset type ID
            include_fields: Whether to include field definitions

        Returns:
            JSON string with the flexible asset type details
        """
        params = {}
        if include_fields:
            params["include"] = "flexible_asset_fields"

        response = await client.get(f"/flexible_asset_types/{type_id}", params)
        fat = response.get("data", {})

        result = _format_flexible_asset_type(fat)

        # Include field definitions if requested
        if include_fields:
            included = response.get("included", [])
            result["fields"] = [
                _format_flexible_asset_field(f)
                for f in included
                if f.get("type") == "flexible_asset_fields"
            ]

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def list_flexible_asset_fields(
        flexible_asset_type_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List field definitions for a flexible asset type.

        Args:
            flexible_asset_type_id: The flexible asset type ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of field definitions
        """
        params: dict[str, Any] = {
            "filter[flexible_asset_type_id]": flexible_asset_type_id,
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        response = await client.get("/flexible_asset_fields", params)
        fields = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "flexible_asset_type_id": flexible_asset_type_id,
            "fields": [_format_flexible_asset_field(f) for f in fields],
            "total_count": meta.get("total-count", len(fields)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Flexible Assets (Instances)
    # =========================================================================

    @mcp.tool()
    async def list_flexible_assets(
        flexible_asset_type_id: int | None = None,
        organization_id: int | None = None,
        name: str | None = None,
        archived: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List flexible asset instances.

        Args:
            flexible_asset_type_id: Filter by flexible asset type
            organization_id: Filter by organization
            name: Filter by name (partial match)
            archived: Filter by archived status
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of flexible assets
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if flexible_asset_type_id:
            params["filter[flexible_asset_type_id]"] = flexible_asset_type_id
        if organization_id:
            params["filter[organization_id]"] = organization_id
        if name:
            params["filter[name]"] = name
        if archived is not None:
            params["filter[archived]"] = str(archived).lower()

        response = await client.get("/flexible_assets", params)
        assets = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "flexible_assets": [_format_flexible_asset(a) for a in assets],
            "total_count": meta.get("total-count", len(assets)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_flexible_asset(asset_id: int) -> str:
        """Get a specific flexible asset by ID.

        Args:
            asset_id: The flexible asset ID

        Returns:
            JSON string with the flexible asset details including all traits
        """
        response = await client.get(f"/flexible_assets/{asset_id}")
        asset = response.get("data", {})

        return json.dumps(_format_flexible_asset(asset), indent=2)

    @mcp.tool()
    async def search_flexible_assets(
        query: str,
        flexible_asset_type_id: int | None = None,
        organization_id: int | None = None,
        limit: int = 10,
    ) -> str:
        """Search for flexible assets by name.

        Args:
            query: Search query string
            flexible_asset_type_id: Optional type filter
            organization_id: Optional organization filter
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching flexible assets
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if flexible_asset_type_id:
            params["filter[flexible_asset_type_id]"] = flexible_asset_type_id
        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/flexible_assets", params)
        assets = response.get("data", [])

        result = {
            "query": query,
            "flexible_assets": [_format_flexible_asset(a) for a in assets],
            "count": len(assets),
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def create_flexible_asset(
        organization_id: int,
        flexible_asset_type_id: int,
        traits: dict[str, Any],
    ) -> str:
        """Create a new flexible asset.

        Args:
            organization_id: Organization ID (required)
            flexible_asset_type_id: Flexible asset type ID (required)
            traits: Dictionary of field values matching the type's schema.
                    Keys should match field names, values should match field types.

        Returns:
            JSON string with the created flexible asset
        """
        data = {
            "data": {
                "type": "flexible_assets",
                "attributes": {
                    "organization-id": organization_id,
                    "flexible-asset-type-id": flexible_asset_type_id,
                    "traits": traits,
                },
            }
        }

        response = await client.post("/flexible_assets", data)
        asset = response.get("data", {})

        return json.dumps(_format_flexible_asset(asset), indent=2)

    @mcp.tool()
    async def update_flexible_asset(
        asset_id: int,
        traits: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> str:
        """Update an existing flexible asset.

        Args:
            asset_id: The flexible asset ID
            traits: Updated field values (merged with existing traits)
            archived: Set archived status

        Returns:
            JSON string with the updated flexible asset
        """
        attributes: dict[str, Any] = {}

        if traits is not None:
            attributes["traits"] = traits
        if archived is not None:
            attributes["archived"] = archived

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "flexible_assets",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/flexible_assets/{asset_id}", data)
        asset = response.get("data", {})

        return json.dumps(_format_flexible_asset(asset), indent=2)

    @mcp.tool()
    async def delete_flexible_asset(asset_id: int) -> str:
        """Delete a flexible asset.

        Args:
            asset_id: The flexible asset ID

        Returns:
            JSON string with deletion confirmation
        """
        await client.delete(f"/flexible_assets/{asset_id}")

        return json.dumps({
            "success": True,
            "message": f"Flexible asset {asset_id} deleted successfully",
        }, indent=2)

    @mcp.tool()
    async def get_organization_flexible_assets(
        organization_id: int,
        flexible_asset_type_id: int | None = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """Get all flexible assets for an organization.

        Args:
            organization_id: The organization ID
            flexible_asset_type_id: Optional filter by type
            include_archived: Whether to include archived assets
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with the organization's flexible assets
        """
        params: dict[str, Any] = {
            "filter[organization_id]": organization_id,
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if flexible_asset_type_id:
            params["filter[flexible_asset_type_id]"] = flexible_asset_type_id
        if not include_archived:
            params["filter[archived]"] = "false"

        response = await client.get("/flexible_assets", params)
        assets = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "organization_id": organization_id,
            "flexible_assets": [_format_flexible_asset(a) for a in assets],
            "total_count": meta.get("total-count", len(assets)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)
