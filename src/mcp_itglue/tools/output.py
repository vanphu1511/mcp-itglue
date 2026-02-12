"""Output formatting utilities for IT Glue MCP tools.

Provides compact output modes and file saving to reduce context window usage.
"""

import json
import tempfile
import time
from enum import Enum
from typing import Any


class OutputFormat(str, Enum):
    """Output format modes for list/search results."""

    FULL = "full"  # All fields (current default behavior)
    COMPACT = "compact"  # Essential fields only (id, name, key identifier)
    SUMMARY = "summary"  # Just count and list of IDs


# Compact field definitions for each entity type
# Maps entity type to list of fields to include in compact mode
COMPACT_FIELDS: dict[str, list[str]] = {
    "organization": ["id", "name", "organization_type", "organization_status"],
    "configuration": ["id", "name", "hostname", "primary_ip", "organization_id"],
    "password": ["id", "name", "username", "organization_id"],
    "contact": ["id", "name", "title", "organization_id"],
    "flexible_asset": ["id", "name", "flexible_asset_type_id", "organization_id"],
    "flexible_asset_type": ["id", "name", "enabled"],
    "flexible_asset_field": ["id", "name", "kind", "required"],
    "document": ["id", "name", "organization_id"],
    "document_folder": ["id", "name", "organization_id", "parent_folder_id"],
    "location": ["id", "name", "city", "organization_id"],
    "domain": ["id", "name", "expires_at", "organization_id"],
    "checklist": ["id", "name", "completed", "due_date", "organization_id"],
    "checklist_task": ["id", "name", "completed", "checklist_id"],
    # Reference data types
    "manufacturer": ["id", "name"],
    "model": ["id", "name", "manufacturer_id"],
    "operating_system": ["id", "name"],
    "configuration_type": ["id", "name"],
    "configuration_status": ["id", "name"],
    "contact_type": ["id", "name"],
    "organization_type": ["id", "name"],
    "organization_status": ["id", "name"],
    "country": ["id", "name", "iso"],
    "region": ["id", "name", "country_id"],
    "password_category": ["id", "name"],
    # Related items
    "related_item": ["id", "resource_type", "resource_id", "resource_name"],
}


def _filter_to_compact(item: dict[str, Any], entity_type: str) -> dict[str, Any]:
    """Filter an item to only include compact fields."""
    fields = COMPACT_FIELDS.get(entity_type, ["id", "name"])
    return {k: v for k, v in item.items() if k in fields}


def _extract_summary(items: list[dict[str, Any]], entity_type: str) -> dict[str, Any]:
    """Extract summary information from items."""
    return {
        "count": len(items),
        "ids": [item.get("id") for item in items],
        "names": [item.get("name") for item in items if item.get("name")],
    }


def save_to_temp_file(data: dict[str, Any], prefix: str = "itglue") -> str:
    """Save data to a temporary JSON file.

    Args:
        data: The data to save
        prefix: Prefix for the temp filename

    Returns:
        Path to the created temp file
    """
    timestamp = int(time.time())
    filename = f"{prefix}_{timestamp}.json"
    filepath = f"/tmp/{filename}"

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return filepath


def format_list_output(
    items: list[dict[str, Any]],
    entity_type: str,
    list_key: str,
    output_format: str = "compact",
    save_to_file: bool = False,
    extra_fields: dict[str, Any] | None = None,
) -> str:
    """Format list output with support for compact mode and file saving.

    Args:
        items: List of formatted items
        entity_type: Type of entity (e.g., "organization", "configuration")
        list_key: Key name for the list in output (e.g., "organizations")
        output_format: One of "full", "compact", "summary"
        save_to_file: If True, save full data to temp file and return path
        extra_fields: Additional fields to include in the result (e.g., total_count, page)

    Returns:
        JSON string with formatted output
    """
    extra = extra_fields or {}

    # If saving to file, write full data and return reference
    if save_to_file:
        full_result = {
            list_key: items,
            **extra,
        }
        filepath = save_to_temp_file(full_result, f"itglue_{entity_type}")
        return json.dumps(
            {
                "saved_to_file": filepath,
                "count": len(items),
                "total_count": extra.get("total_count", len(items)),
                "message": f"Full results saved to {filepath}. Use jq to query.",
            },
            indent=2,
        )

    # Format based on output mode
    fmt = OutputFormat(output_format) if output_format in OutputFormat.__members__.values() else OutputFormat.COMPACT

    if fmt == OutputFormat.SUMMARY:
        result = {
            **_extract_summary(items, entity_type),
            **{k: v for k, v in extra.items() if k in ("total_count", "page", "page_size")},
        }
    elif fmt == OutputFormat.COMPACT:
        result = {
            list_key: [_filter_to_compact(item, entity_type) for item in items],
            "count": len(items),
            **{k: v for k, v in extra.items() if k in ("total_count", "page", "page_size")},
        }
    else:  # FULL
        result = {
            list_key: items,
            **extra,
        }

    return json.dumps(result, indent=2)


def format_search_output(
    items: list[dict[str, Any]],
    entity_type: str,
    list_key: str,
    query: str,
    output_format: str = "compact",
    save_to_file: bool = False,
    extra_fields: dict[str, Any] | None = None,
) -> str:
    """Format search output with support for compact mode and file saving.

    Args:
        items: List of formatted items
        entity_type: Type of entity
        list_key: Key name for the list in output
        query: The search query string
        output_format: One of "full", "compact", "summary"
        save_to_file: If True, save full data to temp file
        extra_fields: Additional fields to include

    Returns:
        JSON string with formatted output
    """
    extra = extra_fields or {}
    extra["query"] = query
    extra["count"] = len(items)

    return format_list_output(
        items=items,
        entity_type=entity_type,
        list_key=list_key,
        output_format=output_format,
        save_to_file=save_to_file,
        extra_fields=extra,
    )
