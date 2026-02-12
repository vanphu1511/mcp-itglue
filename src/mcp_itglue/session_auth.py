"""Session-based authentication for IT Glue internal APIs.

IT Glue has two different API mechanisms:
1. Public API (api.eu.itglue.com) - Uses API keys or JWT Bearer tokens
   - Works for most operations including checklist creation with JWT
2. Internal Web API ({tenant}.eu.itglue.com) - Uses session cookies + XSRF token
   - Required for document content operations (the /docs/{id}/versions/ endpoint)

This module manages the session-based authentication for internal APIs.

Browser Persistence:
- By default, browser closes after session capture
- Set KEEP_BROWSER_OPEN=True to keep browser open for subsequent operations
- Use close_browser() to manually close when done
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Optional dependency - only needed when capturing sessions
try:
    from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .config import logger

# Session cache location
SESSION_CACHE_DIR = Path.home() / ".config" / "mcp-itglue"
SESSION_CACHE_FILE = SESSION_CACHE_DIR / "session_data.json"

# Session refresh - check every 30 minutes
SESSION_REFRESH_INTERVAL = 1800

# Browser persistence settings
KEEP_BROWSER_OPEN = False  # Toggle: if True, browser stays open after auth

# Module-level browser state (for persistence)
_playwright_instance: "Playwright | None" = None
_browser_context: "BrowserContext | None" = None
_browser_page: "Page | None" = None


@dataclass
class ITGlueSession:
    """Represents an authenticated IT Glue session with cookies and XSRF token."""
    
    tenant_subdomain: str  # e.g., "guidance-technologies-limited"
    xsrf_token: str
    cookies: list[dict[str, Any]]  # Playwright cookie format
    captured_at: int  # Unix timestamp
    
    @property
    def base_url(self) -> str:
        """Get the tenant-specific base URL."""
        return f"https://{self.tenant_subdomain}.eu.itglue.com"
    
    @property
    def age_seconds(self) -> int:
        """How old is this session in seconds."""
        return int(time.time() - self.captured_at)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for caching."""
        return {
            "tenant_subdomain": self.tenant_subdomain,
            "xsrf_token": self.xsrf_token,
            "cookies": self.cookies,
            "captured_at": self.captured_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ITGlueSession":
        """Deserialize from cache."""
        return cls(
            tenant_subdomain=data["tenant_subdomain"],
            xsrf_token=data["xsrf_token"],
            cookies=data["cookies"],
            captured_at=data["captured_at"],
        )


def _save_session_to_cache(session: ITGlueSession) -> None:
    """Save session to disk cache."""
    SESSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SESSION_CACHE_FILE, "w") as f:
        json.dump(session.to_dict(), f, indent=2)
    SESSION_CACHE_FILE.chmod(0o600)
    logger.info(f"Session cached to {SESSION_CACHE_FILE}")


def _load_session_from_cache() -> ITGlueSession | None:
    """Load session from disk cache if exists."""
    if not SESSION_CACHE_FILE.exists():
        return None
    
    try:
        with open(SESSION_CACHE_FILE) as f:
            data = json.load(f)
        session = ITGlueSession.from_dict(data)
        logger.info(f"Loaded cached session for {session.tenant_subdomain}, age: {session.age_seconds}s")
        return session
    except Exception as e:
        logger.warning(f"Failed to load cached session: {e}")
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

    # Use persistent context for cookie retention
    # Use same profile as JWT auth so user only authenticates once
    user_data_dir = SESSION_CACHE_DIR / "browser_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    # Use Chromium (same as JWT auth) for unified authentication
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


async def capture_session_from_browser(
    itglue_subdomain: str = "guidance-technologies-limited.eu",
    headless: bool = False,
    timeout_seconds: int = 120,
    keep_open: bool | None = None,
) -> ITGlueSession:
    """
    Capture session data (cookies, XSRF token, tenant) from browser.

    Opens a browser, waits for SAML auth, then captures:
    - Session cookies
    - XSRF token (from cookie or header)
    - Tenant subdomain (from URL after redirect)

    Args:
        itglue_subdomain: IT Glue subdomain to start (e.g., "encyro.eu")
        headless: Run browser in headless mode
        timeout_seconds: Max time to wait for auth
        keep_open: Override KEEP_BROWSER_OPEN setting. If None, uses global setting.

    Returns:
        Captured session data
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is required for session capture. "
            "Install with: pip install playwright && playwright install chromium"
        )

    # Determine whether to keep browser open
    should_keep_open = keep_open if keep_open is not None else KEEP_BROWSER_OPEN

    captured_xsrf: str | None = None
    captured_tenant: str | None = None

    # Get or create browser
    browser, page = await _get_or_create_browser(headless=headless)

    try:
        # Capture XSRF token from requests
        async def handle_request(request):
            nonlocal captured_xsrf, captured_tenant

            url = request.url
            headers = request.headers

            # Capture XSRF token from header
            if "x-xsrf-token" in headers and not captured_xsrf:
                captured_xsrf = headers["x-xsrf-token"]
                logger.info("Captured XSRF token from request header")

            # Capture tenant from URL pattern
            # e.g., https://guidance-technologies-limited.eu.itglue.com/...
            if ".eu.itglue.com" in url and not captured_tenant:
                match = re.match(r"https://([^.]+)\.eu\.itglue\.com", url)
                if match and match.group(1) not in ["app", "api", "encyro"]:
                    captured_tenant = match.group(1)
                    logger.info(f"Captured tenant subdomain: {captured_tenant}")

        page.on("request", handle_request)

        # Navigate to IT Glue
        itglue_url = f"https://{itglue_subdomain}.itglue.com/"
        logger.info(f"Navigating to {itglue_url}")
        await page.goto(itglue_url, wait_until="networkidle")

        # Wait for authentication and data capture
        start_time = time.time()
        while not (captured_xsrf and captured_tenant):
            if time.time() - start_time > timeout_seconds:
                if not should_keep_open:
                    await close_browser()
                raise RuntimeError(
                    f"Timeout waiting for session capture after {timeout_seconds}s. "
                    "Make sure you completed SAML login and navigated within IT Glue."
                )

            current_url = page.url
            if "login" in current_url.lower() or "saml" in current_url.lower():
                logger.info("Waiting for SAML authentication...")
            elif captured_tenant and not captured_xsrf:
                logger.info("Authenticated - waiting for XSRF token (try navigating in IT Glue)...")

            await asyncio.sleep(1)

        # Get all cookies
        cookies = await browser.cookies()

        # Remove the request handler to avoid duplicate captures
        page.remove_listener("request", handle_request)

    finally:
        # Only close browser if not keeping it open
        if not should_keep_open:
            await close_browser()
        else:
            logger.info("Browser kept open for subsequent operations")

    # Create and cache session
    session = ITGlueSession(
        tenant_subdomain=captured_tenant,
        xsrf_token=captured_xsrf,
        cookies=cookies,
        captured_at=int(time.time()),
    )

    _save_session_to_cache(session)

    logger.info(f"Session captured for tenant: {captured_tenant}")
    return session


async def get_session(
    force_refresh: bool = False,
    itglue_subdomain: str = "guidance-technologies-limited.eu",
    keep_open: bool | None = None,
) -> ITGlueSession:
    """
    Get a valid session, capturing new one if needed.

    Args:
        force_refresh: Force new session capture
        itglue_subdomain: IT Glue subdomain for auth
        keep_open: Override KEEP_BROWSER_OPEN setting. If None, uses global setting.

    Returns:
        Valid session data
    """
    if not force_refresh:
        cached = _load_session_from_cache()
        if cached is not None:
            logger.info(f"Using cached session for tenant: {cached.tenant_subdomain}")
            return cached

    logger.info("Capturing new session from browser...")
    return await capture_session_from_browser(
        itglue_subdomain=itglue_subdomain,
        keep_open=keep_open,
    )


def get_cached_session() -> ITGlueSession | None:
    """Get cached session without triggering browser auth."""
    return _load_session_from_cache()


def clear_session_cache() -> None:
    """Clear the session cache."""
    if SESSION_CACHE_FILE.exists():
        SESSION_CACHE_FILE.unlink()
        logger.info("Session cache cleared")
