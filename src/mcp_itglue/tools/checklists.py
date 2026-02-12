"""IT Glue Checklists tools for MCP.

Checklists in IT Glue are task lists that can be assigned to organizations
and tracked for completion. They can be created from templates or manually.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client
from .output import format_list_output, format_search_output


def _format_checklist(checklist: dict[str, Any]) -> dict[str, Any]:
    """Format a checklist object for display."""
    attrs = checklist.get("attributes", {})
    return {
        "id": checklist.get("id"),
        "organization_id": attrs.get("organization-id"),
        "checklist_template_id": attrs.get("checklist-template-id"),
        "name": attrs.get("name"),
        "description": attrs.get("description"),
        "completed": attrs.get("completed"),
        "completed_at": attrs.get("completed-at"),
        "due_date": attrs.get("due-date"),
        "assignee_id": attrs.get("assignee-id"),
        "restricted": attrs.get("restricted"),
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
    }


def _format_checklist_task(task: dict[str, Any]) -> dict[str, Any]:
    """Format a checklist task object for display."""
    attrs = task.get("attributes", {})
    return {
        "id": task.get("id"),
        "checklist_id": attrs.get("checklist-id"),
        "name": attrs.get("name"),
        "description": attrs.get("description"),
        "completed": attrs.get("completed"),
        "completed_at": attrs.get("completed-at"),
        "position": attrs.get("position"),
        "assignee_id": attrs.get("assignee-id"),
        "due_date": attrs.get("due-date"),
    }


def register_checklist_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    """Register checklist-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: Optional IT Glue client (uses global client if not provided)
    """
    client = client or get_client()

    @mcp.tool()
    async def list_checklists(
        organization_id: int | None = None,
        completed: bool | None = None,
        assignee_id: int | None = None,
        checklist_template_id: int | None = None,
        include_tasks: bool = False,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List checklists from IT Glue.

        Args:
            organization_id: Filter by organization ID
            completed: Filter by completion status
            assignee_id: Filter by assignee user ID
            checklist_template_id: Filter by template ID
            include_tasks: Whether to include checklist tasks
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of checklists
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id
        if completed is not None:
            params["filter[completed]"] = str(completed).lower()
        if assignee_id:
            params["filter[assignee_id]"] = assignee_id
        if checklist_template_id:
            params["filter[checklist_template_id]"] = checklist_template_id
        if include_tasks:
            params["include"] = "checklist_tasks"

        # Use nested endpoint if organization_id is provided
        if organization_id:
            endpoint = f"/organizations/{organization_id}/relationships/checklists"
        else:
            endpoint = "/checklists"

        response = await client.get(endpoint, params)
        checklists = response.get("data", [])
        meta = response.get("meta", {})

        extra_fields: dict[str, Any] = {
            "total_count": meta.get("total-count", len(checklists)),
            "page": page,
            "page_size": page_size,
        }

        # Include tasks if requested
        if include_tasks:
            included = response.get("included", [])
            tasks_by_checklist: dict[str, list] = {}
            for item in included:
                # JSON:API returns type in kebab-case (checklist-tasks)
                if item.get("type") in ("checklist-tasks", "checklist_tasks"):
                    task = _format_checklist_task(item)
                    checklist_id = str(task.get("checklist_id"))
                    if checklist_id not in tasks_by_checklist:
                        tasks_by_checklist[checklist_id] = []
                    tasks_by_checklist[checklist_id].append(task)
            extra_fields["tasks_by_checklist"] = tasks_by_checklist

        return format_list_output(
            items=[_format_checklist(c) for c in checklists],
            entity_type="checklist",
            list_key="checklists",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields=extra_fields,
        )

    @mcp.tool()
    async def get_checklist(checklist_id: int, include_tasks: bool = True) -> str:
        """Get a specific checklist by ID.

        Args:
            checklist_id: The checklist ID
            include_tasks: Whether to include checklist tasks

        Returns:
            JSON string with checklist details
        """
        params = {}
        if include_tasks:
            params["include"] = "checklist_tasks"

        response = await client.get(f"/checklists/{checklist_id}", params)
        checklist = response.get("data", {})

        result = _format_checklist(checklist)

        # Include tasks if requested
        if include_tasks:
            included = response.get("included", [])
            # JSON:API returns type in kebab-case (checklist-tasks)
            result["tasks"] = [
                _format_checklist_task(t)
                for t in included
                if t.get("type") in ("checklist-tasks", "checklist_tasks")
            ]
            # Sort tasks by position (handle None values)
            result["tasks"].sort(key=lambda t: t.get("position") or 0)

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_organization_checklists(
        organization_id: int,
        completed: bool | None = None,
        include_tasks: bool = False,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """Get all checklists for a specific organization.

        Args:
            organization_id: The organization ID
            completed: Filter by completion status
            include_tasks: Whether to include checklist tasks
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with the organization's checklists
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if completed is not None:
            params["filter[completed]"] = str(completed).lower()
        if include_tasks:
            params["include"] = "checklist_tasks"

        response = await client.get(
            f"/organizations/{organization_id}/relationships/checklists", params
        )
        checklists = response.get("data", [])
        meta = response.get("meta", {})

        extra_fields: dict[str, Any] = {
            "organization_id": organization_id,
            "total_count": meta.get("total-count", len(checklists)),
            "page": page,
            "page_size": page_size,
        }

        # Include tasks if requested
        if include_tasks:
            included = response.get("included", [])
            tasks_by_checklist: dict[str, list] = {}
            for item in included:
                # JSON:API returns type in kebab-case (checklist-tasks)
                if item.get("type") in ("checklist-tasks", "checklist_tasks"):
                    task = _format_checklist_task(item)
                    checklist_id = str(task.get("checklist_id"))
                    if checklist_id not in tasks_by_checklist:
                        tasks_by_checklist[checklist_id] = []
                    tasks_by_checklist[checklist_id].append(task)
            extra_fields["tasks_by_checklist"] = tasks_by_checklist

        return format_list_output(
            items=[_format_checklist(c) for c in checklists],
            entity_type="checklist",
            list_key="checklists",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields=extra_fields,
        )

    # NOTE: create_checklist removed - API key auth doesn't work for checklist creation.
    # Use create_checklist_jwt from register_jwt_checklist_tools instead.

    @mcp.tool()
    async def update_checklist(
        checklist_id: int,
        name: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        restricted: bool | None = None,
    ) -> str:
        """Update an existing checklist.

        Args:
            checklist_id: The checklist ID
            name: New checklist name
            description: New checklist description
            completed: Mark checklist as completed/incomplete
            due_date: New due date (YYYY-MM-DD)
            assignee_id: New assignee user ID
            restricted: New restricted status

        Returns:
            JSON string with the updated checklist
        """
        attributes: dict[str, Any] = {}

        if name:
            attributes["name"] = name
        if description is not None:
            attributes["description"] = description
        if completed is not None:
            attributes["completed"] = completed
        if due_date is not None:
            attributes["due-date"] = due_date
        if assignee_id is not None:
            attributes["assignee-id"] = assignee_id
        if restricted is not None:
            attributes["restricted"] = restricted

        if not attributes:
            return json.dumps({"error": "No attributes provided to update"})

        data = {
            "data": {
                "type": "checklists",
                "attributes": attributes,
            }
        }

        response = await client.patch(f"/checklists/{checklist_id}", data)
        checklist = response.get("data", {})

        return json.dumps(_format_checklist(checklist), indent=2)

    @mcp.tool()
    async def complete_checklist(checklist_id: int) -> str:
        """Mark a checklist as completed.

        Args:
            checklist_id: The checklist ID

        Returns:
            JSON string with the updated checklist
        """
        data = {
            "data": {
                "type": "checklists",
                "attributes": {"completed": True},
            }
        }

        response = await client.patch(f"/checklists/{checklist_id}", data)
        checklist = response.get("data", {})

        return json.dumps(_format_checklist(checklist), indent=2)

    @mcp.tool()
    async def uncomplete_checklist(checklist_id: int) -> str:
        """Mark a checklist as incomplete.

        Args:
            checklist_id: The checklist ID

        Returns:
            JSON string with the updated checklist
        """
        data = {
            "data": {
                "type": "checklists",
                "attributes": {"completed": False},
            }
        }

        response = await client.patch(f"/checklists/{checklist_id}", data)
        checklist = response.get("data", {})

        return json.dumps(_format_checklist(checklist), indent=2)

    @mcp.tool()
    async def delete_checklists(checklist_ids: list[int]) -> str:
        """Delete multiple checklists.

        Args:
            checklist_ids: List of checklist IDs to delete

        Returns:
            JSON string with deletion confirmation
        """
        data = {
            "data": [
                {"type": "checklists", "attributes": {"id": cid}}
                for cid in checklist_ids
            ]
        }

        await client.delete("/checklists", data)

        return json.dumps({
            "success": True,
            "message": f"Deleted {len(checklist_ids)} checklist(s)",
            "deleted_ids": checklist_ids,
        }, indent=2)

    @mcp.tool()
    async def list_incomplete_checklists(
        organization_id: int | None = None,
        overdue_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List incomplete checklists, optionally filtered by organization.

        Args:
            organization_id: Optional organization ID filter
            overdue_only: If True, only return checklists past their due date
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of incomplete checklists
        """
        params: dict[str, Any] = {
            "filter[completed]": "false",
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        if organization_id:
            params["filter[organization_id]"] = organization_id

        response = await client.get("/checklists", params)
        checklists = response.get("data", [])
        meta = response.get("meta", {})

        formatted = [_format_checklist(c) for c in checklists]

        # Filter to overdue if requested
        if overdue_only:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).date()
            formatted = [
                c for c in formatted
                if c.get("due_date") and datetime.fromisoformat(
                    c["due_date"].replace("Z", "+00:00")
                ).date() < now
            ]

        return format_list_output(
            items=formatted,
            entity_type="checklist",
            list_key="checklists",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(checklists)),
                "filtered_count": len(formatted),
                "page": page,
                "page_size": page_size,
                "filters": {
                    "completed": False,
                    "organization_id": organization_id,
                    "overdue_only": overdue_only,
                },
            },
        )


    # =========================================================================
    # Checklist Templates
    # =========================================================================

    @mcp.tool()
    async def list_checklist_templates(
        page: int = 1,
        page_size: int = 50,
        output_format: str = "compact",
        save_to_file: bool = False,
    ) -> str:
        """List all checklist templates.

        Checklist templates are reusable checklists that can be instantiated
        for specific organizations. Use these template IDs when creating
        checklists with create_checklist(checklist_template_id=...).

        Args:
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)
            output_format: Output format - "full" (all fields), "compact" (key fields only), or "summary" (counts and IDs only). Default: compact
            save_to_file: If True, saves full results to a temp file and returns the path for jq processing

        Returns:
            JSON string with list of checklist templates
        """
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": min(page_size, 1000),
        }

        response = await client.get("/checklist_templates", params)
        templates = response.get("data", [])
        meta = response.get("meta", {})

        formatted = []
        for t in templates:
            attrs = t.get("attributes", {})
            formatted.append({
                "id": t.get("id"),
                "name": attrs.get("name"),
                "description": attrs.get("description"),
                "created_at": attrs.get("created-at"),
                "updated_at": attrs.get("updated-at"),
            })

        return format_list_output(
            items=formatted,
            entity_type="checklist_template",
            list_key="checklist_templates",
            output_format=output_format,
            save_to_file=save_to_file,
            extra_fields={
                "total_count": meta.get("total-count", len(templates)),
                "page": page,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_checklist_template(template_id: int) -> str:
        """Get a specific checklist template by ID.

        Args:
            template_id: The checklist template ID

        Returns:
            JSON string with template details
        """
        response = await client.get(f"/checklist_templates/{template_id}")
        template = response.get("data", {})
        attrs = template.get("attributes", {})

        result = {
            "id": template.get("id"),
            "name": attrs.get("name"),
            "description": attrs.get("description"),
            "created_at": attrs.get("created-at"),
            "updated_at": attrs.get("updated-at"),
        }

        return json.dumps(result, indent=2)

    # NOTE: create_checklist_from_template removed - API key auth doesn't work for checklist creation.
    # Use create_checklist_from_template_jwt from register_jwt_checklist_tools instead.


# =============================================================================
# JWT-Authenticated Checklist Tools
# =============================================================================
# These tools use JWT authentication captured from browser sessions.
# Required because API key authentication doesn't work for checklist creation.

def register_jwt_checklist_tools(mcp: FastMCP) -> None:
    """Register JWT-authenticated checklist tools with the MCP server.

    These tools use JWT tokens captured from authenticated browser sessions
    instead of API keys. This is required for checklist creation, which
    IT Glue's API key authentication doesn't support.

    Args:
        mcp: The FastMCP server instance
    """
    from ..jwt_client import get_jwt_client, JWTClientError
    from ..jwt_auth import (
        get_cached_token,
        clear_token_cache,
        set_keep_browser_open,
        get_keep_browser_open,
        is_browser_open,
        close_browser,
    )
    
    @mcp.tool()
    async def jwt_token_status() -> str:
        """Check the status of the cached JWT token.
        
        Returns information about the currently cached JWT token including
        whether it's valid, when it expires, and the authenticated user.
        
        Returns:
            JSON string with token status
        """
        token = get_cached_token()
        
        if token is None:
            return json.dumps({
                "status": "no_token",
                "message": "No cached JWT token. Use jwt_capture_token to authenticate.",
            }, indent=2)
        
        if token.is_expired:
            return json.dumps({
                "status": "expired",
                "message": "Token is expired or expiring soon. Use jwt_capture_token to refresh.",
                "email": token.email,
                "expires_at": token.expires_at,
            }, indent=2)
        
        return json.dumps({
            "status": "valid",
            "email": token.email,
            "user_id": token.user_id,
            "account_id": token.account_id,
            "expires_in_minutes": token.time_remaining_minutes,
            "expires_at": token.expires_at,
        }, indent=2)
    
    @mcp.tool()
    async def jwt_clear_token() -> str:
        """Clear the cached JWT token.

        Use this if you need to re-authenticate with a different account
        or if the token is causing issues.

        Returns:
            Confirmation message
        """
        clear_token_cache()
        return json.dumps({
            "success": True,
            "message": "JWT token cache cleared. Next JWT operation will require browser authentication.",
        }, indent=2)

    @mcp.tool()
    async def browser_keep_open(enabled: bool) -> str:
        """Enable or disable browser persistence after authentication.

        When enabled (True), the browser window stays open after capturing
        authentication tokens. This is useful when you have multiple operations
        that need authentication - you only need to log in once per session.

        When disabled (False, the default), the browser closes automatically
        after each authentication capture.

        Args:
            enabled: True to keep browser open after auth, False to close it

        Returns:
            Confirmation of the new setting
        """
        set_keep_browser_open(enabled)
        return json.dumps({
            "success": True,
            "keep_browser_open": enabled,
            "message": f"Browser will {'stay open' if enabled else 'close'} after authentication.",
            "hint": "Use browser_close to manually close the browser when done." if enabled else None,
        }, indent=2)

    @mcp.tool()
    async def browser_status() -> str:
        """Check the current browser persistence status.

        Returns information about:
        - Whether browser persistence is enabled
        - Whether a browser is currently open

        Returns:
            JSON string with browser status
        """
        browser_open = is_browser_open()
        keep_open = get_keep_browser_open()

        return json.dumps({
            "keep_browser_open_enabled": keep_open,
            "browser_currently_open": browser_open,
            "message": (
                "Browser is open and will stay open for subsequent operations."
                if browser_open and keep_open else
                "Browser is open but will close after next operation."
                if browser_open and not keep_open else
                "No browser currently open. Browser persistence is enabled."
                if not browser_open and keep_open else
                "No browser currently open. Browser will close after each auth."
            ),
        }, indent=2)

    @mcp.tool()
    async def browser_close() -> str:
        """Close the persistent browser if it's open.

        Use this to manually close the browser when you're done with
        operations that require authentication. Only needed when
        browser persistence is enabled (browser_keep_open enabled=True).

        Returns:
            Confirmation message
        """
        was_open = is_browser_open()
        await close_browser()
        return json.dumps({
            "success": True,
            "was_open": was_open,
            "message": "Browser closed." if was_open else "No browser was open.",
        }, indent=2)

    @mcp.tool()
    async def create_checklist_jwt(
        organization_id: int,
        name: str,
        description: str | None = None,
        checklist_template_id: int | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        restricted: bool = False,
    ) -> str:
        """Create a new checklist using JWT authentication.
        
        This tool uses JWT authentication (captured from browser session)
        instead of API key authentication. This is REQUIRED for checklist
        creation because IT Glue's API key auth doesn't support it.
        
        If no valid JWT token is cached, this will open a browser window
        for SAML authentication.
        
        Args:
            organization_id: Organization ID (required)
            name: Checklist name
            description: Checklist description
            checklist_template_id: Optional template ID to create from
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the checklist to
            restricted: Whether the checklist is restricted
        
        Returns:
            JSON string with the created checklist
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.create_checklist(
                organization_id=organization_id,
                name=name,
                description=description,
                checklist_template_id=checklist_template_id,
                due_date=due_date,
                assignee_id=assignee_id,
                restricted=restricted,
            )
            
            return json.dumps(_format_checklist(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    # =========================================================================
    # JWT-Authenticated Checklist Task Tools
    # =========================================================================
    
    @mcp.tool()
    async def create_checklist_task_jwt(
        checklist_id: int,
        name: str,
        description: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        position: int | None = None,
        completed: bool = False,
    ) -> str:
        """Create a new task on a checklist using JWT authentication.
        
        This tool uses JWT authentication (captured from browser session)
        instead of API key authentication. This is REQUIRED for task creation
        because IT Glue's public API doesn't expose the checklist_tasks POST endpoint.
        
        If no valid JWT token is cached, this will open a browser window
        for SAML authentication.
        
        Args:
            checklist_id: Checklist ID to add the task to (required)
            name: Task name (required)
            description: Task description
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the task to
            position: Position/order of the task in the list
            completed: Whether the task is already completed (default: False)
        
        Returns:
            JSON string with the created task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.create_checklist_task(
                checklist_id=checklist_id,
                name=name,
                description=description,
                due_date=due_date,
                assignee_id=assignee_id,
                position=position,
                completed=completed,
            )
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def update_checklist_task_jwt(
        task_id: int,
        name: str | None = None,
        description: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        position: int | None = None,
        completed: bool | None = None,
    ) -> str:
        """Update an existing checklist task using JWT authentication.
        
        This tool uses JWT authentication because IT Glue's public API
        doesn't support task modification.
        
        Args:
            task_id: Task ID to update (required)
            name: New task name
            description: New task description
            due_date: New due date in ISO format (YYYY-MM-DD)
            assignee_id: New assignee user ID
            position: New position/order in the list
            completed: New completion status
        
        Returns:
            JSON string with the updated task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.update_checklist_task(
                task_id=task_id,
                name=name,
                description=description,
                due_date=due_date,
                assignee_id=assignee_id,
                position=position,
                completed=completed,
            )
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def delete_checklist_task_jwt(task_id: int) -> str:
        """Delete a checklist task using JWT authentication.
        
        This tool uses JWT authentication because IT Glue's public API
        doesn't support task deletion.
        
        Args:
            task_id: Task ID to delete
        
        Returns:
            JSON string with deletion confirmation
        """
        jwt_client = get_jwt_client()
        
        try:
            await jwt_client.delete_checklist_task(task_id=task_id)
            
            return json.dumps({
                "success": True,
                "message": f"Task {task_id} deleted successfully",
                "deleted_task_id": task_id,
            }, indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def complete_checklist_task_jwt(task_id: int) -> str:
        """Mark a checklist task as completed using JWT authentication.
        
        Args:
            task_id: Task ID to complete
        
        Returns:
            JSON string with the updated task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.complete_checklist_task(task_id=task_id)
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def uncomplete_checklist_task_jwt(task_id: int) -> str:
        """Mark a checklist task as not completed using JWT authentication.
        
        Args:
            task_id: Task ID to mark as incomplete
        
        Returns:
            JSON string with the updated task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.uncomplete_checklist_task(task_id=task_id)
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def create_checklist_from_template_jwt(
        organization_id: int,
        checklist_template_id: int,
        name: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
    ) -> str:
        """Create a checklist from a template using JWT authentication.
        
        This tool uses JWT authentication (captured from browser session)
        instead of API key authentication. This is REQUIRED for checklist
        creation because IT Glue's API key auth doesn't support it.
        
        If no valid JWT token is cached, this will open a browser window
        for SAML authentication.
        
        Args:
            organization_id: Organization ID
            checklist_template_id: Template ID to create from
            name: Optional custom name (uses template name if not provided)
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the checklist to
        
        Returns:
            JSON string with the created checklist
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.create_checklist_from_template(
                organization_id=organization_id,
                checklist_template_id=checklist_template_id,
                name=name,
                due_date=due_date,
                assignee_id=assignee_id,
            )
            
            return json.dumps(_format_checklist(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    # =========================================================================
    # JWT-Authenticated Checklist Task Tools
    # =========================================================================
    
    @mcp.tool()
    async def create_checklist_task_jwt(
        checklist_id: int,
        name: str,
        description: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        position: int | None = None,
        completed: bool = False,
    ) -> str:
        """Create a new task on a checklist using JWT authentication.
        
        This tool uses JWT authentication (captured from browser session)
        instead of API key authentication. This is REQUIRED for task creation
        because IT Glue's public API doesn't expose the checklist_tasks POST endpoint.
        
        If no valid JWT token is cached, this will open a browser window
        for SAML authentication.
        
        Args:
            checklist_id: Checklist ID to add the task to (required)
            name: Task name (required)
            description: Task description
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the task to
            position: Position/order of the task in the list
            completed: Whether the task is already completed (default: False)
        
        Returns:
            JSON string with the created task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.create_checklist_task(
                checklist_id=checklist_id,
                name=name,
                description=description,
                due_date=due_date,
                assignee_id=assignee_id,
                position=position,
                completed=completed,
            )
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def update_checklist_task_jwt(
        task_id: int,
        name: str | None = None,
        description: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        position: int | None = None,
        completed: bool | None = None,
    ) -> str:
        """Update an existing checklist task using JWT authentication.
        
        This tool uses JWT authentication because IT Glue's public API
        doesn't support task modification.
        
        Args:
            task_id: Task ID to update (required)
            name: New task name
            description: New task description
            due_date: New due date in ISO format (YYYY-MM-DD)
            assignee_id: New assignee user ID
            position: New position/order in the list
            completed: New completion status
        
        Returns:
            JSON string with the updated task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.update_checklist_task(
                task_id=task_id,
                name=name,
                description=description,
                due_date=due_date,
                assignee_id=assignee_id,
                position=position,
                completed=completed,
            )
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def delete_checklist_task_jwt(task_id: int) -> str:
        """Delete a checklist task using JWT authentication.
        
        This tool uses JWT authentication because IT Glue's public API
        doesn't support task deletion.
        
        Args:
            task_id: Task ID to delete
        
        Returns:
            JSON string with deletion confirmation
        """
        jwt_client = get_jwt_client()
        
        try:
            await jwt_client.delete_checklist_task(task_id=task_id)
            
            return json.dumps({
                "success": True,
                "message": f"Task {task_id} deleted successfully",
                "deleted_task_id": task_id,
            }, indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def complete_checklist_task_jwt(task_id: int) -> str:
        """Mark a checklist task as completed using JWT authentication.
        
        Args:
            task_id: Task ID to complete
        
        Returns:
            JSON string with the updated task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.complete_checklist_task(task_id=task_id)
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
    
    @mcp.tool()
    async def uncomplete_checklist_task_jwt(task_id: int) -> str:
        """Mark a checklist task as not completed using JWT authentication.
        
        Args:
            task_id: Task ID to mark as incomplete
        
        Returns:
            JSON string with the updated task
        """
        jwt_client = get_jwt_client()
        
        try:
            result = await jwt_client.uncomplete_checklist_task(task_id=task_id)
            
            return json.dumps(_format_checklist_task(result), indent=2)
        
        except JWTClientError as e:
            return json.dumps({
                "error": str(e),
                "status_code": e.status_code,
                "hint": "If authentication failed, try jwt_clear_token and retry.",
            }, indent=2)
