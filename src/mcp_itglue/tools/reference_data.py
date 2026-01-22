"""IT Glue Reference Data tools for MCP.

Reference data includes lookup tables used throughout IT Glue:
- Manufacturers
- Models
- Operating Systems
- Configuration Types
- Configuration Statuses
- Contact Types
- Organization Types
- Organization Statuses
- Password Categories
- Countries/Regions
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


def _format_simple_reference(item: dict[str, Any]) -> dict[str, Any]:
    """Format a simple reference item (id, name only)."""
    attrs = item.get("attributes", {})
    return {
        "id": item.get("id"),
        "name": attrs.get("name"),
    }


def _format_model(model: dict[str, Any]) -> dict[str, Any]:
    """Format a model object."""
    attrs = model.get("attributes", {})
    return {
        "id": model.get("id"),
        "name": attrs.get("name"),
        "manufacturer_id": attrs.get("manufacturer-id"),
        "manufacturer_name": attrs.get("manufacturer-name"),
    }


def _format_operating_system(os: dict[str, Any]) -> dict[str, Any]:
    """Format an operating system object."""
    attrs = os.get("attributes", {})
    return {
        "id": os.get("id"),
        "name": attrs.get("name"),
        "platform": attrs.get("platform"),
    }


def _format_configuration_type(ct: dict[str, Any]) -> dict[str, Any]:
    """Format a configuration type object."""
    attrs = ct.get("attributes", {})
    return {
        "id": ct.get("id"),
        "name": attrs.get("name"),
    }


def _format_configuration_status(cs: dict[str, Any]) -> dict[str, Any]:
    """Format a configuration status object."""
    attrs = cs.get("attributes", {})
    return {
        "id": cs.get("id"),
        "name": attrs.get("name"),
    }


def register_reference_data_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register reference data tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    # =========================================================================
    # Manufacturers
    # =========================================================================

    @mcp.tool()
    async def list_manufacturers(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all manufacturers.

        Manufacturers are used when creating configurations to specify
        the device manufacturer (e.g., Dell, HP, Cisco).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of manufacturers
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/manufacturers", params)
        manufacturers = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "manufacturers": [_format_simple_reference(m) for m in manufacturers],
            "total_count": meta.get("total-count", len(manufacturers)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def search_manufacturers(query: str, limit: int = 10) -> str:
        """Search for manufacturers by name.

        Args:
            query: Search query string
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching manufacturers
        """
        params = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        response = await client.get("/manufacturers", params)
        manufacturers = response.get("data", [])

        result = {
            "query": query,
            "manufacturers": [_format_simple_reference(m) for m in manufacturers],
            "count": len(manufacturers),
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Models
    # =========================================================================

    @mcp.tool()
    async def list_models(
        manufacturer_id: int | None = None,
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all models.

        Models are used when creating configurations to specify the
        device model (e.g., PowerEdge R740, ProLiant DL380).

        Args:
            manufacturer_id: Filter by manufacturer ID
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of models
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if manufacturer_id:
            params["filter[manufacturer_id]"] = manufacturer_id
        if name:
            params["filter[name]"] = name

        response = await client.get("/models", params)
        models = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "models": [_format_model(m) for m in models],
            "total_count": meta.get("total-count", len(models)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def search_models(
        query: str,
        manufacturer_id: int | None = None,
        limit: int = 10,
    ) -> str:
        """Search for models by name.

        Args:
            query: Search query string
            manufacturer_id: Optional manufacturer filter
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching models
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if manufacturer_id:
            params["filter[manufacturer_id]"] = manufacturer_id

        response = await client.get("/models", params)
        models = response.get("data", [])

        result = {
            "query": query,
            "models": [_format_model(m) for m in models],
            "count": len(models),
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Operating Systems
    # =========================================================================

    @mcp.tool()
    async def list_operating_systems(
        name: str | None = None,
        platform: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all operating systems.

        Operating systems are used when creating configurations to specify
        the device's OS (e.g., Windows Server 2019, Ubuntu 22.04).

        Args:
            name: Filter by name (partial match)
            platform: Filter by platform (e.g., 'Windows', 'Linux', 'macOS')
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of operating systems
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name
        if platform:
            params["filter[platform]"] = platform

        response = await client.get("/operating_systems", params)
        os_list = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "operating_systems": [_format_operating_system(os) for os in os_list],
            "total_count": meta.get("total-count", len(os_list)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def search_operating_systems(query: str, limit: int = 10) -> str:
        """Search for operating systems by name.

        Args:
            query: Search query string
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching operating systems
        """
        params = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        response = await client.get("/operating_systems", params)
        os_list = response.get("data", [])

        result = {
            "query": query,
            "operating_systems": [_format_operating_system(os) for os in os_list],
            "count": len(os_list),
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Configuration Types
    # =========================================================================

    @mcp.tool()
    async def list_configuration_types(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all configuration types.

        Configuration types categorize devices/assets (e.g., Server,
        Workstation, Network Device, Printer).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of configuration types
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/configuration_types", params)
        types = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "configuration_types": [_format_configuration_type(t) for t in types],
            "total_count": meta.get("total-count", len(types)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Configuration Statuses
    # =========================================================================

    @mcp.tool()
    async def list_configuration_statuses(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all configuration statuses.

        Configuration statuses indicate the state of a device/asset
        (e.g., Active, Inactive, Decommissioned).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of configuration statuses
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/configuration_statuses", params)
        statuses = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "configuration_statuses": [_format_configuration_status(s) for s in statuses],
            "total_count": meta.get("total-count", len(statuses)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Contact Types
    # =========================================================================

    @mcp.tool()
    async def list_contact_types(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all contact types.

        Contact types categorize contacts (e.g., Primary, Technical,
        Billing, Emergency).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of contact types
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/contact_types", params)
        types = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "contact_types": [_format_simple_reference(t) for t in types],
            "total_count": meta.get("total-count", len(types)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Organization Types
    # =========================================================================

    @mcp.tool()
    async def list_organization_types(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all organization types.

        Organization types categorize organizations (e.g., Customer,
        Prospect, Vendor, Internal).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of organization types
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/organization_types", params)
        types = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "organization_types": [_format_simple_reference(t) for t in types],
            "total_count": meta.get("total-count", len(types)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Organization Statuses
    # =========================================================================

    @mcp.tool()
    async def list_organization_statuses(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all organization statuses.

        Organization statuses indicate the state of an organization
        (e.g., Active, Inactive, Onboarding).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of organization statuses
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/organization_statuses", params)
        statuses = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "organization_statuses": [_format_simple_reference(s) for s in statuses],
            "total_count": meta.get("total-count", len(statuses)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Password Categories
    # =========================================================================

    @mcp.tool()
    async def list_password_categories(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all password categories.

        Password categories organize passwords by type (e.g., Admin,
        User, Service Account, API Key).

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of password categories
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/password_categories", params)
        categories = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "password_categories": [_format_simple_reference(c) for c in categories],
            "total_count": meta.get("total-count", len(categories)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Countries & Regions
    # =========================================================================

    @mcp.tool()
    async def list_countries(
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List all countries.

        Countries are used when specifying location addresses.

        Args:
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of countries
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/countries", params)
        countries = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "countries": [_format_simple_reference(c) for c in countries],
            "total_count": meta.get("total-count", len(countries)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def list_regions(
        country_id: int,
        name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List regions/states for a country.

        Regions are used when specifying location addresses.

        Args:
            country_id: Country ID to get regions for
            name: Filter by name (partial match)
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of regions
        """
        params: dict[str, Any] = {
            "filter[country_id]": country_id,
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if name:
            params["filter[name]"] = name

        response = await client.get("/regions", params)
        regions = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "country_id": country_id,
            "regions": [_format_simple_reference(r) for r in regions],
            "total_count": meta.get("total-count", len(regions)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    # =========================================================================
    # Convenience: Get All Reference Data
    # =========================================================================

    @mcp.tool()
    async def get_all_reference_data() -> str:
        """Get all reference data in a single call.

        This is useful for caching reference data locally or understanding
        what options are available. Returns the first page of each type.

        Returns:
            JSON string with all reference data types
        """
        # Fetch all reference data in parallel would be ideal, but for now
        # we'll do it sequentially to avoid rate limits
        result: dict[str, list] = {}

        endpoints = [
            ("manufacturers", "/manufacturers"),
            ("configuration_types", "/configuration_types"),
            ("configuration_statuses", "/configuration_statuses"),
            ("contact_types", "/contact_types"),
            ("organization_types", "/organization_types"),
            ("organization_statuses", "/organization_statuses"),
            ("password_categories", "/password_categories"),
        ]

        for key, endpoint in endpoints:
            try:
                response = await client.get(endpoint, {"page[size]": 100})
                data = response.get("data", [])
                result[key] = [_format_simple_reference(item) for item in data]
            except Exception as e:
                result[key] = [{"error": str(e)}]

        return json.dumps(result, indent=2)
