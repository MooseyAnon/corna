"""Shared enum values across application."""
import enum


class ContentType(enum.Enum):
    """Types of content we currently accept."""
    TEXT = "text"
    PHOTO = "picture"

    def __eq__(self, other):
        return self.value == other


class SessionNames(enum.Enum):
    SESSION = "corna-sesh"


class ThemeReviewState(enum.Enum):
    UNKNOWN = "unknown"
    MERGED = "merged"
