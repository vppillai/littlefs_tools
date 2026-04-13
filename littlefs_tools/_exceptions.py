"""Exception hierarchy for littlefs_tools."""


class LittleFSToolsError(Exception):
    """Base exception for littlefs_tools errors."""


class ImageTooSmallError(LittleFSToolsError):
    """Raised when the source contents exceed the image capacity."""


class ValidationError(LittleFSToolsError):
    """Raised when an argument fails validation."""


class DestinationNotEmptyError(LittleFSToolsError):
    """Raised when the extraction destination is not empty and --force is not set."""


class AutoDetectError(LittleFSToolsError):
    """Raised when auto-detection of image parameters fails."""


class ImageCorruptError(LittleFSToolsError):
    """Raised when the image fails integrity checks."""


class PathNotFoundError(LittleFSToolsError):
    """Raised when a path does not exist inside the image."""
