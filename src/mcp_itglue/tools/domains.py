"""IT Glue Domains tools for MCP.

Domains represent Active Directory domains and web domains
associated with organizations.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


def _format_domain(domain: dict[str, Any]) -> dict[str, Any]:
    """Format a domain object for display."""
    attrs = domain.get("attributes", {})
    return {
        "id": domain.get("id"),
        "organization_id": attrs.get("organization-id"),
        "name": attrs.get("name"),
        "notes": attrs.get("notes"),
        "expires_at": attrs.get("expires-at"),
        "registrar": attrs.get("registrar-name"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_domain_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register domain-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_domains(
        organization_id: int | None = None,
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List domains from IT Glue.

        Args:
            organization_id: Filter by organization ID
            name: Filter by domain name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of domains
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if name:
            params["filter[name]"] = name

        response = await client.get("/domains", params)
        domains = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "domains": [_format_domain(d) for d in domains],
            "total_count": meta.get("total-count", len(domains)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_domain(domain_id: int) -> str:
        """Get a specific domain by ID.

        Args:
            domain_id: The domain ID

        Returns:
            JSON string with domain details
        """
        response = await client.get(f"/domains/{domain_id}")
        domain = response.get("data", {})

        return json.dumps(_format_domain(domain), indent=2)

    @mcp.tool()
    async def search_domains(
        query: str,
        organization_id: int | None = None,
        limit: int = 10,
    ) -> str:
        """Search for domains by name.

        Args:
            query: Search query string
            organization_id: Optional organization filter
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching domains
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/domains", params)
        domains = response.get("data", [])

        result = {
            "query": query,
            "domains": [_format_domain(d) for d in domains],
            "count": len(domains),
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_organization_domains(
        organization_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """Get all domains for a specific organization.

        Args:
            organization_id: The organization ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with the organization's domains
        """
        params: dict[str, Any] = {
            "filter[organization_id]": organization_id,
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        response = await client.get("/domains", params)
        domains = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "organization_id": organization_id,
            "domains": [_format_domain(d) for d in domains],
            "total_count": meta.get("total-count", len(domains)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def list_expiring_domains(
        days: int = 30,
        organization_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List domains expiring within a specified number of days.

        Args:
            days: Number of days to look ahead (default 30)
            organization_id: Optional organization filter
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with domains expiring soon
        """
        from datetime import datetime, timedelta, timezone

        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
            "sort": "expires_at",
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/domains", params)
        domains = response.get("data", [])
        meta = response.get("meta", {})

        # Filter to domains expiring within the specified days
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)

        expiring = []
        for d in domains:
            attrs = d.get("attributes", {})
            expires_at = attrs.get("expires-at")
            if expires_at:
                try:
                    exp_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if now <= exp_date <= cutoff:
                        expiring.append(_format_domain(d))
                except (ValueError, TypeError):
                    pass

        result = {
            "domains": expiring,
            "count": len(expiring),
            "days_ahead": days,
            "cutoff_date": cutoff.isoformat(),
        }

        return json.dumps(result, indent=2)
