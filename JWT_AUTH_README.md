# IT Glue JWT Authentication for Checklist Creation

## Problem
IT Glue's API key authentication doesn't support checklist creation (`POST /checklists`). The API returns "Only supported for JWT requests: Unauthorized resource access".

## Solution
Capture JWT Bearer tokens from authenticated browser sessions (SAML/SSO login) and use those for checklist API calls.

## Implementation

### New Files Created

1. **`src/mcp_itglue/jwt_auth.py`** - Token capture and caching
   - Captures JWT tokens from browser sessions using Playwright
   - Caches tokens to `~/.config/mcp-itglue/jwt_token.json`
   - Tokens valid for 2 hours, auto-refresh 10 minutes before expiry

2. **`src/mcp_itglue/jwt_client.py`** - JWT-authenticated HTTP client
   - Uses captured Bearer tokens instead of API keys
   - Specifically for operations that require JWT auth

3. **`capture_jwt_token.py`** - Standalone token capture script
   - Run manually to capture/refresh tokens
   - Usage: `python capture_jwt_token.py`

### Modified Files

1. **`src/mcp_itglue/tools/checklists.py`** - Added JWT tools:
   - `jwt_token_status` - Check cached token status
   - `jwt_clear_token` - Clear cached token
   - `create_checklist_jwt` - Create checklist with JWT auth
   - `create_checklist_from_template_jwt` - Create from template with JWT auth

2. **`src/mcp_itglue/tools/__init__.py`** - Export new tools

3. **`src/mcp_itglue/server.py`** - Register JWT tools

4. **`pyproject.toml`** - Added optional `jwt` dependency group for Playwright

## Usage

### Installation
```bash
# Install with JWT support
pip install -e ".[jwt]"

# Install Playwright browsers
playwright install chromium
```

### Capturing a Token
```bash
# Option 1: Standalone script
python capture_jwt_token.py

# Option 2: Auto-capture when using MCP tools
# (browser window opens automatically if no valid token)
```

### Using in MCP
```python
# Check token status
jwt_token_status()

# Create checklist (auto-captures token if needed)
create_checklist_jwt(
    organization_id=123,
    name="My Checklist",
    description="Created via JWT auth"
)

# Create from template
create_checklist_from_template_jwt(
    organization_id=123,
    checklist_template_id=456
)
```

## How It Works

1. **Token Capture**: Playwright opens a browser, navigates to IT Glue, user completes SAML login
2. **Token Interception**: Request listener captures `Authorization: Bearer <jwt>` headers from API calls
3. **Token Caching**: Token saved to disk with metadata (expiry, user info)
4. **Token Reuse**: Subsequent API calls use cached token until it expires
5. **Auto-Refresh**: When token expires, browser opens again for re-auth

## Token Details (from recon)

```json
{
  "header": {
    "typ": "JWT",
    "alg": "RS256"
  },
  "payload": {
    "sub": 4521410723414257,
    "iss": "itglue.com",
    "aud": ["itglue.com", "bms.kaseya.com"],
    "exp": 1769710447,  // 2 hours from issuance
    "iat": 1769703247,
    "itglue": {
      "account_id": 3531876280484020,
      "email": "jdeane@iglutech.com"
    }
  }
}
```

## API Endpoint

- **URL**: `https://api.eu.itglue.com/checklists`
- **Method**: POST
- **Auth**: `Authorization: Bearer <jwt_token>`
- **Content-Type**: `application/vnd.api+json`

## Notes

- Tokens are signed with RS256 (IT Glue's private key) - we cannot mint our own
- Browser profile is persisted at `~/.config/mcp-itglue/browser_profile/` for session cookies
- Token cache file has restricted permissions (0600)
- Playwright is an optional dependency - MCP server works without it (just can't create checklists)
