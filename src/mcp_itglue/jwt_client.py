"""JWT-authenticated HTTP client for IT Glue API operations.

This client uses JWT Bearer tokens (captured from browser sessions)
instead of API keys. Required for certain operations like checklist
creation that don't work with API key authentication.
"""

import httpx
from typing import Any

from .config import logger
from .jwt_auth import get_jwt_token, get_cached_token, JWTToken


class JWTClientError(Exception):
    """Error from JWT-authenticated API call."""
    
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ITGlueJWTClient:
    """
    HTTP client for IT Glue API using JWT authentication.
    
    This client is specifically for operations that require JWT auth
    (like checklist creation). For most operations, use the regular
    API key-based ITGlueClient.
    
    Usage:
        client = ITGlueJWTClient()
        
        # This will prompt for browser auth if no cached token
        result = await client.create_checklist(
            organization_id=123,
            name="My Checklist"
        )
    """
    
    # EU API endpoint (the internal API that accepts JWT auth)
    API_URL = "https://api.eu.itglue.com"
    
    def __init__(self, api_url: str | None = None):
        """
        Initialize the JWT client.
        
        Args:
            api_url: Override API URL (defaults to EU endpoint)
        """
        self.api_url = api_url or self.API_URL
        self._token: JWTToken | None = None
        self._http_client: httpx.AsyncClient | None = None
    
    async def _ensure_token(self, auto_refresh: bool = True) -> JWTToken:
        """
        Ensure we have a valid token.
        
        Args:
            auto_refresh: If True, opens browser for auth when needed.
                         If False, raises error when no valid token.
        
        Returns:
            Valid JWT token
        
        Raises:
            JWTClientError: If no valid token and auto_refresh is False
        """
        # Check if we already have a valid token
        if self._token is not None and not self._token.is_expired:
            return self._token
        
        # Try loading from cache
        cached = get_cached_token()
        if cached is not None:
            self._token = cached
            return self._token
        
        # Need to capture a new token
        if not auto_refresh:
            raise JWTClientError(
                "No valid JWT token available. "
                "Run token capture first or enable auto_refresh."
            )
        
        logger.info("No valid token, initiating browser authentication...")
        self._token = await get_jwt_token()
        return self._token
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=30.0,
            )
        return self._http_client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
    
    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auto_refresh: bool = True,
    ) -> dict[str, Any]:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., "/checklists")
            json_data: JSON body data
            params: Query parameters
            auto_refresh: Auto-capture token if needed
        
        Returns:
            Parsed JSON response
        
        Raises:
            JWTClientError: On API errors
        """
        token = await self._ensure_token(auto_refresh)
        client = await self._get_http_client()
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/json",
        }
        
        logger.debug(f"JWT API request: {method} {endpoint}")
        
        response = await client.request(
            method=method,
            url=endpoint,
            headers=headers,
            json=json_data,
            params=params,
        )
        
        # Handle errors
        if response.status_code >= 400:
            error_body = None
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            
            raise JWTClientError(
                f"API error {response.status_code}: {error_body}",
                status_code=response.status_code,
                response_body=error_body,
            )
        
        # Handle empty responses
        if response.status_code == 204 or not response.content:
            return {}
        
        return response.json()
    
    # =========================================================================
    # Checklist Operations
    # =========================================================================
    
    async def create_checklist(
        self,
        organization_id: int,
        name: str,
        description: str | None = None,
        checklist_template_id: int | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        restricted: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new checklist using JWT authentication.
        
        This method uses JWT auth which is required for checklist creation.
        The regular API key authentication doesn't work for this endpoint.
        
        Args:
            organization_id: Organization ID (required)
            name: Checklist name
            description: Checklist description
            checklist_template_id: Optional template ID to create from
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the checklist to
            restricted: Whether the checklist is restricted
        
        Returns:
            Created checklist data
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
        
        response = await self.request("POST", "/checklists", json_data=data)
        return response.get("data", {})
    
    async def create_checklist_from_template(
        self,
        organization_id: int,
        checklist_template_id: int,
        name: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a checklist from a template using JWT authentication.
        
        Args:
            organization_id: Organization ID
            checklist_template_id: Template ID to create from
            name: Optional custom name (uses template name if not provided)
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the checklist to
        
        Returns:
            Created checklist data
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "checklist-template-id": checklist_template_id,
        }
        
        if name:
            attributes["name"] = name
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
        
        response = await self.request("POST", "/checklists", json_data=data)
        return response.get("data", {})
    
    # =========================================================================
    # Checklist Task Operations
    # =========================================================================
    
    async def create_checklist_task(
        self,
        checklist_id: int,
        name: str,
        description: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        position: int | None = None,
        completed: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new task on a checklist using JWT authentication.
        
        This method uses the internal API endpoint for checklist task creation
        which is not available via the public API with API key authentication.
        
        Args:
            checklist_id: Checklist ID to add the task to (required)
            name: Task name (required)
            description: Task description
            due_date: Due date in ISO format (YYYY-MM-DD)
            assignee_id: User ID to assign the task to
            position: Position/order of the task in the list
            completed: Whether the task is already completed
        
        Returns:
            Created task data
        """
        attributes: dict[str, Any] = {
            "checklist-id": checklist_id,
            "name": name,
            "completed": completed,
        }
        
        if description:
            attributes["description"] = description
        if due_date:
            attributes["due-date"] = due_date
        if assignee_id:
            attributes["assignee-id"] = assignee_id
        # API uses "order" instead of "position" for task ordering
        if position is not None:
            attributes["order"] = position
        else:
            # Default to 0 (end of list) if not specified
            attributes["order"] = 0
        
        data = {
            "data": {
                "type": "checklist_tasks",
                "attributes": attributes,
            }
        }
        
        response = await self.request("POST", "/checklist_tasks", json_data=data)
        return response.get("data", {})
    
    async def update_checklist_task(
        self,
        task_id: int,
        name: str | None = None,
        description: str | None = None,
        due_date: str | None = None,
        assignee_id: int | None = None,
        position: int | None = None,
        completed: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing checklist task using JWT authentication.
        
        Args:
            task_id: Task ID to update (required)
            name: New task name
            description: New task description
            due_date: New due date in ISO format (YYYY-MM-DD)
            assignee_id: New assignee user ID
            position: New position/order in the list
            completed: New completion status
        
        Returns:
            Updated task data
        """
        attributes: dict[str, Any] = {}
        
        if name is not None:
            attributes["name"] = name
        if description is not None:
            attributes["description"] = description
        if due_date is not None:
            attributes["due-date"] = due_date
        if assignee_id is not None:
            attributes["assignee-id"] = assignee_id
        # API uses "order" instead of "position" for task ordering
        if position is not None:
            attributes["order"] = position
        if completed is not None:
            attributes["completed"] = completed
        
        data = {
            "data": {
                "type": "checklist-tasks",
                "id": str(task_id),
                "attributes": attributes,
            }
        }
        
        response = await self.request("PATCH", f"/checklist_tasks/{task_id}", json_data=data)
        return response.get("data", {})
    
    async def delete_checklist_task(
        self,
        task_id: int,
    ) -> bool:
        """
        Delete a checklist task using JWT authentication.
        
        Args:
            task_id: Task ID to delete
        
        Returns:
            True if deletion was successful
        """
        # Use bulk delete endpoint with JSON:API format
        data = {
            "data": [
                {
                    "type": "checklist-tasks",
                    "attributes": {
                        "id": task_id
                    }
                }
            ]
        }
        await self.request("DELETE", "/checklist_tasks", json_data=data)
        return True
    
    async def complete_checklist_task(
        self,
        task_id: int,
    ) -> dict[str, Any]:
        """
        Mark a checklist task as completed.
        
        Args:
            task_id: Task ID to complete
        
        Returns:
            Updated task data
        """
        return await self.update_checklist_task(task_id, completed=True)
    
    async def uncomplete_checklist_task(
        self,
        task_id: int,
    ) -> dict[str, Any]:
        """
        Mark a checklist task as not completed.

        Args:
            task_id: Task ID to uncomplete

        Returns:
            Updated task data
        """
        return await self.update_checklist_task(task_id, completed=False)

    # =========================================================================
    # Document Operations
    # =========================================================================
    # Document content creation/update requires JWT auth - API keys don't work

    async def create_document(
        self,
        organization_id: int,
        name: str,
        content: str,
        document_folder_id: int | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new document using JWT authentication.

        This method uses JWT auth which is required for document content.
        The regular API key authentication doesn't persist document content.

        Args:
            organization_id: Organization ID (required)
            name: Document name/title
            content: Document content as HTML
            document_folder_id: Optional folder ID to place document in
            public: Whether the document is publicly visible

        Returns:
            Created document data
        """
        attributes: dict[str, Any] = {
            "organization-id": organization_id,
            "name": name,
            "content": content,
            "public": public,
        }

        if document_folder_id:
            attributes["document-folder-id"] = document_folder_id

        data = {
            "data": {
                "type": "documents",
                "attributes": attributes,
            }
        }

        response = await self.request("POST", "/documents", json_data=data)
        return response.get("data", {})

    async def update_document(
        self,
        document_id: int,
        name: str | None = None,
        content: str | None = None,
        document_folder_id: int | None = None,
        public: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing document using JWT authentication.

        This method uses JWT auth which is required for updating document content.
        The regular API key authentication doesn't persist document content.

        Args:
            document_id: Document ID to update
            name: New document name
            content: New document content as HTML
            document_folder_id: New folder ID
            public: New public visibility status

        Returns:
            Updated document data
        """
        attributes: dict[str, Any] = {}

        if name is not None:
            attributes["name"] = name
        if content is not None:
            attributes["content"] = content
        if document_folder_id is not None:
            attributes["document-folder-id"] = document_folder_id
        if public is not None:
            attributes["public"] = public

        if not attributes:
            raise JWTClientError("No attributes provided to update")

        data = {
            "data": {
                "type": "documents",
                "attributes": attributes,
            }
        }

        response = await self.request("PATCH", f"/documents/{document_id}", json_data=data)
        return response.get("data", {})


# =============================================================================
# Global Client Instance
# =============================================================================

_jwt_client: ITGlueJWTClient | None = None


def get_jwt_client() -> ITGlueJWTClient:
    """Get the global JWT client instance."""
    global _jwt_client
    if _jwt_client is None:
        _jwt_client = ITGlueJWTClient()
    return _jwt_client


def reset_jwt_client() -> None:
    """Reset the global JWT client."""
    global _jwt_client
    _jwt_client = None
