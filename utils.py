import os
import base64

is_local = True


def safe_path(path: str) -> str:
    """Safely handle file paths to prevent directory traversal.

    Args:
        path: Input file path
        local: If True, prepend ./data, otherwise use absolute /data path

    Returns:
        Safe file path string
    """
    # Remove any parent directory references
    clean_path = os.path.normpath(path).lstrip("/")

    # Only allow paths under /data
    if clean_path.startswith("data/"):
        clean_path = clean_path[5:]
    elif clean_path.startswith("data"):
        clean_path = clean_path[4:]

    if is_local:
        return os.path.join("./data", clean_path)
    return os.path.join("/data", clean_path)


def safe_read(path: str, *args, **kwargs):
    """Safely read a file from the data directory."""
    safe_file_path = safe_path(path)
    with open(safe_file_path, *args, **kwargs) as f:
        return f.read()


def safe_write(path: str, data, *args, **kwargs):
    """Safely write a file to the data directory."""
    safe_file_path = safe_path(path)
    os.makedirs(os.path.dirname(safe_file_path), exist_ok=True)
    with open(safe_file_path, "w", *args, **kwargs) as f:
        return f.write(data)


def png_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode("utf-8")
    return base64_string
