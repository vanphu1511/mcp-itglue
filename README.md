# MCP IT Glue Server

A Model Context Protocol (MCP) server for IT Glue API integration. This server enables AI assistants like Claude to interact with IT Glue documentation and asset management system.

## Features

- **Organizations**: List, search, create, and update organizations
- **Configurations**: Manage devices and assets with full CRUD operations
- **Passwords**: Secure password management with controlled access
- **Contacts**: Manage contact information for organizations

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

## Available Tools

### Organizations

| Tool | Description |
|------|-------------|
| `list_organizations` | List organizations with optional filters |
| `get_organization` | Get a specific organization by ID |
| `search_organizations` | Search organizations by name |
| `create_organization` | Create a new organization |
| `update_organization` | Update an existing organization |

### Configurations (Devices/Assets)

| Tool | Description |
|------|-------------|
| `list_configurations` | List configurations with optional filters |
| `get_configuration` | Get a specific configuration by ID |
| `search_configurations` | Search configurations by name/hostname |
| `create_configuration` | Create a new configuration |
| `update_configuration` | Update an existing configuration |

### Passwords

| Tool | Description |
|------|-------------|
| `list_passwords` | List passwords (values hidden by default) |
| `get_password` | Get a password with optional value retrieval |
| `search_passwords` | Search passwords by name |
| `create_password` | Create a new password entry |
| `update_password` | Update an existing password |
| `delete_password` | Delete a password entry |

### Contacts

| Tool | Description |
|------|-------------|
| `list_contacts` | List contacts with optional filters |
| `get_contact` | Get a specific contact by ID |
| `search_contacts` | Search contacts by name |
| `create_contact` | Create a new contact |
| `update_contact` | Update an existing contact |
| `delete_contact` | Delete a contact |

## Project Structure

```
mcp-itglue/
├── pyproject.toml           # Project configuration
├── README.md                 # This file
├── LICENSE                   # MIT License
└── src/
    └── mcp_itglue/
        ├── __init__.py       # Package initialization
        ├── server.py         # Main MCP server
        ├── client.py         # IT Glue API client
        ├── config.py         # Configuration management
        └── tools/
            ├── __init__.py
            ├── organizations.py
            ├── configurations.py
            ├── passwords.py
            └── contacts.py
```

## Adding New Resources

The modular architecture makes it easy to add new IT Glue resources:

1. Create a new file in `src/mcp_itglue/tools/` (e.g., `locations.py`)
2. Define a `register_*_tools(mcp, client)` function
3. Import and call it in `tools/__init__.py`
4. Call the registration function in `server.py`

Example:

```python
# src/mcp_itglue/tools/locations.py
def register_location_tools(mcp: FastMCP, client: ITGlueClient | None = None) -> None:
    client = client or get_client()

    @mcp.tool()
    async def list_locations(organization_id: int | None = None) -> str:
        """List locations from IT Glue."""
        # Implementation...
```

## Rate Limiting

IT Glue API allows a maximum of 3000 requests per 5-minute window. The client handles rate limit errors (HTTP 429) with appropriate error messages.

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
