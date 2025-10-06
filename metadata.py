# metadata.py
import requests
from rich.table import Table
from rich.console import Console

console = Console()


def _review_and_override_metadata(book_data: dict) -> dict:
    """Displays scraped metadata and allows the user to override it."""
    details_table = Table(title="Scraped Book Details", show_lines=True)
    details_table.add_column("Field", style="bold cyan", width=15)
    details_table.add_column("Value", style="white", min_width=45)

    fields = ["title", "author", "narrator", "year", "cover_url"]
    for field in fields:
        details_table.add_row(field.replace("_", " ").title(), book_data.get(field, "N/A"))

    console.print(details_table)

    if console.input(
        "[yellow]Do you want to change any details? (y/n): [/yellow]"
    ).lower().strip() in ("y", "yes"):
        console.print(
            "\n[cyan]Enter new details or press Enter to keep the current value.[/cyan]"
        )
        for field in fields:
            current_value = book_data.get(field, "")
            new_value = console.input(f"{field.title()} [{current_value}]: ").strip()
            book_data[field] = new_value or current_value

    return book_data


def _download_cover_art(book_data: dict) -> dict:
    """Downloads the cover art from the provided URL."""
    cover_url = book_data.get("cover_url")
    if not cover_url:
        return book_data

    console.print("\n[cyan]Downloading cover art...[/cyan]")
    try:
        response = requests.get(cover_url, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")

        if not content_type.startswith("image/"):
            raise ValueError(f"URL did not point to an image. Content-Type: {content_type}")

        book_data["artwork_data"] = response.content
        book_data["mime_type"] = content_type

    except (requests.RequestException, ValueError) as e:
        console.print(f"[yellow]Warning: Could not download cover art. Error: {e}[/yellow]")
        book_data["artwork_data"] = None
        book_data["mime_type"] = None

    return book_data


def handle_metadata(book_data: dict) -> dict:
    """
    Main function to orchestrate metadata review and cover art download.

    Args:
        book_data: The initial dictionary of scraped data.

    Returns:
        The updated book data dictionary with user overrides and artwork.
    """
    updated_data = _review_and_override_metadata(book_data)
    final_data = _download_cover_art(updated_data)
    return final_data