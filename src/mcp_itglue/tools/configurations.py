"""IT Glue Configurations (devices/assets) tools for MCP."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client
from .output import format_list_output, format_search_output


def _format_configuration(config: dict[str, Any]) -> dict[str, Any]:
    """Format a configuration object for display."""
    attrs = config.get("attributes", {})
    return {
        "id": config.get("id"),
        "organization_id": attrs.get("organization-id"),
        "name": attrs.get("name"),
        "hostname": attrs.get("hostname"),
        "primary_ip": attrs.get("primary-ip"),
        "mac_address": attrs.get("mac-address"),
        "serial_number": attrs.get("serial-number"),
        "asset_tag": attrs.get("asset-tag"),
        "configuration_type": attrs.get("configuration-type-name"),
        "configuration_status": attrs.get("configuration-status-name"),
        "manufacturer": attrs.get("manufacturer-name"),
        "model": attrs.get("model-name"),
        "operating_system": attrs.get("operating-system-name"),
        "operating_system_notes": attrs.get("operating-system-notes"),
        "warranty_expires_at": attrs.get("warranty-expires-at"),
        "installed_by": attrs.get("installed-by"),
        "installed_at": attrs.get("installed-at"),
        "notes": attrs.get("notes"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_configuration_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register configuration-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_configurations(
        organization_id: int | None = None,
        name: str | None = None,
        hostname: str | None = None,
        primary_ip: str | None = None,
        serial_number: str | None = None,
        configuration_type_id: int | None = None,
        configuration_status_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List configurations (devices/assets) from IT Glue.

        Args:
            organization_id: Filter by organization ID
            name: Filter by configuration name (partial match)
            hostname: Filter by hostname
            primary_ip: Filter by primary IP address
            serial_number: Filter by serial number
            configuration_type_id: Filter by configuration type ID
            configuration_status_id: Filter by configuration status ID
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of configurations
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if name:
            params["filter[name]"] = name
        if hostname:
            params["filter[hostname]"] = hostname
        if primary_ip:
            params["filter[primary_ip]"] = primary_ip
        if serial_number:
            params["filter[serial_number]"] = serial_number
        if configuration_type_id:
            params["filter[configuration_type_id]"] = configuration_type_id
        if configuration_status_id:
            params["filter[configuration_status_id]"] = configuration_status_id

        # Use nested endpoint if organization_id is provided
        if organization_id:
            endpoint = f"/organizations/{organization_id}/relationships/configurations"
        else:
            endpoint = "/configurations"

        response = await client.get(endpoint, params)
        configurations = response.get("data", [])
        meta = response.get("meta", {})

        return format_list_output(
            items=[_format_configuration(c) for c in configurations],
            entity_type="configuration",
            list_key="configurations",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(configurations)),
                "page": page,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_configuration(configuration_id: int) -> str:
        """Get a specific configuration by ID.

        Args:
            configuration_id: The IT Glue configuration ID

        Returns:
            JSON string with configuration details
        """
        response = await client.get(f"/configurations/{configuration_id}")
        config = response.get("data", {})

        return json.dumps(_format_configuration(config), indent=2)

    @mcp.tool()
    async def search_configurations(
        query: str,
        organization_id: int | None = None,
        limit: int = 10,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """Search for configurations by name or hostname.

        Args:
            query: Search query string (matches name or hostname)
            organization_id: Optional organization ID to limit search
            limit: Maximum number of results (default 10, max 100)
            output_format: Output format - "full", "compact" (default), or "summary"
            save_to_file: If True, saves full results to a temp file for jq processing

        Returns:
            JSON string with matching configurations
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/configurations", params)
        configurations = response.get("data", [])

        return format_search_output(
            items=[_format_configuration(c) for c in configurations],
            entity_type="configuration",
            list_key="configurations",
            query=query,
            output_format=output_format,
            save_to_file=save_to_file,
        )

    @mcp.tool()
    async def create_configuration(
        organization_id: int,
        name: str,
        configuration_type_id: int,
        hostname: str | None = None,
        primary_ip: str | None = None,
        mac_address: str | None = None,
        serial_number: str | None = None,
        asset_tag: str | None = None,
        configuration_status_id: int | None = None,
        manufacturer_id: int | None = None,
        model_id: int | None = None,
        operating_system_id: int | None = None,
        operating_system_notes: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Create a new configuration (device/asset) in IT Glue.

        Args:
            organization_id: Organization ID (required)
            name: Configuration name (required)
            configuration_type_id: Configuration type ID (required)
            hostname: Device hostname
            primary_ip: Primary IP address
            mac_address: MAC address
            serial_number: Serial number
            asset_tag: Asset tag
            configuration_status_id: Configuration status ID
            manufacturer_id: Manufacturer ID
            model_id: Model ID
            operating_system_id: Operating system ID
            operating_system_notes: OS notes
            notes: General notes

        Returns:
            JSON string with the created configuration
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "name": name,
            "configuration-type-id": configuration_type_id,
        }

        if hostname:
            attributes["hostname"] = hostname
        if primary_ip:
            attributes["primary-ip"] = primary_ip
        if mac_address:
            attributes["mac-address"] = mac_address
        if serial_number:
            attributes["serial-number"] = serial_number
        if asset_tag:
            attributes["asset-tag"] = asset_tag
        if configuration_status_id:
            attributes["configuration-status-id"] = configuration_status_id
        if manufacturer_id:
            attributes["manufacturer-id"] = manufacturer_id
        if model_id:
            attributes["model-id"] = model_id
        if operating_system_id:
            attributes["operating-system-id"] = operating_system_id
        if operating_system_notes:
            attributes["operating-system-notes"] = operating_system_notes
        if notes:
            attributes["notes"] = notes

        data = {
            "data": {
                "type": "configurations",
                "attributes": attributes,
            }
        }

        response = await client.post("/configurations", data)
        config = response.get("data", {})

        return json.dumps(_format_configuration(config), indent=2)

    @mcp.tool()
    async def update_configuration(
        configuration_id: int,
        name: str | None = None,
        hostname: str | None = None,
        primary_ip: str | None = None,
        mac_address: str | None = None,
        serial_number: str | None = None,
        asset_tag: str | None = None,
        configuration_type_id: int | None = None,
        configuration_status_id: int | None = None,
        manufacturer_id: int | None = None,
        model_id: int | None = None,
        operating_system_id: int | None = None,
        operating_system_notes: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Update an existing configuration in IT Glue.

        Args:
            configuration_id: The IT Glue configuration ID
            name: New configuration name
            hostname: New hostname
            primary_ip: New primary IP address
            mac_address: New MAC address
            serial_number: New serial number
            asset_tag: New asset tag
            configuration_type_id: New configuration type ID
            configuration_status_id: New configuration status ID
            manufacturer_id: New manufacturer ID
            model_id: New model ID
            operating_system_id: New operating system ID
            operating_system_notes: New OS notes
            notes: New general notes

        Returns:
            JSON string with the updated configuration
        """
        attributes: dict[str, Any] = {}

        if name:
            attributes["name"] = name
        if hostname is not None:
            attributes["hostname"] = hostname
        if primary_ip is not None:
            attributes["primary-ip"] = primary_ip
        if mac_address is not None:
            attributes["mac-address"] = mac_address
        if serial_number is not None:
            attributes["serial-number"] = serial_number
        if asset_tag is not None:
            attributes["asset-tag"] = asset_tag
        if configuration_type_id:
            attributes["configuration-type-id"] = configuration_type_id
        if configuration_status_id:
            attributes["configuration-status-id"] = configuration_status_id
        if manufacturer_id:
            attributes["manufacturer-id"] = manufacturer_id
        if model_id:
            attributes["model-id"] = model_id
        if operating_system_id:
            attributes["operating-system-id"] = operating_system_id
        if operating_system_notes is not None:
            attributes["operating-system-notes"] = operating_system_notes
        if notes is not None:
            attributes["notes"] = notes

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "configurations",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/configurations/{configuration_id}", data)
        config = response.get("data", {})

        return json.dumps(_format_configuration(config), indent=2)
