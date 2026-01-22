"""IT Glue Related Items tools for MCP.

Related Items allow you to create relationships between different
resources in IT Glue. For example, linking a server to the applications
it hosts, or a contact to the assets they manage.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


# Valid resource types that can be related
VALID_RESOURCE_TYPES = [
    "checklists",
    "checklist-templates",
    "configurations",
    "contacts",
    "documents",
    "domains",
    "flexible-assets",
    "locations",
    "passwords",
    "ssl-certificates",
    "tickets",
]


def _format_related_item(item: dict[str, Any]) -> dict[str, Any]:
    """Format a related item object for display."""
    attrs = item.get("attributes", {})
    return {
        "id": item.get("id"),
        "resource_type": attrs.get("resource-type"),
        "resource_id": attrs.get("resource-id"),
        "resource_url": attrs.get("resource-url"),
        "resource_name": attrs.get("resource-name"),
        "notes": attrs.get("notes"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_related_item_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register related item tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_related_items(
        resource_type: str,
        resource_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List items related to a specific resource.

        Args:
            resource_type: The type of resource (e.g., 'configurations', 'contacts', 'flexible-assets')
            resource_id: The ID of the resource
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of related items

        Valid resource types: checklists, checklist-templates, configurations,
        contacts, documents, domains, flexible-assets, locations, passwords,
        ssl-certificates, tickets
        """
        if resource_type not in VALID_RESOURCE_TYPES:
            return json.dumps({
                "error": f"Invalid resource type: {resource_type}",
                "valid_types": VALID_RESOURCE_TYPES,
            }, indent=2)

        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        endpoint = f"/{resource_type}/{resource_id}/relationships/related_items"
        response = await client.get(endpoint, params)
        items = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "source_type": resource_type,
            "source_id": resource_id,
            "related_items": [_format_related_item(item) for item in items],
            "total_count": meta.get("total-count", len(items)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def create_related_item(
        source_type: str,
        source_id: int,
        destination_type: str,
        destination_id: int,
        notes: str | None = None,
    ) -> str:
        """Create a relationship between two resources.

        Args:
            source_type: The type of the source resource
            source_id: The ID of the source resource
            destination_type: The type of the destination resource
            destination_id: The ID of the destination resource
            notes: Optional notes about the relationship

        Returns:
            JSON string with the created relationship

        Valid resource types: checklists, checklist-templates, configurations,
        contacts, documents, domains, flexible-assets, locations, passwords,
        ssl-certificates, tickets
        """
        if source_type not in VALID_RESOURCE_TYPES:
            return json.dumps({
                "error": f"Invalid source type: {source_type}",
                "valid_types": VALID_RESOURCE_TYPES,
            }, indent=2)

        if destination_type not in VALID_RESOURCE_TYPES:
            return json.dumps({
                "error": f"Invalid destination type: {destination_type}",
                "valid_types": VALID_RESOURCE_TYPES,
            }, indent=2)

        attributes: dict[str, Any] = {
            "resource-type": destination_type,
            "resource-id": destination_id,
        }

        if notes:
            attributes["notes"] = notes

        data = {
            "data": {
                "type": "related_items",
                "attributes": attributes,
            }
        }

        endpoint = f"/{source_type}/{source_id}/relationships/related_items"
        response = await client.post(endpoint, data)
        item = response.get("data", {})

        return json.dumps({
            "success": True,
            "related_item": _format_related_item(item),
            "relationship": {
                "source": {"type": source_type, "id": source_id},
                "destination": {"type": destination_type, "id": destination_id},
            },
        }, indent=2)

    @mcp.tool()
    async def update_related_item(
        source_type: str,
        source_id: int,
        related_item_id: int,
        notes: str | None = None,
    ) -> str:
        """Update a related item (currently only notes can be updated).

        Args:
            source_type: The type of the source resource
            source_id: The ID of the source resource
            related_item_id: The ID of the related item to update
            notes: New notes for the relationship

        Returns:
            JSON string with the updated related item
        """
        if source_type not in VALID_RESOURCE_TYPES:
            return json.dumps({
                "error": f"Invalid source type: {source_type}",
                "valid_types": VALID_RESOURCE_TYPES,
            }, indent=2)

        attributes: dict[str, Any] = {}
        if notes is not None:
            attributes["notes"] = notes

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "related_items",
                "attributes": attributes,
            }
        }

        endpoint = f"/{source_type}/{source_id}/relationships/related_items/{related_item_id}"
        response = await client.patch(endpoint, data)
        item = response.get("data", {})

        return json.dumps(_format_related_item(item), indent=2)

    @mcp.tool()
    async def delete_related_items(
        source_type: str,
        source_id: int,
        related_item_ids: list[int],
    ) -> str:
        """Delete relationships between resources.

        Args:
            source_type: The type of the source resource
            source_id: The ID of the source resource
            related_item_ids: List of related item IDs to delete

        Returns:
            JSON string with deletion confirmation
        """
        if source_type not in VALID_RESOURCE_TYPES:
            return json.dumps({
                "error": f"Invalid source type: {source_type}",
                "valid_types": VALID_RESOURCE_TYPES,
            }, indent=2)

        data = {
            "data": [
                {"type": "related_items", "attributes": {"id": rid}}
                for rid in related_item_ids
            ]
        }

        endpoint = f"/{source_type}/{source_id}/relationships/related_items"
        await client.delete(endpoint, data)

        return json.dumps({
            "success": True,
            "message": f"Deleted {len(related_item_ids)} relationship(s)",
            "deleted_ids": related_item_ids,
        }, indent=2)

    @mcp.tool()
    async def get_configuration_relationships(configuration_id: int) -> str:
        """Get all items related to a specific configuration (device/asset).

        This is a convenience method for a common use case.

        Args:
            configuration_id: The configuration ID

        Returns:
            JSON string with all related items
        """
        response = await client.get(
            f"/configurations/{configuration_id}/relationships/related_items"
        )
        items = response.get("data", [])

        # Group by resource type
        by_type: dict[str, list] = {}
        for item in items:
            formatted = _format_related_item(item)
            rtype = formatted.get("resource_type", "unknown")
            if rtype not in by_type:
                by_type[rtype] = []
            by_type[rtype].append(formatted)

        result = {
            "configuration_id": configuration_id,
            "total_relationships": len(items),
            "by_type": by_type,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_contact_relationships(contact_id: int) -> str:
        """Get all items related to a specific contact.

        This is a convenience method for a common use case.

        Args:
            contact_id: The contact ID

        Returns:
            JSON string with all related items
        """
        response = await client.get(
            f"/contacts/{contact_id}/relationships/related_items"
        )
        items = response.get("data", [])

        # Group by resource type
        by_type: dict[str, list] = {}
        for item in items:
            formatted = _format_related_item(item)
            rtype = formatted.get("resource_type", "unknown")
            if rtype not in by_type:
                by_type[rtype] = []
            by_type[rtype].append(formatted)

        result = {
            "contact_id": contact_id,
            "total_relationships": len(items),
            "by_type": by_type,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_flexible_asset_relationships(flexible_asset_id: int) -> str:
        """Get all items related to a specific flexible asset.

        This is a convenience method for a common use case.

        Args:
            flexible_asset_id: The flexible asset ID

        Returns:
            JSON string with all related items
        """
        response = await client.get(
            f"/flexible-assets/{flexible_asset_id}/relationships/related_items"
        )
        items = response.get("data", [])

        # Group by resource type
        by_type: dict[str, list] = {}
        for item in items:
            formatted = _format_related_item(item)
            rtype = formatted.get("resource_type", "unknown")
            if rtype not in by_type:
                by_type[rtype] = []
            by_type[rtype].append(formatted)

        result = {
            "flexible_asset_id": flexible_asset_id,
            "total_relationships": len(items),
            "by_type": by_type,
        }

        return json.dumps(result, indent=2)
