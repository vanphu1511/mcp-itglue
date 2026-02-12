#!/usr/bin/env python3
"""
Standalone script to capture JWT token from IT Glue browser session.

Usage:
    python capture_jwt_token.py

This opens a browser window for SAML authentication. Once you log in,
the JWT token is captured and cached for use by the MCP server.

The token is stored at: ~/.config/mcp-itglue/jwt_token.json
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_itglue.jwt_auth import get_jwt_token, get_cached_token, clear_token_cache


async def main():
    print("IT Glue JWT Token Capture")
    print("=" * 40)
    
    # Check for existing token
    existing = get_cached_token()
    if existing:
        print(f"\nExisting token found:")
        print(f"  User: {existing.email}")
        print(f"  Expires in: {existing.time_remaining_minutes} minutes")
        
        response = input("\nRefresh token anyway? [y/N]: ").strip().lower()
        if response != "y":
            print("Using existing token.")
            return
        
        clear_token_cache()
    
    print("\nOpening browser for SAML authentication...")
    print("Please log in to IT Glue in the browser window.\n")
    
    try:
        token = await get_jwt_token(force_refresh=True)
        
        print("\n" + "=" * 40)
        print("Token captured successfully!")
        print(f"  User: {token.email}")
        print(f"  Account ID: {token.account_id}")
        print(f"  Expires in: {token.time_remaining_minutes} minutes")
        print(f"\nToken cached at: ~/.config/mcp-itglue/jwt_token.json")
        print("\nYou can now use create_checklist_jwt in the MCP server.")
        
    except Exception as e:
        print(f"\nError capturing token: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
