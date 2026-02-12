"""IT Glue Organizations tools for MCP."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client
from .output import format_list_output, format_search_output


def _format_organization(org: dict[str, Any]) -> dict[str, Any]:
    """Format an organization object for display."""
    attrs = org.get("attributes", {})
    return {
        "id": org.get("id"),
        "name": attrs.get("name"),
        "short_name": attrs.get("short-name"),
        "description": attrs.get("description"),
        "organization_type": attrs.get("organization-type-name"),
        "organization_status": attrs.get("organization-status-name"),
        "primary": attrs.get("primary"),
        "quick_notes": attrs.get("quick-notes"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_organization_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register organization-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_organizations(
        name: str | None = None,
        organization_type_id: int | None = None,
        organization_status_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List organizations from IT Glue.

        Args:
            name: Filter by organization name (partial match)
            organization_type_id: Filter by organization type ID
            organization_status_id: Filter by organization status ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of organizations
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name
        if organization_type_id:
            params["filter[organization_type_id]"] = organization_type_id
        if organization_status_id:
            params["filter[organization_status_id]"] = organization_status_id

        response = await client.get("/organizations", params)
        organizations = response.get("data", [])
        meta = response.get("meta", {})

        return format_list_output(
            items=[_format_organization(org) for org in organizations],
            entity_type="organization",
            list_key="organizations",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(organizations)),
                "page": page,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_organization(organization_id: int) -> str:
        """Get a specific organization by ID.

        Args:
            organization_id: The IT Glue organization ID

        Returns:
            JSON string with organization details
        """
        response = await client.get(f"/organizations/{organization_id}")
        org = response.get("data", {})

        return json.dumps(_format_organization(org), indent=2)

    @mcp.tool()
    async def search_organizations(
        query: str,
        limit: int = 10,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """Search for organizations by name.

        Args:
            query: Search query string
            limit: Maximum number of results (default 10, max 100)
            output_format: Output format - "full", "compact" (default), or "summary"
            save_to_file: If True, saves full results to a temp file for jq processing

        Returns:
            JSON string with matching organizations
        """
        params = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        response = await client.get("/organizations", params)
        organizations = response.get("data", [])

        return format_search_output(
            items=[_format_organization(org) for org in organizations],
            entity_type="organization",
            list_key="organizations",
            query=query,
            output_format=output_format,
            save_to_file=save_to_file,
        )

    @mcp.tool()
    async def create_organization(
        name: str,
        description: str | None = None,
        organization_type_id: int | None = None,
        organization_status_id: int | None = None,
        quick_notes: str | None = None,
    ) -> str:
        """Create a new organization in IT Glue.

        Args:
            name: Organization name (required)
            description: Organization description
            organization_type_id: Organization type ID
            organization_status_id: Organization status ID
            quick_notes: Quick notes for the organization

        Returns:
            JSON string with the created organization
        """
        attributes: dict[str, Any] = {"name": name}

        if description:
            attributes["description"] = description
        if organization_type_id:
            attributes["organization-type-id"] = organization_type_id
        if organization_status_id:
            attributes["organization-status-id"] = organization_status_id
        if quick_notes:
            attributes["quick-notes"] = quick_notes

        data = {
            "data": {
                "type": "organizations",
                "attributes": attributes,
            }
        }

        response = await client.post("/organizations", data)
        org = response.get("data", {})

        return json.dumps(_format_organization(org), indent=2)

    @mcp.tool()
    async def update_organization(
        organization_id: int,
        name: str | None = None,
        description: str | None = None,
        organization_type_id: int | None = None,
        organization_status_id: int | None = None,
        quick_notes: str | None = None,
    ) -> str:
        """Update an existing organization in IT Glue.

        Args:
            organization_id: The IT Glue organization ID
            name: New organization name
            description: New organization description
            organization_type_id: New organization type ID
            organization_status_id: New organization status ID
            quick_notes: New quick notes

        Returns:
            JSON string with the updated organization
        """
        attributes: dict[str, Any] = {}

        if name:
            attributes["name"] = name
        if description is not None:
            attributes["description"] = description
        if organization_type_id:
            attributes["organization-type-id"] = organization_type_id
        if organization_status_id:
            attributes["organization-status-id"] = organization_status_id
        if quick_notes is not None:
            attributes["quick-notes"] = quick_notes

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "organizations",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/organizations/{organization_id}", data)
        org = response.get("data", {})

        return json.dumps(_format_organization(org), indent=2)
