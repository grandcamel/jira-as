"""
Shared constants for JIRA Assistant Skills.

Single source of truth for field IDs and other constants used across modules.
"""

# Default Agile field IDs (common defaults, may vary per JIRA instance)
# These can be overridden via environment variables (see config_manager.py)
DEFAULT_AGILE_FIELDS = {
    "epic_link": "customfield_10014",
    "story_points": "customfield_10016",
    "epic_name": "customfield_10011",
    "epic_color": "customfield_10012",
    "sprint": "customfield_10020",
}

# Convenience aliases for commonly used fields
EPIC_LINK_FIELD = DEFAULT_AGILE_FIELDS["epic_link"]
STORY_POINTS_FIELD = DEFAULT_AGILE_FIELDS["story_points"]
