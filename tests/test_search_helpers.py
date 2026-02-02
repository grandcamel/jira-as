"""
Tests for search_helpers module.
"""

import pytest
from assistant_skills_lib.error_handler import ValidationError

from jira_as.search_helpers import fuzzy_find_by_name, fuzzy_find_by_name_optional


class TestFuzzyFindByName:
    """Tests for fuzzy_find_by_name function."""

    def test_exact_match_case_insensitive(self):
        """Test exact match is case-insensitive."""
        items = [{"name": "Done"}, {"name": "In Progress"}, {"name": "To Do"}]
        result = fuzzy_find_by_name(items, "done", item_type="status")
        assert result["name"] == "Done"

    def test_exact_match_uppercase(self):
        """Test exact match with uppercase input."""
        items = [{"name": "Done"}, {"name": "In Progress"}]
        result = fuzzy_find_by_name(items, "DONE", item_type="status")
        assert result["name"] == "Done"

    def test_partial_match_fuzzy(self):
        """Test partial match with fuzzy enabled."""
        items = [{"name": "In Progress"}, {"name": "Done"}]
        result = fuzzy_find_by_name(items, "progress", item_type="status")
        assert result["name"] == "In Progress"

    def test_partial_match_disabled(self):
        """Test partial match fails when fuzzy is disabled."""
        items = [{"name": "In Progress"}, {"name": "Done"}]
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name(items, "progress", item_type="status", fuzzy=False)
        assert "not found" in str(exc_info.value)
        assert "In Progress" in str(exc_info.value)

    def test_empty_items_raises(self):
        """Test empty items list raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name([], "test", item_type="transition")
        assert "No transitions available" in str(exc_info.value)

    def test_not_found_raises(self):
        """Test not found raises ValidationError with available options."""
        items = [{"name": "Done"}, {"name": "In Progress"}]
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name(items, "nonexistent", item_type="status")
        assert "not found" in str(exc_info.value)
        assert "Done" in str(exc_info.value)
        assert "In Progress" in str(exc_info.value)

    def test_multiple_exact_matches_raises(self):
        """Test multiple exact matches raises ValidationError."""
        items = [{"name": "Done"}, {"name": "done"}]  # Both match "done" exactly
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name(items, "done", item_type="status")
        assert "Multiple exact matches" in str(exc_info.value)

    def test_ambiguous_partial_match_raises(self):
        """Test ambiguous partial match raises ValidationError."""
        items = [{"name": "In Progress"}, {"name": "Progress Review"}]
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name(items, "progress", item_type="status")
        assert "Ambiguous" in str(exc_info.value)
        assert "In Progress" in str(exc_info.value)
        assert "Progress Review" in str(exc_info.value)

    def test_custom_name_getter(self):
        """Test with custom name getter function."""
        items = [{"title": "First"}, {"title": "Second"}]
        result = fuzzy_find_by_name(
            items,
            "first",
            name_getter=lambda x: x.get("title", ""),
            item_type="item",
        )
        assert result["title"] == "First"

    def test_item_type_in_error_message(self):
        """Test item_type appears in error messages."""
        items = [{"name": "Done"}]
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name(items, "missing", item_type="workflow")
        assert "Workflow" in str(exc_info.value)


class TestFuzzyFindByNameOptional:
    """Tests for fuzzy_find_by_name_optional function."""

    def test_exact_match_returns_item(self):
        """Test exact match returns the item."""
        items = [{"name": "Done"}, {"name": "In Progress"}]
        result = fuzzy_find_by_name_optional(items, "done")
        assert result["name"] == "Done"

    def test_partial_match_returns_item(self):
        """Test partial match returns the item when fuzzy enabled."""
        items = [{"name": "In Progress"}, {"name": "Done"}]
        result = fuzzy_find_by_name_optional(items, "progress")
        assert result["name"] == "In Progress"

    def test_no_match_returns_none(self):
        """Test no match returns None instead of raising."""
        items = [{"name": "Done"}, {"name": "In Progress"}]
        result = fuzzy_find_by_name_optional(items, "nonexistent")
        assert result is None

    def test_empty_items_returns_none(self):
        """Test empty items returns None."""
        result = fuzzy_find_by_name_optional([], "test")
        assert result is None

    def test_no_fuzzy_match_returns_none(self):
        """Test no fuzzy match returns None when fuzzy disabled."""
        items = [{"name": "In Progress"}]
        result = fuzzy_find_by_name_optional(items, "progress", fuzzy=False)
        assert result is None

    def test_multiple_exact_matches_raises(self):
        """Test multiple exact matches still raises ValidationError."""
        items = [{"name": "Done"}, {"name": "done"}]
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name_optional(items, "done")
        assert "Multiple exact matches" in str(exc_info.value)

    def test_ambiguous_partial_match_raises(self):
        """Test ambiguous partial match raises ValidationError."""
        items = [{"name": "Progress A"}, {"name": "Progress B"}]
        with pytest.raises(ValidationError) as exc_info:
            fuzzy_find_by_name_optional(items, "progress")
        assert "Ambiguous" in str(exc_info.value)
        assert "more specific" in str(exc_info.value)

    def test_custom_name_getter(self):
        """Test with custom name getter function."""
        items = [{"label": "Alpha"}, {"label": "Beta"}]
        result = fuzzy_find_by_name_optional(
            items,
            "alpha",
            name_getter=lambda x: x.get("label", ""),
        )
        assert result["label"] == "Alpha"

    def test_custom_name_getter_no_match(self):
        """Test custom name getter with no match returns None."""
        items = [{"label": "Alpha"}]
        result = fuzzy_find_by_name_optional(
            items,
            "gamma",
            name_getter=lambda x: x.get("label", ""),
        )
        assert result is None
