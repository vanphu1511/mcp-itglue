#!/usr/bin/env python3
"""
Capture IT Glue session data for document operations.

IT Glue document content requires session-based authentication (cookies + XSRF token)
because the public API doesn't persist document content. This script captures the
required session data from an authenticated browser session.

Usage:
    python capture_session.py

The script will:
1. Open a browser window
2. Navigate to IT Glue (you may need to complete SAML login)
3. Capture session cookies and XSRF token
4. Save session data to ~/.config/mcp-itglue/session_data.json

Once captured, the session can be used by the MCP server for document operations.
"""

import asyncio
import sys


async def main():
    # Add parent directory to path for imports
    sys.path.insert(0, str(__file__).rsplit("/", 1)[0])
    
    from src.mcp_itglue.session_auth import capture_session_from_browser
    
    print("=" * 60)
    print("IT Glue Session Capture")
    print("=" * 60)
    print()
    print("This will open a browser window for IT Glue authentication.")
    print("Complete the SAML login, then navigate within IT Glue.")
    print("The script will capture session data automatically.")
    print()
    
    try:
        session = await capture_session_from_browser(
            itglue_subdomain="app.eu",
            headless=False,
            timeout_seconds=180,
        )
        
        print()
        print("=" * 60)
        print("✓ Session captured successfully!")
        print("=" * 60)
        print(f"  Tenant: {session.tenant_subdomain}")
        print(f"  Base URL: {session.base_url}")
        print(f"  XSRF Token: {session.xsrf_token[:20]}...")
        print(f"  Cookies: {len(session.cookies)} captured")
        print()
        print("Session data saved. Document operations are now available.")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
