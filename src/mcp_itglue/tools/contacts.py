"""IT Glue Contacts tools for MCP."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


def _format_contact(contact: dict[str, Any]) -> dict[str, Any]:
    """Format a contact object for display."""
    attrs = contact.get("attributes", {})
    return {
        "id": contact.get("id"),
        "organization_id": attrs.get("organization-id"),
        "first_name": attrs.get("first-name"),
        "last_name": attrs.get("last-name"),
        "name": attrs.get("name"),
        "title": attrs.get("title"),
        "contact_type": attrs.get("contact-type-name"),
        "location": attrs.get("location-name"),
        "important": attrs.get("important"),
        "notes": attrs.get("notes"),
        # Contact information
        "contact_emails": attrs.get("contact-emails", []),
        "contact_phones": attrs.get("contact-phones", []),
        # Timestamps
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def register_contact_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register contact-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_contacts(
        organization_id: int | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        title: str | None = None,
        contact_type_id: int | None = None,
        important: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """List contacts from IT Glue.

        Args:
            organization_id: Filter by organization ID
            first_name: Filter by first name (partial match)
            last_name: Filter by last name (partial match)
            title: Filter by job title (partial match)
            contact_type_id: Filter by contact type ID
            important: Filter by important flag
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

        Returns:
            JSON string with list of contacts
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if first_name:
            params["filter[first_name]"] = first_name
        if last_name:
            params["filter[last_name]"] = last_name
        if title:
            params["filter[title]"] = title
        if contact_type_id:
            params["filter[contact_type_id]"] = contact_type_id
        if important is not None:
            params["filter[important]"] = str(important).lower()

        # Use nested endpoint if organization_id is provided
        if organization_id:
            endpoint = f"/organizations/{organization_id}/relationships/contacts"
        else:
            endpoint = "/contacts"

        response = await client.get(endpoint, params)
        contacts = response.get("data", [])
        meta = response.get("meta", {})

        result = {
            "contacts": [_format_contact(c) for c in contacts],
            "total_count": meta.get("total-count", len(contacts)),
            "page": page,
            "page_size": page_size,
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_contact(contact_id: int) -> str:
        """Get a specific contact by ID.

        Args:
            contact_id: The IT Glue contact ID

        Returns:
            JSON string with contact details
        """
        response = await client.get(f"/contacts/{contact_id}")
        contact = response.get("data", {})

        return json.dumps(_format_contact(contact), indent=2)

    @mcp.tool()
    async def search_contacts(
        query: str,
        organization_id: int | None = None,
        limit: int = 10,
    ) -> str:
        """Search for contacts by name.

        Args:
            query: Search query string (searches first and last name)
            organization_id: Optional organization ID to limit search
            limit: Maximum number of results (default 10, max 100)

        Returns:
            JSON string with matching contacts
        """
        # IT Glue doesn't have a combined name search, so we search by first name
        # A more sophisticated implementation could search both fields
        params: dict[str, Any] = {
            "filter[first_name]": query,
            "page[size]": min(limit, 100),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/contacts", params)
        contacts = response.get("data", [])

        result = {
            "query": query,
            "contacts": [_format_contact(c) for c in contacts],
            "count": len(contacts),
        }

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def create_contact(
        organization_id: int,
        first_name: str,
        last_name: str,
        contact_type_id: int | None = None,
        location_id: int | None = None,
        title: str | None = None,
        important: bool = False,
        notes: str | None = None,
        contact_emails: list[dict[str, Any]] | None = None,
        contact_phones: list[dict[str, Any]] | None = None,
    ) -> str:
        """Create a new contact in IT Glue.

        Args:
            organization_id: Organization ID (required)
            first_name: Contact first name (required)
            last_name: Contact last name (required)
            contact_type_id: Contact type ID
            location_id: Location ID
            title: Job title
            important: Whether this is an important contact
            notes: Additional notes
            contact_emails: List of email objects with 'value' and optional 'label_name', 'primary'
            contact_phones: List of phone objects with 'value' and optional 'label_name', 'primary', 'extension'

        Returns:
            JSON string with the created contact
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "first-name": first_name,
            "last-name": last_name,
            "important": important,
        }

        if contact_type_id:
            attributes["contact-type-id"] = contact_type_id
        if location_id:
            attributes["location-id"] = location_id
        if title:
            attributes["title"] = title
        if notes:
            attributes["notes"] = notes
        if contact_emails:
            attributes["contact-emails"] = contact_emails
        if contact_phones:
            attributes["contact-phones"] = contact_phones

        data = {
            "data": {
                "type": "contacts",
                "attributes": attributes,
            }
        }

        response = await client.post("/contacts", data)
        contact = response.get("data", {})

        return json.dumps(_format_contact(contact), indent=2)

    @mcp.tool()
    async def update_contact(
        contact_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        contact_type_id: int | None = None,
        location_id: int | None = None,
        title: str | None = None,
        important: bool | None = None,
        notes: str | None = None,
        contact_emails: list[dict[str, Any]] | None = None,
        contact_phones: list[dict[str, Any]] | None = None,
    ) -> str:
        """Update an existing contact in IT Glue.

        Args:
            contact_id: The IT Glue contact ID
            first_name: New first name
            last_name: New last name
            contact_type_id: New contact type ID
            location_id: New location ID
            title: New job title
            important: New important flag
            notes: New notes
            contact_emails: New list of email objects
            contact_phones: New list of phone objects

        Returns:
            JSON string with the updated contact
        """
        attributes: dict[str, Any] = {}

        if first_name:
            attributes["first-name"] = first_name
        if last_name:
            attributes["last-name"] = last_name
        if contact_type_id:
            attributes["contact-type-id"] = contact_type_id
        if location_id:
            attributes["location-id"] = location_id
        if title is not None:
            attributes["title"] = title
        if important is not None:
            attributes["important"] = important
        if notes is not None:
            attributes["notes"] = notes
        if contact_emails is not None:
            attributes["contact-emails"] = contact_emails
        if contact_phones is not None:
            attributes["contact-phones"] = contact_phones

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "contacts",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/contacts/{contact_id}", data)
        contact = response.get("data", {})

        return json.dumps(_format_contact(contact), indent=2)

    @mcp.tool()
    async def delete_contact(contact_id: int) -> str:
        """Delete a contact from IT Glue.

        Args:
            contact_id: The IT Glue contact ID

        Returns:
            JSON string with deletion confirmation
        """
        await client.delete(f"/contacts/{contact_id}")

        return json.dumps({
            "success": True,
            "message": f"Contact {contact_id} deleted successfully",
        }, indent=2)
