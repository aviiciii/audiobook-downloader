import re


def sanitize_book_title(title, max_length=200):
    """
    Sanitizes a book title to be safe for use as a directory or filename
    on Windows, macOS, and Linux.

    Args:
        title (str): The original book title.
        max_length (int): Maximum length of the filename (default 200 to be safe).

    Returns:
        str: A safe, clean directory name.
    """
    if not title:
        return "Untitled_Book"

    title = title.replace(":", " -")

    title = title.replace("/", "-").replace("\\", "-")

    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)

    title = title.strip(" .")

    # Check for Reserved Windows Filenames
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    if title.upper() in reserved_names:
        title = f"_{title}_"

    title = re.sub(r"\s+", " ", title)

    if len(title) > max_length:
        title = title[:max_length].strip()

    if not title:
        return "Unknown_Title"

    return title


def parse_chapter_ranges(selection_str, max_chapters):
    """
    Parses a string of chapter ranges (e.g., "1-5, 8, 10-12")
    and returns a sorted list of 0-based indices.
    """
    indices = set()
    
    if selection_str == "":
        return []
        
    parts = selection_str.split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                # Clamp values to valid range
                start = max(1, start)
                end = min(max_chapters, end)
                if start <= end:
                    for i in range(start, end + 1):
                        indices.add(i - 1)  # Convert to 0-based index
            except ValueError:
                continue
        else:
            try:
                num = int(part)
                if 1 <= num <= max_chapters:
                    indices.add(num - 1)  # Convert to 0-based index
            except ValueError:
                continue

    return sorted(list(indices))


# --- Example Usage ---
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    titles = [
        "Dune: The Machine Crusade",
        "How to use < > * ? | in Python",
        "COM1",
        "   A book    with    extra     spaces.   ",
        "AC/DC: Highway to Hell",
    ]

    console = Console()
    table = Table(title="Sanitizer Test Results")
    table.add_column("Original", style="cyan")
    table.add_column("Sanitized", style="green")

    for t in titles:
        table.add_row(t, sanitize_book_title(t))

    console.print(table)
    
    selection = "1-3, 5, 7-9"
    max_chapters = 10
    indices = parse_chapter_ranges(selection, max_chapters)
    console.print(f"Selected chapter indices for '{selection}': {indices}")

