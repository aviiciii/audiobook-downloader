# downloader.py
import os
import time
import subprocess
from http.client import IncompleteRead
import requests
from mutagen.id3 import (
    ID3, APIC, TALB, TPE1, TPE2, TCON, TDRC, TRCK, TIT2, ID3NoHeaderError # pyright: ignore[reportPrivateImportUsage]
)
from rich.progress import Progress
from rich.console import Console

console = Console()

def _download_with_session(session, url, file_path, headers, title, progress_log):
    """Downloads a file using a requests.Session, with retries."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with session.get(url, headers=headers, stream=True, timeout=(10, 180)) as r:
                r.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except (requests.RequestException, IncompleteRead) as e:
            progress_log(
                f"[yellow]Attempt {attempt + 1}/{max_retries} failed for '{title}': {e}[/yellow]"
            )
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    progress_log(f"[red]Failed to download '{title}' after {max_retries} attempts.[/red]")
    return False


def _download_with_yt_dlp(url, output_template, headers, title, progress_log):
    """Downloads a file using yt-dlp."""
    command = [
        "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--retries", "5", "-o", output_template
    ]
    if headers:
        for key, value in headers.items():
            command.extend(["--add-header", f"{key}: {value}"])
    command.append(url)

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        progress_log(f"[red]yt-dlp error downloading '{title}'. Check logs.[/red]")
        if result.stderr.strip():
            console.log(f"stderr:\n{result.stderr}")
        return False
    return True



def _apply_id3_tags(file_path, book_data, track_num, total_tracks):
    """Applies ID3 tags to an MP3 file."""
    try:
        audio = ID3(file_path)
    except ID3NoHeaderError:
        audio = ID3()

    # Ensure metadata values are strings and handle potential None values
    title = book_data.get("title") or "Unknown Title"
    author = book_data.get("author") or "Unknown Author"
    narrator = book_data.get("narrator") or "Unknown Narrator"
    year = str(book_data.get("year") or "")  # Ensure year is a string
    chapter_title = book_data["chapters"][track_num-1].get("title") or f"Chapter {track_num}"

    # Apply the validated tags
    audio["TALB"] = TALB(encoding=3, text=title)
    audio["TPE1"] = TPE1(encoding=3, text=author)
    audio["TPE2"] = TPE2(encoding=3, text=narrator)
    audio["TDRC"] = TDRC(encoding=3, text=year)
    audio["TCON"] = TCON(encoding=3, text="Audiobook")
    audio["TIT2"] = TIT2(encoding=3, text=chapter_title)
    audio["TRCK"] = TRCK(encoding=3, text=f"{track_num}/{total_tracks}")

    if book_data.get("artwork_data") and book_data.get("mime_type"):
        audio["APIC"] = APIC(
            encoding=3,
            mime=book_data["mime_type"],
            type=3,
            desc="Cover",
            data=book_data["artwork_data"],
        )
    audio.save(file_path, v2_version=3)


def download_and_tag_audiobook(book_data):
    """Downloads all chapters, applies ID3 tags, and shows progress."""
    book_title = book_data["title"]
    book_dir = os.path.join(os.getcwd(), "Audiobooks", book_title)
    os.makedirs(book_dir, exist_ok=True)

    chapters = book_data["chapters"]
    total_chapters = len(chapters)
    console.print(f"\n[green]Found {total_chapters} chapters. Starting download...[/green]\n")

    with Progress() as progress:
        task = progress.add_task(f"[cyan]Downloading '{book_title}'...", total=total_chapters)
        session = requests.Session()

        for i, chapter in enumerate(chapters, start=1):
            chapter_title = chapter["title"]
            file_path = os.path.join(book_dir, f"{chapter_title}.mp3")

            if os.path.exists(file_path):
                progress.log(f"[yellow]Skipping '{chapter_title}', already exists.[/yellow]")
                progress.advance(task)
                continue

            progress.log(f"[cyan]Downloading '{chapter_title}'...[/cyan]")
            
            # Decide download strategy
            use_session_download = book_data.get("site") in ("goldenaudiobook.net", "zaudiobooks.com")
            
            if use_session_download:
                success = _download_with_session(
                    session, chapter["url"], file_path, book_data.get("site_headers", {}), chapter_title, progress.log
                )
            else:
                output_template = os.path.join(book_dir, f"{chapter_title}.%(ext)s")
                success = _download_with_yt_dlp(
                    chapter["url"], output_template, book_data.get("site_headers", {}), chapter_title, progress.log
                )

            if success:
                _apply_id3_tags(file_path, book_data, i, total_chapters)
                progress.log(f"[green]✔ Completed '{chapter_title}'[/green]")
            else:
                progress.log(f"[red]❌ Failed to download '{chapter_title}'[/red]")
            
            progress.advance(task)

    console.print(f"\n[bold green]Download complete for '{book_title}'![/bold green]")