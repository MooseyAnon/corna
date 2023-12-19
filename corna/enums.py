"""Shared enum values across application."""
import enum


class EnumWrapper(enum.Enum):
    """Wrapper to add extra functionality to enums."""

    def __eq__(self, other):
        """Make equality syntax more ergonomic."""
        return self.value == other


class ContentType(EnumWrapper):
    """Types of content we currently accept."""
    TEXT = "text"
    PHOTO = "picture"


class SessionNames(EnumWrapper):
    """Session names."""
    SESSION = "corna-sesh"


class ThemeReviewState(enum.Enum):
    """States of theme PR."""
    UNKNOWN = "unknown"
    MERGED = "merged"

    def __eq__(self, other):
        return self.value == other
