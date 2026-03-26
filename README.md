![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![MCP](https://img.shields.io/badge/MCP-FastMCP-purple)

# MCP IT Glue Server

A comprehensive Model Context Protocol (MCP) server for IT Glue API integration. This server enables AI assistants like Claude to interact with IT Glue's documentation and asset management system.

## Features

### Core Entities
- **Organizations**: List, search, create, and update organizations
- **Configurations**: Manage devices and assets with full CRUD operations
- **Passwords**: Secure password management with controlled access
- **Contacts**: Manage contact information for organizations

### Extended Entities
- **Flexible Assets**: Custom documentation schemas and instances
- **Checklists**: Task lists with completion tracking
- **Documents**: SOPs, runbooks, and uploaded files
- **Locations**: Physical/logical sites within organizations
- **Domains**: Active Directory and web domains

### Relationships & Reference Data
- **Related Items**: Create and manage relationships between resources
- **Reference Data**: Manufacturers, models, OS, configuration types, etc.

### Production-Ready Features
- **Rate Limiting**: Automatic retry with exponential backoff
- **Error Taxonomy**: Structured error types (Auth, NotFound, Validation, RateLimit, Server)
- **Pagination**: Auto-pagination with iterator support for large datasets
- **Async/Await**: Full async support throughout

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd mcp-itglue

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
pip install -e .
```

## Configuration

Set the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ITGLUE_API_KEY` | Your IT Glue API key (required) | - |
| `ITGLUE_API_URL` | IT Glue API base URL | `https://api.itglue.com` |
| `ITGLUE_TIMEOUT` | Request timeout in seconds | `30.0` |
| `ITGLUE_MAX_RETRIES` | Maximum retry attempts | `3` |

### Regional API URLs

- **US**: `https://api.itglue.com` (default)
- **EU**: `https://api.eu.itglue.com`
- **Australia**: `https://api.au.itglue.com`

### Getting an API Key

1. Log in to IT Glue
2. Go to **Account Settings** > **API Keys**
3. Generate a new API key
4. Store it securely - keys do not expire but can be revoked

## Usage

### Running the Server

```bash
# Using the installed script
mcp-itglue

# Or directly with Python
python -m mcp_itglue.server
```

### Claude Desktop Integration

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "itglue": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-itglue",
        "run",
        "mcp-itglue"
      ],
      "env": {
        "ITGLUE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Restart Claude Desktop after updating the configuration.

## Available Tools (80+)

### Organizations (5 tools)
| Tool | Description |
|------|-------------|
| `list_organizations` | List organizations with optional filters |
| `get_organization` | Get a specific organization by ID |
| `search_organizations` | Search organizations by name |
| `create_organization` | Create a new organization |
| `update_organization` | Update an existing organization |

### Configurations (5 tools)
| Tool | Description |
|------|-------------|
| `list_configurations` | List configurations with optional filters |
| `get_configuration` | Get a specific configuration by ID |
| `search_configurations` | Search configurations by name/hostname |
| `create_configuration` | Create a new configuration |
| `update_configuration` | Update an existing configuration |

### Passwords (6 tools)
| Tool | Description |
|------|-------------|
| `list_passwords` | List passwords (values hidden by default) |
| `get_password` | Get a password with optional value retrieval |
| `search_passwords` | Search passwords by name |
| `create_password` | Create a new password entry |
| `update_password` | Update an existing password |
| `delete_password` | Delete a password entry |

### Contacts (6 tools)
| Tool | Description |
|------|-------------|
| `list_contacts` | List contacts with optional filters |
| `get_contact` | Get a specific contact by ID |
| `search_contacts` | Search contacts by name |
| `create_contact` | Create a new contact |
| `update_contact` | Update an existing contact |
| `delete_contact` | Delete a contact |

### Flexible Assets (10 tools)
| Tool | Description |
|------|-------------|
| `list_flexible_asset_types` | List all flexible asset type schemas |
| `get_flexible_asset_type` | Get type with field definitions |
| `list_flexible_asset_fields` | List fields for a type |
| `list_flexible_assets` | List flexible asset instances |
| `get_flexible_asset` | Get a specific flexible asset |
| `search_flexible_assets` | Search flexible assets by name |
| `create_flexible_asset` | Create a new flexible asset |
| `update_flexible_asset` | Update an existing flexible asset |
| `delete_flexible_asset` | Delete a flexible asset |
| `get_organization_flexible_assets` | Get all flexible assets for an org |

### Checklists (10 tools)
| Tool | Description |
|------|-------------|
| `list_checklists` | List checklists with optional filters |
| `get_checklist` | Get checklist with tasks |
| `get_organization_checklists` | Get checklists for an organization |
| `create_checklist` | Create a new checklist |
| `update_checklist` | Update an existing checklist |
| `complete_checklist` | Mark a checklist as completed |
| `uncomplete_checklist` | Mark a checklist as incomplete |
| `delete_checklists` | Delete multiple checklists |
| `list_incomplete_checklists` | List incomplete/overdue checklists |

### Documents (7 tools)
| Tool | Description |
|------|-------------|
| `list_documents` | List documents with optional filters |
| `get_document` | Get document with content |
| `search_documents` | Search documents by name |
| `update_document` | Update document metadata/content |
| `get_organization_documents` | Get documents for an organization |
| `list_document_folders` | List document folders |
| `get_document_folder` | Get a specific document folder |

### Locations (7 tools)
| Tool | Description |
|------|-------------|
| `list_locations` | List locations with optional filters |
| `get_location` | Get a specific location |
| `search_locations` | Search locations by name |
| `create_location` | Create a new location |
| `update_location` | Update an existing location |
| `delete_location` | Delete a location |
| `get_organization_locations` | Get locations for an organization |

### Domains (5 tools)
| Tool | Description |
|------|-------------|
| `list_domains` | List domains with optional filters |
| `get_domain` | Get a specific domain |
| `search_domains` | Search domains by name |
| `get_organization_domains` | Get domains for an organization |
| `list_expiring_domains` | List domains expiring soon |

### Related Items (7 tools)
| Tool | Description |
|------|-------------|
| `list_related_items` | List items related to a resource |
| `create_related_item` | Create a relationship |
| `update_related_item` | Update relationship notes |
| `delete_related_items` | Delete relationships |
| `get_configuration_relationships` | Get all relationships for a config |
| `get_contact_relationships` | Get all relationships for a contact |
| `get_flexible_asset_relationships` | Get relationships for a flexible asset |

### Reference Data (15 tools)
| Tool | Description |
|------|-------------|
| `list_manufacturers` | List device manufacturers |
| `search_manufacturers` | Search manufacturers by name |
| `list_models` | List device models |
| `search_models` | Search models by name |
| `list_operating_systems` | List operating systems |
| `search_operating_systems` | Search operating systems |
| `list_configuration_types` | List configuration types |
| `list_configuration_statuses` | List configuration statuses |
| `list_contact_types` | List contact types |
| `list_organization_types` | List organization types |
| `list_organization_statuses` | List organization statuses |
| `list_password_categories` | List password categories |
| `list_countries` | List countries |
| `list_regions` | List regions for a country |
| `get_all_reference_data` | Get all reference data at once |

## Error Handling

The client provides structured error types:

```python
from mcp_itglue.client import (
    ITGlueError,           # Base error
    ITGlueAuthError,       # 401/403 - Authentication/authorization failed
    ITGlueNotFoundError,   # 404 - Resource not found
    ITGlueValidationError, # 400/422 - Request validation failed
    ITGlueConflictError,   # 409 - Resource conflict
    ITGlueRateLimitError,  # 429 - Rate limit exceeded
    ITGlueServerError,     # 5xx - Server errors
)
```

All errors include:
- `message`: Human-readable error message
- `status_code`: HTTP status code
- `errors`: List of structured error details from the API

## Rate Limiting

IT Glue API allows a maximum of 3000 requests per 5-minute window. The client automatically:
- Retries on rate limit errors (429) with exponential backoff
- Respects `Retry-After` headers when provided
- Retries on transient server errors (500, 502, 503, 504)

## Project Structure

```
mcp-itglue/
├── pyproject.toml           # Project configuration
├── README.md                 # This file
└── src/
    └── mcp_itglue/
        ├── __init__.py       # Package initialization
        ├── server.py         # Main MCP server
        ├── client.py         # IT Glue API client with retry logic
        ├── config.py         # Configuration management
        └── tools/
            ├── __init__.py
            ├── organizations.py
            ├── configurations.py
            ├── passwords.py
            ├── contacts.py
            ├── flexible_assets.py
            ├── checklists.py
            ├── documents.py
            ├── locations.py
            ├── domains.py
            ├── related_items.py
            └── reference_data.py
```

## Adding New Resources

The modular architecture makes it easy to add new IT Glue resources:

1. Create a new file in `src/mcp_itglue/tools/` (e.g., `ssl_certificates.py`)
2. Define a `register_*_tools(mcp, client)` function
3. Import and export it in `tools/__init__.py`
4. Call the registration function in `server.py`

Example:

```python
# src/mcp_itglue/tools/ssl_certificates.py
from mcp.server.fastmcp import FastMCP
from ..client import ITGlueClient, get_client

def register_ssl_certificate_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    client = client or get_client()

    @mcp.tool()
    async def list_ssl_certificates(organization_id: int | None = None) -> str:
        """List SSL certificates from IT Glue."""
        # Implementation...
```

## Development

### Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
```

### Code Formatting

```bash
ruff check .
ruff format .
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Resources

- [IT Glue API Documentation](https://api.itglue.com/developer/)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
