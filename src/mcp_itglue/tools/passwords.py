"""IT Glue Passwords tools for MCP."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client
from .output import format_list_output, format_search_output


def _format_password(password: dict[str, Any], include_password: bool = False) -> dict[str, Any]:
    """Format a password object for display.

    Args:
        password: The password object from IT Glue
        include_password: Whether to include the actual password value
    """
    attrs = password.get("attributes", {})
    result = {
        "id": password.get("id"),
        "organization_id": attrs.get("organization-id"),
        "name": attrs.get("name"),
        "username": attrs.get("username"),
        "url": attrs.get("url"),
        "password_category": attrs.get("password-category-name"),
        "password_folder": attrs.get("password-folder-id"),
        "resource_type": attrs.get("resource-type"),
        "resource_id": attrs.get("resource-id"),
        "otp_enabled": attrs.get("otp-enabled", False),
        "notes": attrs.get("notes"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }

    if include_password:
        result["password"] = attrs.get("password")
        # Include OTP secret only when showing password (requires same permission level)
        if attrs.get("otp-secret"):
            result["otp_secret"] = attrs.get("otp-secret")

    return result


def register_password_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register password-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_passwords(
        organization_id: int | None = None,
        name: str | None = None,
        password_category_id: int | None = None,
        url: str | None = None,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List passwords from IT Glue (without password values).

        Args:
            organization_id: Filter by organization ID
            name: Filter by password name (partial match)
            password_category_id: Filter by password category ID
            url: Filter by URL
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of passwords (password values not included)
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if name:
            params["filter[name]"] = name
        if password_category_id:
            params["filter[password_category_id]"] = password_category_id
        if url:
            params["filter[url]"] = url

        # Use nested endpoint if organization_id is provided
        if organization_id:
            endpoint = f"/organizations/{organization_id}/relationships/passwords"
        else:
            endpoint = "/passwords"

        response = await client.get(endpoint, params)
        passwords = response.get("data", [])
        meta = response.get("meta", {})

        return format_list_output(
            items=[_format_password(p, include_password=False) for p in passwords],
            entity_type="password",
            list_key="passwords",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(passwords)),
                "page": page,
                "page_size": page_size,
                "note": "Password values are not included. Use get_password to retrieve a specific password.",
            },
        )

    @mcp.tool()
    async def get_password(password_id: int, show_password: bool = False) -> str:
        """Get a specific password by ID.

        Args:
            password_id: The IT Glue password ID
            show_password: Whether to include the actual password value

        Returns:
            JSON string with password details
        """
        params = {}
        if show_password:
            params["show_password"] = "true"

        response = await client.get(f"/passwords/{password_id}", params)
        password = response.get("data", {})

        return json.dumps(_format_password(password, include_password=show_password), indent=2)

    @mcp.tool()
    async def search_passwords(
        query: str,
        organization_id: int | None = None,
        limit: int = 10,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """Search for passwords by name.

        Args:
            query: Search query string
            organization_id: Optional organization ID to limit search
            limit: Maximum number of results (default 10, max 100)
            output_format: Output format - "full", "compact" (default), or "summary"
            save_to_file: If True, saves full results to a temp file for jq processing

        Returns:
            JSON string with matching passwords (password values not included)
        """
        params: dict[str, Any] = {
            "filter[name]": query,
            "page[size]": min(limit, 100),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/passwords", params)
        passwords = response.get("data", [])

        return format_search_output(
            items=[_format_password(p, include_password=False) for p in passwords],
            entity_type="password",
            list_key="passwords",
            query=query,
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "note": "Password values are not included. Use get_password to retrieve a specific password.",
            },
        )

    @mcp.tool()
    async def create_password(
        organization_id: int,
        name: str,
        password: str,
        username: str | None = None,
        url: str | None = None,
        password_category_id: int | None = None,
        password_folder_id: int | None = None,
        notes: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        otp_secret: str | None = None,
    ) -> str:
        """Create a new password entry in IT Glue.

        Args:
            organization_id: Organization ID (required)
            name: Password entry name (required)
            password: The password value (required)
            username: Associated username
            url: Associated URL
            password_category_id: Password category ID
            password_folder_id: Password folder ID
            notes: Additional notes
            resource_type: Related resource type (e.g., 'Configuration')
            resource_id: Related resource ID
            otp_secret: TOTP secret key (Base32 encoded, min 16 chars) for 2FA

        Returns:
            JSON string with the created password entry (password value not included)
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "name": name,
            "password": password,
        }

        if username:
            attributes["username"] = username
        if url:
            attributes["url"] = url
        if password_category_id:
            attributes["password-category-id"] = password_category_id
        if password_folder_id:
            attributes["password-folder-id"] = password_folder_id
        if notes:
            attributes["notes"] = notes
        if resource_type:
            attributes["resource-type"] = resource_type
        if resource_id:
            attributes["resource-id"] = resource_id
        if otp_secret:
            attributes["otp-secret"] = otp_secret

        data = {
            "data": {
                "type": "passwords",
                "attributes": attributes,
            }
        }

        response = await client.post("/passwords", data)
        password_obj = response.get("data", {})

        return json.dumps(_format_password(password_obj, include_password=False), indent=2)

    @mcp.tool()
    async def update_password(
        password_id: int,
        name: str | None = None,
        password: str | None = None,
        username: str | None = None,
        url: str | None = None,
        password_category_id: int | None = None,
        password_folder_id: int | None = None,
        notes: str | None = None,
        otp_secret: str | None = None,
    ) -> str:
        """Update an existing password entry in IT Glue.

        Args:
            password_id: The IT Glue password ID
            name: New password entry name
            password: New password value
            username: New username
            url: New URL
            password_category_id: New password category ID
            password_folder_id: New password folder ID
            notes: New notes
            otp_secret: TOTP secret key (Base32 encoded, min 16 chars) for 2FA

        Returns:
            JSON string with the updated password entry (password value not included)
        """
        attributes: dict[str, Any] = {}

        if name:
            attributes["name"] = name
        if password:
            attributes["password"] = password
        if username is not None:
            attributes["username"] = username
        if url is not None:
            attributes["url"] = url
        if password_category_id:
            attributes["password-category-id"] = password_category_id
        if password_folder_id:
            attributes["password-folder-id"] = password_folder_id
        if notes is not None:
            attributes["notes"] = notes
        if otp_secret is not None:
            attributes["otp-secret"] = otp_secret

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "passwords",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/passwords/{password_id}", data)
        password_obj = response.get("data", {})

        return json.dumps(_format_password(password_obj, include_password=False), indent=2)

    @mcp.tool()
    async def delete_password(password_id: int) -> str:
        """Delete a password entry from IT Glue.

        Args:
            password_id: The IT Glue password ID

        Returns:
            JSON string with deletion confirmation
        """
        await client.delete(f"/passwords/{password_id}")

        return json.dumps({
            "success": True,
            "message": f"Password {password_id} deleted successfully",
        }, indent=2)
