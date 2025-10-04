import os
import tempfile
from pathlib import Path
from rich.console import Console

import main as ad

console = Console()

# ✅ Grouped test URLs by website
TEST_URLS = {
    # "goldenaudiobook": [
    #     "https://goldenaudiobook.net/andy-weir-project-hail-mary-audiobook/",
    #     "https://goldenaudiobook.net/pierce-brown-audiobook-red-rising/"
    # ],
    # "tokybook": [
    #     "https://tokybook.com/post/project-hail-mary-746adb",
    #     "https://tokybook.com/post/harry-potter-and-the-sorcerers-stone-book-1-5d0dc7"
    # ],
    # "zaudiobooks": [
    #     "https://zaudiobooks.com/daisy-jones-the-six/",
    #     "https://zaudiobooks.com/red-rising/"
    # ],
    # "fulllengthaudiobooks": [
    #     "https://fulllengthaudiobooks.net/george-r-r-martin-world-of-ice-fire-audiobook/",
    #     "https://fulllengthaudiobooks.net/john-green-looking-for-alaska-audiobook-2/"
    # ],
    # "hdaudiobooks": [
    #     "https://hdaudiobooks.net/what-its-us/",
    #     "https://hdaudiobooks.net/audiobook-red-rising-pierce-brown/"
    # ],
    "bigaudiobooks": [
        "https://bigaudiobooks.net/gillian-flynn-dark-places-audiobook/",
        "https://bigaudiobooks.net/1984/"
    ],
    
}

def run_real_test(book_url: str) -> bool:
    console.print(f"\n[bold cyan]Testing: {book_url}[/bold cyan]")

    scraper = ad.get_scraper(book_url)
    if not scraper:
        console.print(f"[red]No scraper found for: {book_url}[/red]")
        return False

    book_data = scraper.fetch_book_data(book_url)
    if not book_data or not book_data.get("chapters"):
        console.print(f"[red]Failed to scrape chapters from {book_url}[/red]")
        return False

    # Only keep first 2 chapters
    book_data["chapters"] = book_data["chapters"][:2]

    # Test directory inside Audiobooks/Test/
    base_dir = Path("Test")

    os.makedirs(base_dir, exist_ok=True)

    console.print(f"[green]Downloading 2 chapters to: {base_dir}[/green]")

    # Temporarily change working directory so main.py puts it inside Audiobooks/Test/
    old_cwd = os.getcwd()
    os.chdir(base_dir)
    try:
        ad.download_and_tag_audiobook(book_data)
    finally:
        os.chdir(old_cwd)
    check_dir = base_dir / "Audiobooks" / book_data["title"]
    # Check if MP3s were created
    downloaded = list(check_dir.glob("*.mp3"))
    if len(downloaded) >= 2:
        console.print(f"[bold green]✓ Test Passed: {book_url}[/bold green]")
        return True
    else:
        console.print(f"[bold red]✗ Test Failed: No MP3s found[/bold red]")
        return False
    

if __name__ == "__main__":
    overall_passed = 0
    overall_total = 0

    for site, urls in TEST_URLS.items():
        console.print(f"\n[bold magenta]=== Testing {site.upper()} ===[/bold magenta]")

        passed = 0
        for url in urls:
            if run_real_test(url):
                passed += 1

        total = len(urls)
        overall_passed += passed
        overall_total += total

        console.print(
            f"[yellow]Summary for {site}: {passed}/{total} passed[/yellow]"
        )

    console.print(
        f"\n[bold cyan]OVERALL SUMMARY: {overall_passed}/{overall_total} passed[/bold cyan]"
    )