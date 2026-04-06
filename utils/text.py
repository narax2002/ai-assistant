"""Text utilities shared across interfaces."""


def chunk_text(text: str, limit: int) -> list[str]:
    """Split *text* into chunks of at most *limit* characters.

    Splits prefer newline boundaries when possible.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            split_at = text.rfind("\n", start, end)
            if split_at > start:
                end = split_at
        chunks.append(text[start:end].strip())
        start = end

    return [chunk for chunk in chunks if chunk]
