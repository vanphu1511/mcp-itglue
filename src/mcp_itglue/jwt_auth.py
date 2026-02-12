"""JWT token capture from IT Glue SAML session using Playwright.

This module handles capturing Bearer tokens from authenticated IT Glue
browser sessions. These tokens are required for certain API operations
(like checklist creation) that don't work with API key authentication.

Token Lifecycle:
- Tokens are valid for 2 hours after issuance
- Tokens are cached to disk and reused until near expiration
- When tokens expire, a browser window opens for re-authentication

Browser Persistence:
- By default, browser closes after token capture
- Set KEEP_BROWSER_OPEN=True to keep browser open for subsequent operations
- Use close_browser() to manually close when done
"""

import asyncio
import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Optional dependency - only needed when capturing tokens
try:
    from playwright.async_api import async_playwright, Page, BrowserContext, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .config import logger

# Token cache location
TOKEN_CACHE_DIR = Path.home() / ".config" / "mcp-itglue"
TOKEN_CACHE_FILE = TOKEN_CACHE_DIR / "jwt_token.json"

# Refresh tokens 10 minutes before expiration
TOKEN_REFRESH_BUFFER_SECONDS = 600

# Browser persistence settings
KEEP_BROWSER_OPEN = False  # Toggle: if True, browser stays open after auth

# Module-level browser state (for persistence)
_playwright_instance: "Playwright | None" = None
_browser_context: "BrowserContext | None" = None
_browser_page: "Page | None" = None


@dataclass
class JWTToken:
    """Represents a captured JWT token with metadata."""
    
    token: str
    issued_at: int  # Unix timestamp
    expires_at: int  # Unix timestamp
    user_id: int
    account_id: int
    email: str
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired or will expire soon."""
        return time.time() >= (self.expires_at - TOKEN_REFRESH_BUFFER_SECONDS)
    
    @property
    def time_remaining_seconds(self) -> int:
        """Seconds until token expires."""
        return max(0, int(self.expires_at - time.time()))
    
    @property
    def time_remaining_minutes(self) -> int:
        """Minutes until token expires."""
        return self.time_remaining_seconds // 60
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for caching."""
        return {
            "token": self.token,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "email": self.email,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JWTToken":
        """Deserialize from dictionary."""
        return cls(
            token=data["token"],
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            user_id=data["user_id"],
            account_id=data["account_id"],
            email=data["email"],
        )
    
    @classmethod
    def from_jwt(cls, token: str) -> "JWTToken":
        """Parse token metadata from JWT payload."""
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (base64url)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        return cls(
            token=token,
            issued_at=payload.get("iat", 0),
            expires_at=payload.get("exp", 0),
            user_id=payload.get("id", payload.get("sub", 0)),
            account_id=payload.get("itglue", {}).get("account_id", 0),
            email=payload.get("itglue", {}).get("email", ""),
        )


def _save_token_to_cache(token: JWTToken) -> None:
    """Save token to disk cache."""
    TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(token.to_dict(), f, indent=2)
    # Restrict permissions (owner read/write only)
    TOKEN_CACHE_FILE.chmod(0o600)
    logger.info(f"Token cached to {TOKEN_CACHE_FILE}")


def _load_token_from_cache() -> JWTToken | None:
    """Load token from disk cache if valid."""
    if not TOKEN_CACHE_FILE.exists():
        return None
    
    try:
        with open(TOKEN_CACHE_FILE) as f:
            data = json.load(f)
        token = JWTToken.from_dict(data)
        
        if token.is_expired:
            logger.info("Cached token is expired or expiring soon")
            return None
        
        logger.info(f"Loaded cached token, {token.time_remaining_minutes} minutes remaining")
        return token
    except Exception as e:
        logger.warning(f"Failed to load cached token: {e}")
        return None


async def _get_or_create_browser(
    headless: bool = False,
) -> tuple["BrowserContext", "Page"]:
    """
    Get existing browser or create a new one.

    If KEEP_BROWSER_OPEN is True, reuses the existing browser instance.
    Otherwise, creates a new browser each time.

    Returns:
        Tuple of (browser_context, page)
    """
    global _playwright_instance, _browser_context, _browser_page

    # If we have an existing browser and it's still open, reuse it
    if _browser_context is not None and _browser_page is not None:
        try:
            # Check if browser is still responsive
            _ = _browser_page.url
            logger.info("Reusing existing browser session")
            return _browser_context, _browser_page
        except Exception:
            # Browser was closed externally, clean up
            logger.info("Previous browser session closed, creating new one")
            _browser_context = None
            _browser_page = None
            if _playwright_instance:
                await _playwright_instance.stop()
                _playwright_instance = None

    # Create new playwright instance
    if _playwright_instance is None:
        _playwright_instance = await async_playwright().start()

    # Use persistent context to retain cookies across sessions
    user_data_dir = TOKEN_CACHE_DIR / "browser_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    _browser_context = await _playwright_instance.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=headless,
        viewport={"width": 1280, "height": 800},
    )

    _browser_page = _browser_context.pages[0] if _browser_context.pages else await _browser_context.new_page()

    return _browser_context, _browser_page


async def close_browser() -> None:
    """
    Close the persistent browser if open.

    Call this when you're done with browser operations to clean up resources.
    """
    global _playwright_instance, _browser_context, _browser_page

    if _browser_context is not None:
        try:
            await _browser_context.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        _browser_context = None
        _browser_page = None

    if _playwright_instance is not None:
        try:
            await _playwright_instance.stop()
        except Exception as e:
            logger.warning(f"Error stopping playwright: {e}")
        _playwright_instance = None


def is_browser_open() -> bool:
    """Check if the persistent browser is currently open."""
    return _browser_context is not None and _browser_page is not None


def set_keep_browser_open(value: bool) -> None:
    """
    Set whether the browser should stay open after authentication.

    Args:
        value: True to keep browser open, False to close after auth
    """
    global KEEP_BROWSER_OPEN
    KEEP_BROWSER_OPEN = value
    logger.info(f"Browser persistence {'enabled' if value else 'disabled'}")


def get_keep_browser_open() -> bool:
    """Get the current browser persistence setting."""
    return KEEP_BROWSER_OPEN


async def _capture_token_from_browser(
    itglue_subdomain: str = "app.eu",
    headless: bool = False,
    timeout_seconds: int = 120,
    keep_open: bool | None = None,
) -> JWTToken:
    """
    Capture JWT token by intercepting requests in an authenticated browser session.

    This opens a browser window, navigates to IT Glue, and waits for the user
    to complete SAML authentication. Once authenticated, it captures the
    Bearer token from API requests.

    Args:
        itglue_subdomain: IT Glue subdomain (e.g., "app.eu" for EU region)
        headless: Run browser in headless mode (requires saved session/cookies)
        timeout_seconds: Maximum time to wait for authentication
        keep_open: Override KEEP_BROWSER_OPEN setting for this call.
                   If None, uses the global KEEP_BROWSER_OPEN setting.

    Returns:
        Captured JWT token with metadata

    Raises:
        RuntimeError: If playwright not installed or token capture fails
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is required for JWT token capture. "
            "Install with: pip install playwright && playwright install chromium"
        )

    # Determine whether to keep browser open
    should_keep_open = keep_open if keep_open is not None else KEEP_BROWSER_OPEN

    captured_token: str | None = None

    # Get or create browser
    browser, page = await _get_or_create_browser(headless=headless)

    try:
        # Set up request interception to capture Bearer token
        async def handle_request(request):
            nonlocal captured_token
            url = request.url
            if "itg-api-prod" in url or "api.eu.itglue.com" in url or "api.itglue.com" in url:
                auth_header = request.headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    captured_token = auth_header[7:]  # Strip "Bearer " prefix
                    logger.info("Captured JWT token from API request")

        page.on("request", handle_request)

        # Navigate to IT Glue
        itglue_url = f"https://{itglue_subdomain}.itglue.com/"
        logger.info(f"Navigating to {itglue_url}")
        await page.goto(itglue_url, wait_until="networkidle")

        # Wait for token capture or timeout
        start_time = time.time()
        while captured_token is None:
            if time.time() - start_time > timeout_seconds:
                if not should_keep_open:
                    await close_browser()
                raise RuntimeError(
                    f"Timeout waiting for authentication after {timeout_seconds}s. "
                    "Make sure you completed SAML login in the browser window."
                )

            # Check if we're on a login page
            current_url = page.url
            if "login" in current_url.lower() or "saml" in current_url.lower():
                logger.info("Waiting for SAML authentication...")

            await asyncio.sleep(1)

        # Remove the request handler to avoid duplicate captures
        page.remove_listener("request", handle_request)

    finally:
        # Only close browser if not keeping it open
        if not should_keep_open:
            await close_browser()
        else:
            logger.info("Browser kept open for subsequent operations")

    # Parse and return token
    token = JWTToken.from_jwt(captured_token)
    logger.info(
        f"Token captured successfully. "
        f"User: {token.email}, "
        f"Expires in {token.time_remaining_minutes} minutes"
    )

    # Cache the token
    _save_token_to_cache(token)

    return token


async def get_jwt_token(
    force_refresh: bool = False,
    itglue_subdomain: str = "app.eu",
    headless: bool = False,
    keep_open: bool | None = None,
) -> JWTToken:
    """
    Get a valid JWT token, refreshing if necessary.

    This function first checks for a cached token. If the cached token
    is valid, it returns immediately. Otherwise, it opens a browser
    window for the user to authenticate.

    Args:
        force_refresh: Force token refresh even if cached token is valid
        itglue_subdomain: IT Glue subdomain for authentication
        headless: Run browser in headless mode
        keep_open: Override KEEP_BROWSER_OPEN setting. If None, uses global setting.

    Returns:
        Valid JWT token
    """
    if not force_refresh:
        cached_token = _load_token_from_cache()
        if cached_token is not None:
            logger.info(f"Using cached token (expires in {cached_token.time_remaining_minutes} min)")
            return cached_token

    logger.info("Capturing new JWT token from browser session...")
    return await _capture_token_from_browser(
        itglue_subdomain=itglue_subdomain,
        headless=headless,
        keep_open=keep_open,
    )


def get_cached_token() -> JWTToken | None:
    """
    Get cached token without triggering browser authentication.
    
    Returns None if no valid cached token exists.
    """
    return _load_token_from_cache()


def clear_token_cache() -> None:
    """Clear the token cache file."""
    if TOKEN_CACHE_FILE.exists():
        TOKEN_CACHE_FILE.unlink()
        logger.info("Token cache cleared")
