import argparse
import os
import platform
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
from utils import sanitize_book_title, parse_chapter_ranges


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


def download_and_tag_audiobook(book_data, output_dir=None):
    sanitized_title = book_data["title"]
    author_name = book_data.get("author")
    narrator_name = book_data.get("narrator")
    year_text = book_data.get("year")
    artwork_data = book_data.get("artwork_data")
    mime_type = book_data.get("mime_type")

    base = output_dir if output_dir else os.getcwd()
    book_dir = os.path.join(base, "Audiobooks", sanitized_title)
    os.makedirs(book_dir, exist_ok=True)

    total_chapters = len(book_data["chapters"])
    console.print(
        f"\n[green]Found {total_chapters} chapters. Starting download...[/green]\n"
    )

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

                    next_chapter_idx = i  # 'i' is 1-based, list is 0-based, so book_data["chapters"][i] is the NEXT one
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
                        progress.log(
                            f"[yellow]Resume detected: Redownloading last found file ({chapter_title})...[/yellow]"
                        )
                        # Allow to fall through to download logic below
                    else:
                        progress.log(
                            f"[dim]Skipping {chapter_title}, already exists.[/dim]"
                        )
                        progress.advance(task)
                        continue

                # --- DOWNLOAD LOGIC ---

                # 1. TOKYBOOK (New Parallel Downloader)
                if book_data.get("site") == "tokybook.com":
                    progress.log(
                        f"[cyan]Downloading {chapter_title} (Parallel)...[/cyan]"
                    )
                    # Download to a temporary TS file first (Tokybook streams are MPEG-TS)
                    temp_ts_file = os.path.join(book_dir, f"{chapter_title}.ts")
                    TokybookScraper.download_chapter(
                        chapter, book_data, temp_ts_file, progress
                    )

                    # Convert TS to proper MP3 using FFmpeg to ensure metadata tags work
                    progress.log(f"[dim]Converting {chapter_title} to MP3...[/dim]")
                    try:
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-i",
                                temp_ts_file,
                                "-y",  # Overwrite output
                                "-vn",  # No video
                                "-acodec",
                                "libmp3lame",
                                "-q:a",
                                "2",  # VBR Quality ~190kbps
                                "-loglevel",
                                "error",
                                final_file_name,
                            ],
                            check=True,
                        )

                        # Cleanup temp file
                        if os.path.exists(temp_ts_file):
                            os.remove(temp_ts_file)

                    except subprocess.CalledProcessError:
                        progress.log(
                            f"[red]FFmpeg conversion failed for {chapter_title}[/red]"
                        )
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
                    progress.log(
                        f"[cyan]Downloading {chapter_title} (yt-dlp)...[/cyan]"
                    )
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
                system = platform.system()
                if system == "Darwin":
                    subprocess.run(["open", url])
                elif system == "Windows":
                    subprocess.run(["start", url], shell=True)
                elif system == "Linux":
                    subprocess.run(["xdg-open", url])
            if attempt < max_attempts - 1:
                time.sleep(5**attempt)
    raise Exception(
        f"Failed to download {chapter_title} ({url}) after {max_attempts} attempts"
    )


def build_parser():
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="audiobook-downloader",
        description="Download and tag audiobooks from supported websites.",
        epilog=(
            "supported sites:\n"
            "  tokybook.com, goldenaudiobook.net, zaudiobooks.com,\n"
            "  fulllengthaudiobooks.net, hdaudiobooks.net, bigaudiobooks.net\n"
            "\n"
            "examples:\n"
            "  %(prog)s https://tokybook.com/post/project-hail-mary-94ed6d\n"
            '  %(prog)s https://tokybook.com/post/circe-c21c22 -c "1-5,8"\n'
            "  %(prog)s https://zaudiobooks.com/red-rising/ -o ~/my-audiobooks\n"
            '  %(prog)s URL --title "My Book" --author "Author Name"\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", nargs="?", default=None, help="audiobook URL to download")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="output directory (default: ./Audiobooks)",
    )
    parser.add_argument(
        "-c",
        "--chapters",
        default=None,
        help='chapter selection, e.g. "1-5,8,10" (default: all)',
    )
    parser.add_argument("--title", default=None, help="override book title")
    parser.add_argument("--author", default=None, help="override author name")
    parser.add_argument("--narrator", default=None, help="override narrator name")
    parser.add_argument("--year", default=None, help="override publication year")
    parser.add_argument("--cover-url", default=None, help="override cover art URL")
    return parser


def main(args=None):
    """Main entry point for the audiobook downloader."""
    parser = build_parser()
    parsed = parser.parse_args(args)

    console.print("[bold cyan]--- Audiobook Downloader ---[/bold cyan]")

    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        console.print(
            "[red]Error: ffmpeg is not installed. Check the README for installation instructions.[/red]"
        )
        exit(1)

    # --- Get URL (from CLI arg or interactive prompt) ---
    input_book_url = parsed.url
    if input_book_url:
        scraper = get_scraper(input_book_url)
        if not scraper:
            console.print(
                "[red]Error: Unsupported website. Please enter a valid URL from a supported site.[/red]"
            )
            exit(1)
    else:
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
        exit(1)

    book_data["title"] = sanitize_book_title(book_data.get("title", "Unknown_Book"))

    # --- 2. Apply CLI overrides or interactive review ---
    cli_overrides = {
        "title": parsed.title,
        "author": parsed.author,
        "narrator": parsed.narrator,
        "year": parsed.year,
        "cover_url": parsed.cover_url,
    }
    has_overrides = any(v is not None for v in cli_overrides.values())

    if has_overrides:
        if cli_overrides["title"]:
            book_data["title"] = sanitize_book_title(cli_overrides["title"])
        if cli_overrides["author"]:
            book_data["author"] = cli_overrides["author"]
        if cli_overrides["narrator"]:
            book_data["narrator"] = cli_overrides["narrator"]
        if cli_overrides["year"]:
            book_data["year"] = cli_overrides["year"]
        if cli_overrides["cover_url"]:
            book_data["cover_url"] = cli_overrides["cover_url"]

    details_table = Table(title="Scraped Book Details", show_lines=True)
    details_table.add_column("Field", style="bold cyan", width=15)
    details_table.add_column("Value", style="white", min_width=45)
    details_table.add_row("Title", book_data.get("title", "N/A"))
    details_table.add_row("Author", book_data.get("author", "N/A"))
    details_table.add_row("Narrator", book_data.get("narrator", "N/A"))
    details_table.add_row("Year", book_data.get("year", "N/A"))
    details_table.add_row("Cover Art URL", book_data.get("cover_url", "N/A"))
    console.print(details_table)

    if not has_overrides:
        if console.input(
            "[yellow]Do you want to change any of these details? (y/n): [/yellow]"
        ).lower().strip() in ("y", "yes", "yep", "1"):
            console.print(
                "\n[cyan]Enter new details. Press Enter to keep the current value.[/cyan]"
            )
            book_data["title"] = sanitize_book_title(
                console.input(f"Title [{book_data.get('title', '')}]: ").strip()
                or book_data.get("title")
            )
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

    # --- 3. Chapter Selection ---
    total_chapters = len(book_data["chapters"])
    book_data["total_chapters_count"] = total_chapters

    final_chapter_list = []

    if parsed.chapters:
        # CLI chapter selection
        selected_indices = parse_chapter_ranges(parsed.chapters, total_chapters)
        if not selected_indices:
            console.print("[red]No valid chapters selected. Exiting.[/red]")
            exit(1)

        console.print(
            f"\n[green]Selected {len(selected_indices)} of {total_chapters} chapters.[/green]"
        )
        for idx in selected_indices:
            chapter = book_data["chapters"][idx]
            chapter["track_num"] = idx + 1
            final_chapter_list.append(chapter)
    elif parsed.url:
        # Non-interactive mode with URL arg: download all by default
        console.print(f"\n[green]Found {total_chapters} chapters.[/green]")
        for i, chapter in enumerate(book_data["chapters"]):
            chapter["track_num"] = i + 1
            final_chapter_list.append(chapter)
    else:
        # Interactive chapter selection
        console.print(f"\n[green]Found {total_chapters} chapters.[/green]")
        choice = console.input(
            "[yellow]Press [bold]Enter[/bold] to download ALL, or type [bold]'s'[/bold] to select specific chapters: [/yellow]"
        )

        if choice.lower().strip() in ("s", "y", "select", "yes", "yep", "1"):
            console.print(
                f"\n[bold]Chapters available: 1 to {total_chapters}[/bold]"
            )
            console.print(
                "You can specify individual chapters or ranges (e.g., '1-5, 8, 10')."
            )
            console.print(
                "Downloaded chapters will be skipped. To redownload any chapter delete it in the downloads folder."
            )
            selection = console.input(
                "\n[yellow]Enter chapter numbers/ranges to download: [/yellow]"
            ).lower().strip()
            selected_indices = parse_chapter_ranges(selection, total_chapters)

            if not selected_indices:
                console.print("[red]No valid chapters selected. Exiting.[/red]")
                exit(1)

            selected_table = Table(
                title=f"Selected {len(selected_indices)} Chapters",
                show_header=True,
                header_style="bold magenta",
            )
            selected_table.add_column("#", style="dim", width=4)
            selected_table.add_column("Chapter Title")

            for idx in selected_indices:
                if 0 <= idx < len(book_data["chapters"]):
                    title = book_data["chapters"][idx].get("title", "Unknown")
                    selected_table.add_row(f"{idx + 1:02}", title)

            console.print(selected_table)

            for idx in selected_indices:
                chapter = book_data["chapters"][idx]
                chapter["track_num"] = idx + 1
                final_chapter_list.append(chapter)
        else:
            for i, chapter in enumerate(book_data["chapters"]):
                chapter["track_num"] = i + 1
                final_chapter_list.append(chapter)

    book_data["chapters"] = final_chapter_list

    # --- 4. Set output directory ---
    if parsed.output:
        output_dir = parsed.output
    else:
        output_dir = os.getcwd()

    # --- 5. Download cover art ---
    if book_data.get("cover_url"):
        console.print("\n[cyan]Downloading cover art...[/cyan]")
        try:
            artwork_response = requests.get(book_data["cover_url"])
            artwork_response.raise_for_status()
            content_type = artwork_response.headers.get("Content-Type", "")
            if content_type.startswith("image/"):
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

    # --- 6. Start the download process ---
    download_and_tag_audiobook(book_data, output_dir)


if __name__ == "__main__":
    main()
