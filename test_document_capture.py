#!/usr/bin/env python3
"""
Capture the exact API request format for document creation in IT Glue.

This script opens a browser to IT Glue, lets you log in and create a document,
and captures the exact API request format used by the web UI.
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def capture_document_creation():
    """Open browser to capture document creation requests."""
    
    # Store captured requests
    captured_requests = []
    
    async with async_playwright() as p:
        # Launch browser with persistent context for session
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set up request interception
        async def handle_request(request):
            if "/documents" in request.url and request.method in ("POST", "PATCH"):
                try:
                    post_data = request.post_data
                    if post_data:
                        captured_requests.append({
                            "url": request.url,
                            "method": request.method,
                            "headers": dict(request.headers),
                            "body": post_data,
                        })
                        print(f"\n{'='*60}")
                        print(f"CAPTURED {request.method} to {request.url}")
                        print(f"{'='*60}")
                        print(f"Headers: {json.dumps(dict(request.headers), indent=2)}")
                        print(f"\nBody:\n{post_data}")
                        print(f"{'='*60}\n")
                except Exception as e:
                    print(f"Error capturing request: {e}")
        
        async def handle_response(response):
            if "/documents" in response.url and response.request.method in ("POST", "PATCH"):
                try:
                    body = await response.text()
                    print(f"\n{'='*60}")
                    print(f"RESPONSE from {response.url}")
                    print(f"Status: {response.status}")
                    print(f"{'='*60}")
                    print(f"Body:\n{body[:2000]}...")
                    print(f"{'='*60}\n")
                except Exception as e:
                    print(f"Error capturing response: {e}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # Navigate to IT Glue EU
        print("Navigating to IT Glue...")
        await page.goto("https://eu.itglue.com")
        
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                   DOCUMENT CAPTURE INSTRUCTIONS                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  1. Log in if needed (should be SSO/SAML)                       ║
║                                                                  ║
║  2. Navigate to an organization                                  ║
║                                                                  ║
║  3. Go to Documents section                                      ║
║                                                                  ║
║  4. Create a NEW document with some content                      ║
║                                                                  ║
║  5. Save the document                                            ║
║                                                                  ║
║  The script will capture the API request details                 ║
║                                                                  ║
║  When done, close the browser or press Ctrl+C                    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")
        
        # Wait for browser to be closed
        try:
            while True:
                await asyncio.sleep(1)
                # Check if page is still open
                if page.is_closed():
                    break
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        await browser.close()
        
        # Output summary
        print("\n" + "="*60)
        print("CAPTURE SUMMARY")
        print("="*60)
        print(f"Captured {len(captured_requests)} document API requests")
        
        if captured_requests:
            # Save to file
            with open("document_api_capture.json", "w") as f:
                json.dump(captured_requests, f, indent=2)
            print(f"Saved to document_api_capture.json")


if __name__ == "__main__":
    asyncio.run(capture_document_creation())
