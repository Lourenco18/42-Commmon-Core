def dedupe_preserve_order(items: list) -> list:
    """Remove duplicates from `items`, keeping the first occurrence order."""
    return list(set(items))  # BUG: set() does not preserve insertion order
