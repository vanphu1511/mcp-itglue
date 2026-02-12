"""IT Glue MCP tools package."""

from .checklists import register_checklist_tools, register_jwt_checklist_tools
from .configurations import register_configuration_tools
from .contacts import register_contact_tools
from .documents import register_document_tools, register_jwt_document_tools
from .domains import register_domain_tools
from .flexible_assets import register_flexible_asset_tools
from .locations import register_location_tools
from .organizations import register_organization_tools
from .passwords import register_password_tools
from .reference_data import register_reference_data_tools
from .related_items import register_related_item_tools

__all__ = [
    # Core entities
    "register_organization_tools",
    "register_configuration_tools",
    "register_password_tools",
    "register_contact_tools",
    # Extended entities
    "register_flexible_asset_tools",
    "register_checklist_tools",
    "register_jwt_checklist_tools",
    "register_document_tools",
    "register_jwt_document_tools",
    "register_location_tools",
    "register_domain_tools",
    # Relationships
    "register_related_item_tools",
    # Reference data
    "register_reference_data_tools",
]
