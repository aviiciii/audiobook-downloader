# main.py
import subprocess
from rich.console import Console

from scrapers import get_scraper
from metadata import handle_metadata
from downloader import download_and_tag_audiobook

console = Console()


def main():
    """Main function to orchestrate the audiobook download process."""
    console.print("[bold cyan]--- Audiobook Downloader ---[/bold cyan]")

    # Check for FFmpeg dependency
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            "[red]Error: ffmpeg is not installed or not in your PATH. "
            "Check the README for installation instructions.[/red]"
        )
        return

    # Get a valid URL and corresponding scraper
    while True:
        book_url = console.input("\nEnter the audiobook URL: ").strip()
        scraper = get_scraper(book_url)
        if scraper:
            break
        console.print(
            "[red]Error: Unsupported website. Please enter a valid URL.[/red]"
        )

    # 1. Scrape the initial book data
    book_data = scraper.fetch_book_data(book_url)
    if not book_data:
        console.print("[bold red]Could not retrieve book data. Exiting.[/bold red]")
        return

    # 2. Review, override, and download metadata (like cover art)
    updated_book_data = handle_metadata(book_data)
    if not updated_book_data:
        console.print("[yellow]Metadata handling cancelled. Exiting.[/yellow]")
        return

    # 3. Download all chapters and apply tags
    download_and_tag_audiobook(updated_book_data)


if __name__ == "__main__":
    main()