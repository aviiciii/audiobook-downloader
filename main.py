import os
import re
import requests
import subprocess
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from mutagen.id3 import (
    ID3,
    APIC,
    TALB,
    TPE1,
    TPE2,
    TCON,
    TDRC,
    TRCK,
    TIT2,
    ID3NoHeaderError,
)
from rich.table import Table
from rich.console import Console

console = Console()


# --- HELPER FUNCTION TO SCRAPE DETAILS ---
def get_book_details(soup):
    """Extracts book details from the page's soup."""
    details = {}

    # Find all detail items
    detail_items = soup.select("div.detail-item")
    for item in detail_items:
        label_element = item.find("span", class_="font-medium")
        if not label_element:
            continue

        label = label_element.text.strip().lower()
        value_element = item.find("span", class_="detail-value-link") or item.find(
            "span", class_="detail-value"
        )

        if value_element:
            value = " ".join(value_element.text.split())
            if "authors:" in label:
                details["author"] = value
            elif "narrators:" in label:
                details["narrator"] = value
            elif "release date:" in label:
                match = re.search(r"\d{2,4}$", value)
                if match:
                    year = match.group()
                    details["year"] = f"20{year}" if len(year) == 2 else year

    return details


# --- MAIN DOWNLOAD FUNCTION ---
def download_and_tag_audiobook(book_url):
    """
    Downloads all chapters of a Tokybook audiobook using the new API structure.
    """
    BASE_URL = "https://tokybook.com"
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    # --- 1. Fetch the main audiobook page ---
    try:
        console.print(f"\n[cyan]Fetching book information from:[/cyan] {book_url}")
        response = session.get(book_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        book_title = soup.find("h1", class_=re.compile(r"text-4xl")).text.strip()
        sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)

        scraped_details = get_book_details(soup)
        author_name = scraped_details.get("author")
        narrator_name = scraped_details.get("narrator")
        year_text = scraped_details.get("year")

        cover_img_tag = soup.select_one("div.md\\:col-span-1 img")
        cover_url = urljoin(BASE_URL, cover_img_tag["src"]) if cover_img_tag else None

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error fetching audiobook page:[/bold red] {e}")
        return
    except AttributeError as e:
        console.print(
            f"[bold red]Error:[/bold red] Could not find required elements. "
            f"The website structure may have changed. {e}"
        )
        return

    # --- NEW: Display scraped info and ask for user override ---
    details_table = Table(title="Scraped Book Details", show_lines=True)
    details_table.add_column("Field", style="bold cyan", width=15)
    details_table.add_column("Value", style="white", width=45)

    details_table.add_row("Title", sanitized_title)
    details_table.add_row("Author", author_name or "Not Found")
    details_table.add_row("Narrator", narrator_name or "Not Found")
    details_table.add_row("Year", year_text or "Not Found")
    details_table.add_row("Cover Art URL", cover_url or "Not Found")

    console.print(details_table)

    choice = console.input("[yellow]Do you want to change any of these details? (y/n): [/yellow]").lower().strip()
    if choice == "y" or choice == "yes":
        console.print("\n[cyan]Enter new details. Press Enter to keep the current value.[/cyan]")

        new_author = console.input(f"Author [{author_name}]: ").strip()
        if new_author:
            author_name = new_author

        new_narrator = console.input(f"Narrator [{narrator_name}]: ").strip()
        if new_narrator:
            narrator_name = new_narrator

        new_year = console.input(f"Year [{year_text}]: ").strip()
        if new_year:
            year_text = new_year

        new_cover_url = console.input(f"Cover URL [{cover_url}]: ").strip()
        if new_cover_url:
            cover_url = new_cover_url

    # --- 2. Find the Play Button ---
    try:
        play_button = soup.find("button", {"data-action": "play-now"})
        book_id = play_button["data-book-id"]
        token = play_button["data-token"]
    except (TypeError, KeyError):
        console.print("[bold red]Error:[/bold red] Could not find play button, book ID, or token.")
        return

    # --- 3. Call the /player API ---
    try:
        player_url = f"{BASE_URL}/player"
        headers = {"Referer": book_url, "X-Audiobook-Id": book_id, "X-Playback-Token": token}

        console.print("\n[cyan]Fetching playlist from API...[/cyan]")
        player_response = session.get(player_url, headers=headers)
        player_response.raise_for_status()
        player_soup = BeautifulSoup(player_response.text, "html.parser")

        chapter_links = []
        for item in player_soup.find_all("li", class_="playlist-item-hls"):
            src = item.get("data-track-src")
            if src:
                chapter_links.append(urljoin(BASE_URL, src))
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error fetching player data:[/bold red] {e}")
        return

    if not chapter_links:
        console.print("[bold red]Error:[/bold red] No chapter links found in the player API response.")
        return

    # --- 4. Create directories ---
    book_dir = os.path.join(os.getcwd(), "Audiobooks", sanitized_title)
    os.makedirs(book_dir, exist_ok=True)

    # --- 5. Download cover art ---
    artwork_data, mime_type = None, None
    try:
        if cover_url:
            artwork_response = session.get(cover_url)
            artwork_response.raise_for_status()
            artwork_data = artwork_response.content
            mime_type = (
                "image/jpeg" if cover_url.lower().endswith((".jpg", ".jpeg")) else "image/png"
            )
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]Warning:[/yellow] Could not download cover art. {e}")

    # --- 6. Print Summary ---
    summary_table = Table(title="Final Audiobook Summary", show_lines=True)
    summary_table.add_column("Field", style="bold cyan", width=15)
    summary_table.add_column("Value", style="white", width=45)

    summary_table.add_row("Title", sanitized_title)
    summary_table.add_row("Author", author_name or "N/A")
    summary_table.add_row("Narrator", narrator_name or "N/A")
    summary_table.add_row("Year", year_text or "N/A")
    summary_table.add_row("Cover Art", "Downloaded" if artwork_data else "Not Found/Skipped")
    summary_table.add_row("Save Path", book_dir)

    console.print(summary_table)

    # --- 7. Download each chapter ---
    total_chapters = len(chapter_links)
    console.print(f"\n[green]Found {total_chapters} chapters. Starting download with yt-dlp...[/green]")

    for i, link in enumerate(chapter_links, start=1):
        chapter_title = f"Chapter {i:02}"
        file_name = os.path.join(book_dir, f"{chapter_title}.mp3")
        output_template = os.path.join(book_dir, f"{chapter_title}.%(ext)s")
        console.print(f"\n[cyan]--- Downloading {chapter_title} ({i}/{total_chapters}) ---[/cyan]")

        command = [
            "yt-dlp", "--quiet", "--no-warnings", "--progress",
            "-x",  "--audio-format", "mp3",  "--audio-quality", "0",  
            "--add-header", f"Referer: {book_url}",
            "--add-header", f"x-playback-token: {token}",
            "--retries", "5",
            "-o", output_template,
            link,
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)

            try:
                audio = ID3(file_name)
            except ID3NoHeaderError:
                audio = ID3()

            audio.add(TALB(encoding=3, text=sanitized_title))
            audio.add(TCON(encoding=3, text="Audiobook"))
            audio.add(TRCK(encoding=3, text=f"{i}/{total_chapters}"))
            audio.add(TIT2(encoding=3, text=chapter_title))
            if author_name:
                audio.add(TPE1(encoding=3, text=author_name))
            if narrator_name:
                audio.add(TPE2(encoding=3, text=narrator_name))
            if year_text:
                audio.add(TDRC(encoding=3, text=year_text))
            if artwork_data and mime_type:
                audio.add(APIC(encoding=3, mime=mime_type, type=3, desc="Cover", data=artwork_data))

            audio.save(file_name)
            console.print(f"[green]Downloaded and tagged:[/green] {chapter_title}")

        except FileNotFoundError:
            console.print("\n[bold red]FATAL ERROR:[/bold red] 'yt-dlp' not found. Install yt-dlp and ffmpeg.")
            return
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error:[/bold red] yt-dlp failed for {chapter_title}. {e.stderr}")
        except Exception as e:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")

    console.print("\n[bold green]All chapters downloaded and tagged successfully![/bold green]")


if __name__ == "__main__":
    console.print("[bold cyan]--- Tokybook Downloader (Updated for HLS Streams) ---[/bold cyan]")
    console.print("[yellow]Requires 'yt-dlp' and 'ffmpeg' to be installed.[/yellow]")

    while True:
        input_book_url = console.input("\n[cyan]Enter the Tokybook URL:[/cyan] ").strip()
        if "tokybook.com/post/" in input_book_url:
            download_and_tag_audiobook(book_url=input_book_url)
            break
        console.print("[red]Error:[/red] Please enter a valid URL (e.g., https://tokybook.com/post/...)")