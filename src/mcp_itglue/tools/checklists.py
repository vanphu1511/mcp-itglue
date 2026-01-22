"""IT Glue Checklists tools for MCP.

Checklists in IT Glue are task lists that can be assigned to organizations
and tracked for completion. They can be created from templates or manually.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ITGlueClient, get_client


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

        result = {
            "checklists": [_format_checklist(c) for c in checklists],
            "total_count": meta.get("total-count", len(checklists)),
            "page": page,
            "page_size": page_size,
        }

        # Include tasks if requested
        if include_tasks:
            included = response.get("included", [])
            tasks_by_checklist: dict[str, list] = {}
            for item in included:
                if item.get("type") == "checklist_tasks":
                    task = _format_checklist_task(item)
                    checklist_id = str(task.get("checklist_id"))
                    if checklist_id not in tasks_by_checklist:
                        tasks_by_checklist[checklist_id] = []
                    tasks_by_checklist[checklist_id].append(task)
            result["tasks_by_checklist"] = tasks_by_checklist

        return json.dumps(result, indent=2)

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
            result["tasks"] = [
                _format_checklist_task(t)
                for t in included
                if t.get("type") == "checklist_tasks"
            ]
            # Sort tasks by position
            result["tasks"].sort(key=lambda t: t.get("position", 0))

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_organization_checklists(
        organization_id: int,
        completed: bool | None = None,
        include_tasks: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """Get all checklists for a specific organization.

        Args:
            organization_id: The organization ID
            completed: Filter by completion status
            include_tasks: Whether to include checklist tasks
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

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

        result = {
            "organization_id": organization_id,
            "checklists": [_format_checklist(c) for c in checklists],
            "total_count": meta.get("total-count", len(checklists)),
            "page": page,
            "page_size": page_size,
        }

        # Include tasks if requested
        if include_tasks:
            included = response.get("included", [])
            tasks_by_checklist: dict[str, list] = {}
            for item in included:
                if item.get("type") == "checklist_tasks":
                    task = _format_checklist_task(item)
                    checklist_id = str(task.get("checklist_id"))
                    if checklist_id not in tasks_by_checklist:
                        tasks_by_checklist[checklist_id] = []
                    tasks_by_checklist[checklist_id].append(task)
            result["tasks_by_checklist"] = tasks_by_checklist

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def create_checklist(
        organization_id: int,
        name: str,
        description: str | None = None,
        checklist_template_id: int | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        restricted: bool = False,
    ) -> str:
        """Create a new checklist.

        If creating from a template, name and description are ignored and
        populated from the template.

        Args:
            organization_id: Organization ID (required)
            name: Checklist name (ignored if using template)
            description: Checklist description (ignored if using template)
            checklist_template_id: Optional template ID to create from
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the checklist to
            restricted: Whether the checklist is restricted

        Returns:
            JSON string with the created checklist
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "restricted": restricted,
        }

        if checklist_template_id:
            attributes["checklist-template-id"] = checklist_template_id
        else:
            attributes["name"] = name
            if description:
                attributes["description"] = description

        if due_date:
            attributes["due-date"] = due_date
        if assignee_id:
            attributes["assignee-id"] = assignee_id

        data = {
            "data": {
                "type": "checklists",
                "attributes": attributes,
            }
        }

        response = await client.post("/checklists", data)
        checklist = response.get("data", {})

        return json.dumps(_format_checklist(checklist), indent=2)

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
    ) -> str:
        """List incomplete checklists, optionally filtered by organization.

        Args:
            organization_id: Optional organization ID filter
            overdue_only: If True, only return checklists past their due date
            page: Page number (starts at 1)
            page_size: Number of results per page (max 1000)

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

        result = {
            "checklists": formatted,
            "total_count": meta.get("total-count", len(checklists)),
            "filtered_count": len(formatted),
            "page": page,
            "page_size": page_size,
            "filters": {
                "completed": False,
                "organization_id": organization_id,
                "overdue_only": overdue_only,
            },
        }

        return json.dumps(result, indent=2)
