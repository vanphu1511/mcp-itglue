---
name: itglue-workflows
description: Workflows and important notes for using the IT Glue MCP server. Critical information about checklist creation requiring JWT authentication.
---

# IT Glue MCP Workflows

## Critical: Checklist Creation Requires JWT Authentication

**The regular `create_checklist` tool WILL FAIL.** IT Glue's API key authentication does not support checklist creation—this is an intentional limitation by Datto/Kaseya.

### To Create Checklists:

1. **Use `create_checklist_jwt`** (not `create_checklist`)
2. **Check token status first:** `jwt_token_status`
3. **If no valid token:** Tell the user to run `./capture_token.sh` in the mcp-itglue directory

### Token Lifecycle:
- Tokens are valid for **2 hours**
- Tokens are cached at `~/.config/mcp-itglue/jwt_token.json`
- When expired, user must run `./capture_token.sh` to re-authenticate via browser

### Example Workflow:

```
User: "Create a checklist for Acme Corp"

1. Call jwt_token_status
2. If status != "valid":
   - Tell user: "JWT token needed. Please run ./capture_token.sh in the mcp-itglue directory and complete SAML login."
   - Wait for user to confirm
3. Call create_checklist_jwt(organization_id=X, name="...")
```

### JWT Tools Available:

**Checklist Operations:**
- `jwt_token_status` - Check if token is valid and when it expires
- `jwt_clear_token` - Force re-authentication
- `create_checklist_jwt` - Create checklist (requires valid JWT)
- `create_checklist_from_template_jwt` - Create from template (requires valid JWT)

**Checklist Task Operations (NEW):**
- `create_checklist_task_jwt` - Add a task to a checklist
- `update_checklist_task_jwt` - Update an existing task
- `delete_checklist_task_jwt` - Delete a task
- `complete_checklist_task_jwt` - Mark a task as complete
- `uncomplete_checklist_task_jwt` - Mark a task as incomplete

**Note:** Checklist TASK creation also requires JWT authentication. The public API only supports reading tasks, not creating/modifying them.

## Standard API Key Tools

All other IT Glue operations work with the standard API key authentication:

### Organizations
- `list_organizations`, `get_organization`, `search_organizations`
- `create_organization`, `update_organization`

### Configurations (Assets/Devices)
- `list_configurations`, `get_configuration`, `search_configurations`
- `create_configuration`, `update_configuration`

### Passwords
- `list_passwords`, `get_password`, `search_passwords`
- `create_password`, `update_password`, `delete_password`

### Contacts
- `list_contacts`, `get_contact`, `search_contacts`
- `create_contact`, `update_contact`, `delete_contact`

### Flexible Assets
- `list_flexible_asset_types`, `get_flexible_asset_type`
- `list_flexible_assets`, `get_flexible_asset`, `search_flexible_assets`
- `create_flexible_asset`, `update_flexible_asset`

### Documents
- `list_documents`, `get_document`, `search_documents`
- `create_document`, `delete_document` (metadata only)
- **CONTENT requires Session Auth** - see Document Content section below

### Checklists (Read/Update only with API key)
- `list_checklists`, `get_checklist`
- `update_checklist`, `complete_checklist`, `uncomplete_checklist`
- `list_checklist_templates`, `get_checklist_template`
- **CREATE requires JWT** - see above

### Locations
- `list_locations`, `get_location`, `search_locations`
- `create_location`, `update_location`, `delete_location`

### Domains
- `list_domains`, `get_domain`, `search_domains`
- `list_expiring_domains`

### Related Items
- `list_related_items`, `create_related_item`, `delete_related_items`

### Reference Data
- `list_manufacturers`, `list_models`, `list_operating_systems`
- `list_configuration_types`, `list_configuration_statuses`
- `list_contact_types`, `list_organization_types`, `list_organization_statuses`
- `list_password_categories`, `list_countries`, `list_regions`

## Critical: Document Content Requires Session Authentication

**The regular `create_document` and `update_document` tools WILL NOT PERSIST CONTENT.** IT Glue's public API (both API key and JWT) doesn't support document content—only metadata.

### Why Session Auth?

IT Glue uses a completely different internal API for document content:
- **Endpoint**: `/{org_id}/docs/{doc_id}/versions/` (not `/documents`)
- **Domain**: Tenant subdomain (e.g., `your-company-subdomain.eu.itglue.com`)
- **Auth**: Session cookies + XSRF token (not API key or JWT Bearer)

### To Create/Update Document Content:

1. **Check session status first:** `session_status`
2. **If no valid session:** Tell the user to run `./capture_session.sh` in the mcp-itglue directory
3. **Use `create_document_jwt` or `update_document_jwt`** (these actually use session auth despite the name)

### Session Lifecycle:
- Sessions are cached at `~/.config/mcp-itglue/session_data.json`
- Sessions typically last several hours but may expire
- `session_status` validates if the session is still active
- When expired, user must run `./capture_session.sh` to re-authenticate via browser

### File Uploads:
You can also upload files (PDFs, Word docs, images, etc.) to IT Glue Documents:
- Use `upload_file_to_itglue(organization_id, file_path)` 
- Files are uploaded as GlueFiles to the org's Documents section
- Requires valid session (same as document content)

### Session Tools Available:

- `session_status` - Check if session is valid and authenticated
- `session_clear` - Force re-authentication  
- `create_document_jwt` - Create document with content (requires valid session)
- `update_document_jwt` - Update document content (requires valid session)
- `upload_file_to_itglue` - Upload files (PDF, Word, images, etc.) to Documents

### Example Workflow:

```
User: "Create a document with deployment instructions for Acme Corp"

1. Call session_status
2. If not valid:
   - Tell user: "Session needed. Please run ./capture_session.sh and navigate in IT Glue."
   - Wait for user to confirm
3. Call create_document_jwt(
     organization_id=X,
     name="Deployment Instructions",
     content="<p>Step 1: ...</p>"
   )
```

## Common Patterns

### Finding an Organization ID
```
search_organizations(query="Acme")
```

### Getting Full Organization Context
```
# Get org details
get_organization(organization_id=123)

# Get org's configurations
list_configurations(organization_id=123)

# Get org's passwords
list_passwords(organization_id=123)

# Get org's contacts
list_contacts(organization_id=123)
```

### Working with Flexible Assets
```
# First, find the asset type ID
list_flexible_asset_types()

# Then list/search assets of that type
list_flexible_assets(flexible_asset_type_id=456, organization_id=123)
```
