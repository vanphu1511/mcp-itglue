"""MCP server for IT Glue API integration."""

from mcp.server.fastmcp import FastMCP

from .client import get_client
from .config import get_settings, logger
from .tools import (
    register_checklist_tools,
    register_jwt_checklist_tools,
    register_configuration_tools,
    register_contact_tools,
    register_document_tools,
    register_jwt_document_tools,
    register_domain_tools,
    register_flexible_asset_tools,
    register_location_tools,
    register_organization_tools,
    register_password_tools,
    register_reference_data_tools,
    register_related_item_tools,
)

# Initialize FastMCP server
mcp = FastMCP(
    "IT Glue",
    instructions=(
        "MCP server for IT Glue API - comprehensive IT documentation management "
        "including organizations, configurations, passwords, contacts, flexible assets, "
        "checklists, documents, locations, domains, and relationships"
    ),
)


def register_all_tools() -> None:
    """Register all IT Glue tools with the MCP server."""
    client = get_client()

    logger.info("Registering IT Glue MCP tools...")

    # Core entities
    register_organization_tools(mcp, client)
    register_configuration_tools(mcp, client)
    register_password_tools(mcp, client)
    register_contact_tools(mcp, client)

    # Extended entities
    register_flexible_asset_tools(mcp, client)
    register_checklist_tools(mcp, client)
    register_jwt_checklist_tools(mcp)  # JWT-authenticated checklist creation
    register_document_tools(mcp, client)
    register_jwt_document_tools(mcp)  # JWT-authenticated document creation/update
    register_location_tools(mcp, client)
    register_domain_tools(mcp, client)

    # Relationships
    register_related_item_tools(mcp, client)

    # Reference data (lookup tables)
    register_reference_data_tools(mcp, client)

    logger.info("All IT Glue MCP tools registered successfully")


def check_configuration() -> bool:
    """Check if IT Glue is properly configured."""
    settings = get_settings()

    if not settings.is_configured():
        logger.warning(
            "IT Glue API key not configured. "
            "Set ITGLUE_API_KEY environment variable to enable API access."
        )
        return False

    logger.info(f"IT Glue configured with API URL: {settings.api_url}")
    return True


def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Starting IT Glue MCP server...")

    # Check configuration
    check_configuration()

    # Register tools
    register_all_tools()

    # Run the MCP server using stdio transport
    logger.info("IT Glue MCP server running on stdio transport")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
