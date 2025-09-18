KEEP_CHARACTERS = (" ", ".", "_")

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by replacing spaces with underscores and removing invalid characters."""
    return "".join(c for c in filename if c.isalnum() or c in KEEP_CHARACTERS).rstrip()

