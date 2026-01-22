"""IT Glue Locations tools for MCP.

Locations represent physical or logical sites within an organization,
used to contextualize configurations, contacts, and other resources.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


def _format_location(location: dict[str, Any]) -> dict[str, Any]:
    """Format a location object for display."""
    attrs = location.get("attributes", {})
    return {
        "id": location.get("id"),
        "organization_id": attrs.get("organization-id"),
        "name": attrs.get("name"),
        "primary": attrs.get("primary"),
        "address_1": attrs.get("address-1"),
        "address_2": attrs.get("address-2"),
        "city": attrs.get("city"),
        "region": attrs.get("region-name"),
        "postal_code": attrs.get("postal-code"),
        "country": attrs.get("country-name"),
        "phone": attrs.get("phone"),
        "fax": attrs.get("fax"),
        "notes": attrs.get("notes"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_location_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register location-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_locations(
        organization_id: int | None = None,
        name: str | None = None,
        city: str | None = None,
        region_id: int | None = None,
        country_id: int | None = None,
        primary: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List locations from IT Glue.

        Args:
            organization_id: Filter by organization ID
            name: Filter by location name (partial match)
            city: Filter by city
            region_id: Filter by region/state ID
            country_id: Filter by country ID
            primary: Filter by primary location status
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of locations
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if name:
            params["filter[name]"] = name
        if city:
            params["filter[city]"] = city
        if region_id:
            params["filter[region_id]"] = region_id
        if country_id:
            params["filter[country_id]"] = country_id
        if primary is not None:
            params["filter[primary]"] = str(primary).lower()

        # Use nested endpoint if organization_id is provided
        if organization_id:
            endpoint = f"/organizations/{organization_id}/relationships/locations"
        else:
            endpoint = "/locations"

        response = await client.get(endpoint, params)
        locations = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "locations": [_format_location(loc) for loc in locations],
            "total_count": meta.get("total-count", len(locations)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_location(location_id: int) -> str:
        """Get a specific location by ID.

        Args:
            location_id: The location ID

        Returns:
            JSON string with location details
        """
        response = await client.get(f"/locations/{location_id}")
        location = response.get("data", {})

        return json.dumps(_format_location(location), indent=2)

    @mcp.tool()
    async def search_locations(
        query: str,
        organization_id: int | None = None,
        limit: int = 10,
    ) -> str:
        """Search for locations by name.

        Args:
            query: Search query string
            organization_id: Optional organization filter
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching locations
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/locations", params)
        locations = response.get("data", [])

        result = {
            "query": query,
            "locations": [_format_location(loc) for loc in locations],
            "count": len(locations),
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def create_location(
        organization_id: int,
        name: str,
        address_1: str | None = None,
        address_2: str | None = None,
        city: str | None = None,
        region_id: int | None = None,
        postal_code: str | None = None,
        country_id: int | None = None,
        phone: str | None = None,
        fax: str | None = None,
        notes: str | None = None,
        primary: bool = False,
    ) -> str:
        """Create a new location.

        Args:
            organization_id: Organization ID (required)
            name: Location name (required)
            address_1: Street address line 1
            address_2: Street address line 2
            city: City name
            region_id: Region/state ID
            postal_code: Postal/ZIP code
            country_id: Country ID
            phone: Phone number
            fax: Fax number
            notes: Additional notes
            primary: Whether this is the primary location

        Returns:
            JSON string with the created location
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "name": name,
            "primary": primary,
        }

        if address_1:
            attributes["address-1"] = address_1
        if address_2:
            attributes["address-2"] = address_2
        if city:
            attributes["city"] = city
        if region_id:
            attributes["region-id"] = region_id
        if postal_code:
            attributes["postal-code"] = postal_code
        if country_id:
            attributes["country-id"] = country_id
        if phone:
            attributes["phone"] = phone
        if fax:
            attributes["fax"] = fax
        if notes:
            attributes["notes"] = notes

        data = {
            "data": {
                "type": "locations",
                "attributes": attributes,
            }
        }

        response = await client.post("/locations", data)
        location = response.get("data", {})

        return json.dumps(_format_location(location), indent=2)

    @mcp.tool()
    async def update_location(
        location_id: int,
        name: str | None = None,
        address_1: str | None = None,
        address_2: str | None = None,
        city: str | None = None,
        region_id: int | None = None,
        postal_code: str | None = None,
        country_id: int | None = None,
        phone: str | None = None,
        fax: str | None = None,
        notes: str | None = None,
        primary: bool | None = None,
    ) -> str:
        """Update an existing location.

        Args:
            location_id: The location ID
            name: New location name
            address_1: New street address line 1
            address_2: New street address line 2
            city: New city name
            region_id: New region/state ID
            postal_code: New postal/ZIP code
            country_id: New country ID
            phone: New phone number
            fax: New fax number
            notes: New notes
            primary: New primary status

        Returns:
            JSON string with the updated location
        """
        attributes: dict[str, Any] = {}

        if name:
            attributes["name"] = name
        if address_1 is not None:
            attributes["address-1"] = address_1
        if address_2 is not None:
            attributes["address-2"] = address_2
        if city is not None:
            attributes["city"] = city
        if region_id is not None:
            attributes["region-id"] = region_id
        if postal_code is not None:
            attributes["postal-code"] = postal_code
        if country_id is not None:
            attributes["country-id"] = country_id
        if phone is not None:
            attributes["phone"] = phone
        if fax is not None:
            attributes["fax"] = fax
        if notes is not None:
            attributes["notes"] = notes
        if primary is not None:
            attributes["primary"] = primary

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "locations",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/locations/{location_id}", data)
        location = response.get("data", {})

        return json.dumps(_format_location(location), indent=2)

    @mcp.tool()
    async def delete_location(location_id: int) -> str:
        """Delete a location.

        Args:
            location_id: The location ID

        Returns:
            JSON string with deletion confirmation
        """
        await client.delete(f"/locations/{location_id}")

        return json.dumps({
            "success": True,
            "message": f"Location {location_id} deleted successfully",
        }, indent=2)

    @mcp.tool()
    async def get_organization_locations(
        organization_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """Get all locations for a specific organization.

        Args:
            organization_id: The organization ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with the organization's locations
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        response = await client.get(
            f"/organizations/{organization_id}/relationships/locations", params
        )
        locations = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "organization_id": organization_id,
            "locations": [_format_location(loc) for loc in locations],
            "total_count": meta.get("total-count", len(locations)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)
