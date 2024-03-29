import os


def is_debug_enabled():
    """Return whether debug mode is enabled.

    This is used by developers to enable more logging - mostly during
    publishing where the publisher UI handles all logs no matter what.
    This toggle, when disabled, allows disabling very verbose logs which
    tend to be 'slow' if always running for regular artist publishing.

    Returns:
        bool: Whether debug mode is considered enabled.

    """
    return os.getenv("AYON_USE_DEV") == "1" or os.getenv("AYON_DEBUG") == "1"
