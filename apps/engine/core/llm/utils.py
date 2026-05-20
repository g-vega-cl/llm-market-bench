"""Utility functions for LLM response handling."""


def ensure_list(obj):
    """Ensures that the input object is wrapped in a list if it is not already a list or tuple.

    This is particularly useful for handling LLM responses that may return either a single
    object or a list/tuple of objects (e.g., when multiple tool call blocks are involved).

    Args:
        obj: The object to ensure is a list.

    Returns:
        A list containing the object(s).
    """
    if obj is None:
        return []
    if isinstance(obj, (list, tuple)):
        return list(obj)
    return [obj]
