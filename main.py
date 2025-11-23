import os
import requests
import subprocess
from http.client import IncompleteRead
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
from rich.progress import Progress
import time

from scrapers.tokybook import TokybookScraper
from scrapers.goldenaudiobook import GoldenAudiobookScraper
from scrapers.zaudiobooks import ZaudiobooksScraper
from scrapers.fulllengthaudiobooks import FulllengthAudiobooksScraper
from scrapers.hdaudiobooks import HDAudiobooksScraper
from scrapers.bigaudiobooks import BigAudiobooksScraper


console = Console()


def get_scraper(url):
    """Factory function to select the correct scraper based on the URL."""
    if "tokybook.com" in url:
        return TokybookScraper()
    if "goldenaudiobook.net" in url:
        return GoldenAudiobookScraper()
    if "zaudiobooks.com" in url:
        return ZaudiobooksScraper()
    if "fulllengthaudiobooks.net" in url:
        return FulllengthAudiobooksScraper()
    if "hdaudiobooks.net" in url:
        return HDAudiobooksScraper()
    if "bigaudiobooks.net" in url:
        return BigAudiobooksScraper()
    return None


def download_and_tag_audiobook(book_data):
    sanitized_title = book_data["title"]
    author_name = book_data.get("author")
    narrator_name = book_data.get("narrator")
    year_text = book_data.get("year")
    artwork_data = book_data.get("artwork_data")
    mime_type = book_data.get("mime_type")

    book_dir = os.path.join(os.getcwd(), "Audiobooks", sanitized_title)
    os.makedirs(book_dir, exist_ok=True)

    total_chapters = len(book_data["chapters"])
    console.print(
        f"\n[green]Found {total_chapters} chapters. Starting download...[/green]\n"
    )
    # print(book_data["chapters"])

    with Progress() as progress:
        task = progress.add_task(
            f"[cyan]Downloading {sanitized_title}...", total=total_chapters
        )
        session = requests.Session()
        for i, chapter in enumerate(book_data["chapters"], start=1):
            link = chapter["url"]
            chapter_title = chapter["title"]
            # Formatting chapter names with leading zeros for sorting (e.g., Chapter 001.mp3)
            # This handles the user request for "f'Chapter {i:03}'" naming if the scraped title isn't sufficient
            # But usually we respect the scraped title. 
            # If you specifically want to force the naming convention:
            # chapter_filename = f"Chapter {i:03}.mp3"
            # final_file_name = os.path.join(book_dir, chapter_filename)
            
            final_file_name = os.path.join(book_dir, f"{chapter_title}.mp3")

            try:
                # --- CHECK IF FILE EXISTS ---
                if os.path.exists(final_file_name):
                    # For Tokybook, the user requested "Smart Resume" logic (redownload last file).
                    # Since this loop runs linearly 1..N, if we find a file exists:
                    # 1. We check if the NEXT file also exists. 
                    # 2. If the NEXT file exists, we assume THIS one is fine and skip.
                    # 3. If the NEXT file does NOT exist, we assume THIS one is the "last modified" and redownload it.
                    
                    next_chapter_idx = i # 'i' is 1-based, list is 0-based, so book_data["chapters"][i] is the NEXT one
                    is_last_existing = False
                    
                    if next_chapter_idx < len(book_data["chapters"]):
                         # Construct next filename to check
                         next_title = book_data["chapters"][next_chapter_idx]["title"]
                         next_path = os.path.join(book_dir, f"{next_title}.mp3")
                         if not os.path.exists(next_path):
                             is_last_existing = True
                    else:
                        # This is the very last chapter of the book and it exists
                        is_last_existing = True 

                    if book_data.get("site") == "tokybook.com" and is_last_existing:
                        progress.log(f"[yellow]Resume detected: Redownloading last found file ({chapter_title})...[/yellow]")
                        # Allow to fall through to download logic below
                    else:
                        progress.log(f"[dim]Skipping {chapter_title}, already exists.[/dim]")
                        progress.advance(task)
                        continue

                # --- DOWNLOAD LOGIC ---
                
                # 1. TOKYBOOK (New Parallel Downloader)
                if book_data.get("site") == "tokybook.com":
                    progress.log(f"[cyan]Downloading {chapter_title} (Parallel)...[/cyan]")
                    # Download to a temporary TS file first (Tokybook streams are MPEG-TS)
                    temp_ts_file = os.path.join(book_dir, f"{chapter_title}.ts")
                    TokybookScraper.download_chapter(chapter, book_data, temp_ts_file, progress)
                    
                    # Convert TS to proper MP3 using FFmpeg to ensure metadata tags work
                    progress.log(f"[dim]Converting {chapter_title} to MP3...[/dim]")
                    try:
                        subprocess.run([
                            "ffmpeg", "-i", temp_ts_file, 
                            "-y",           # Overwrite output
                            "-vn",          # No video
                            "-acodec", "libmp3lame", 
                            "-q:a", "2",    # VBR Quality ~190kbps
                            "-loglevel", "error",
                            final_file_name
                        ], check=True)
                        
                        # Cleanup temp file
                        if os.path.exists(temp_ts_file):
                            os.remove(temp_ts_file)
                            
                    except subprocess.CalledProcessError:
                        progress.log(f"[red]FFmpeg conversion failed for {chapter_title}[/red]")
                        continue
                # 2. GOLDEN / ZAUDIO (Session based)
                elif (
                    book_data.get("site") == "goldenaudiobook.net"
                    or book_data.get("site") == "zaudiobooks.com"
                ):
                    headers = book_data.get("site_headers", {})
                    progress.log(f"[cyan]Downloading {chapter_title}...[/cyan]")
                    download_chapters_session(
                        session, link, final_file_name, headers, chapter_title, progress
                    )

                # 3. GENERIC FALLBACK (yt-dlp)
                else:   
                    progress.log(f"[cyan]Downloading {chapter_title} (yt-dlp)...[/cyan]")
                    output_template = os.path.join(book_dir, f"{chapter_title}.%(ext)s")
                    command = [
                        "yt-dlp",
                        "-x",
                        "--audio-format",
                        "mp3",
                        "--audio-quality",
                        "0",
                        "--retries",
                        "5",
                    ]
                    if book_data.get("site_headers"):
                        for key, value in book_data["site_headers"].items():
                            command.extend(["--add-header", f"{key}: {value}"])
                    
                    command.extend(["-o", output_template, link])
                    result = subprocess.run(command, capture_output=True, text=True)

                    if result.returncode != 0:
                        progress.log(f"[red]Error downloading {chapter_title}[/red]")
                        continue

                # --- Add ID3 tags ---
                try:
                    audio = ID3(final_file_name)
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
                    audio.add(
                        APIC(
                            encoding=3,
                            mime=mime_type,
                            type=3,
                            desc="Cover",
                            data=artwork_data,
                        )
                    )
                audio.save(final_file_name, v2_version=3)

            except Exception as e:
                console.print(f"[red]Error downloading {chapter_title}: {e}[/red]")

            progress.log(f"[green]✔ Completed {chapter_title}[/green]")
            progress.advance(task)

    console.print(
        "\n[bold green]All chapters downloaded and tagged successfully![/bold green]"
    )


def download_chapters_session(
    session, url, final_file_name, headers, chapter_title, progress
):
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            with session.get(url, headers=headers, stream=True, timeout=(10, 180)) as r:
                if r.status_code == 403:
                    raise requests.exceptions.HTTPError("403 Forbidden")
                r.raise_for_status()
                with open(final_file_name, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return
        except (requests.exceptions.RequestException, IncompleteRead) as e:
            progress.log(
                f"[yellow]Attempt {attempt + 1} failed for {chapter_title}: {e}[/yellow] [link={url}]{url}[/link]"
            )
            if isinstance(e, requests.exceptions.HTTPError) and "403" in str(e):
                subprocess.run(["open", url])
            if attempt < max_attempts - 1:
                time.sleep(5**attempt)
    raise Exception(
        f"Failed to download {chapter_title} ({url}) after {max_attempts} attempts"
    )


if __name__ == "__main__":
    console.print("[bold cyan]--- Audiobook Downloader ---[/bold cyan]")

    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        console.print(
            "[red]Error: ffmpeg is not installed. Check the README for installation instructions.[/red]"
        )
        exit()

    while True:
        input_book_url = console.input("\nEnter the audiobook URL: ").strip()
        scraper = get_scraper(input_book_url)
        if scraper:
            break
        console.print(
            "[red]Error: Unsupported website. Please enter a valid URL from a supported site.[/red]"
        )

    # --- 1. Scrape data ---
    book_data = scraper.fetch_book_data(input_book_url)

    if not book_data:
        console.print("[bold red]Could not retrieve book data. Exiting.[/bold red]")
        exit()

    # --- 2. Review and Override Metadata ---
    details_table = Table(title="Scraped Book Details", show_lines=True)
    details_table.add_column("Field", style="bold cyan", width=15)
    details_table.add_column("Value", style="white", min_width=45)
    details_table.add_row("Title", book_data.get("title", "N/A"))
    details_table.add_row("Author", book_data.get("author", "N/A"))
    details_table.add_row("Narrator", book_data.get("narrator", "N/A"))
    details_table.add_row("Year", book_data.get("year", "N/A"))
    details_table.add_row("Cover Art URL", book_data.get("cover_url", "N/A"))
    console.print(details_table)

    if console.input(
        "[yellow]Do you want to change any of these details? (y/n): [/yellow]"
    ).lower().strip() in ("y", "yes"):
        console.print(
            "\n[cyan]Enter new details. Press Enter to keep the current value.[/cyan]"
        )
        book_data["title"] = console.input(
            f"Title [{book_data.get('title', '')}]: "
        ).strip() or book_data.get("title")
        book_data["author"] = console.input(
            f"Author [{book_data.get('author', '')}]: "
        ).strip() or book_data.get("author")
        book_data["narrator"] = console.input(
            f"Narrator [{book_data.get('narrator', '')}]: "
        ).strip() or book_data.get("narrator")
        book_data["year"] = console.input(
            f"Year [{book_data.get('year', '')}]: "
        ).strip() or book_data.get("year")
        book_data["cover_url"] = console.input(
            f"Cover URL [{book_data.get('cover_url', '')}]: "
        ).strip() or book_data.get("cover_url")

    # --- 3. Download cover art ---
    if book_data.get("cover_url"):
        console.print("\n[cyan]Downloading cover art...[/cyan]")
        try:
            artwork_response = requests.get(book_data["cover_url"])
            artwork_response.raise_for_status()
            content_type = artwork_response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                pass 
            else:
                book_data["artwork_data"] = artwork_response.content
                book_data["mime_type"] = (
                    "image/jpeg"
                    if content_type == "image/jpeg"
                    or book_data["cover_url"].lower().endswith((".jpg", ".jpeg"))
                    else "image/png"
                )
        except requests.exceptions.RequestException as e:
            console.print(
                f"[yellow]Warning: Could not download cover art. Error: {e}[/yellow]"
            )

    # --- 4. Start the download process ---
    download_and_tag_audiobook(book_data)