import os
import requests
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
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


def download_and_tag_audiobook(
    book_url, cover_url, author_name, year_text, narrator_name
):
    """
    Downloads all chapters of an audiobook, and embeds metadata and cover art.

    Args:
        book_url (str): The URL of the tokybook.com page for the audiobook.
        cover_url (str): The direct URL to the cover image.
        author_name (str): The name of the author.
        year_text (str): The publication year of the audiobook.
        narrator_name (str): The name(s) of the narrator(s).
    """
    # Genre is kept constant as requested
    genre_text = "Audiobook"

    # --- 1. Fetch the main audiobook page and get the title ---
    try:
        print(f"\n\nFetching book information from: {book_url}")
        response = requests.get(book_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, "html.parser")
        book_title = (
            soup.find("div", {"class": "inside-page-hero grid-container grid-parent"})
            .find("h1")
            .text.strip()
        )
        sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching audiobook page: {e}")
        return
    except AttributeError:
        print(
            "Error: Could not find the book title on the page. The website structure may have changed."
        )
        return

    # --- 2. Create a directory for the audiobook ---
    download_location = os.path.join(os.getcwd(), "Audiobooks")
    os.makedirs(download_location, exist_ok=True)
    book_dir = os.path.join(download_location, sanitized_title)
    os.makedirs(book_dir, exist_ok=True)

    # --- 3. Download the cover image data into memory ---
    artwork_data = None
    mime_type = None
    try:
        if cover_url:
            artwork_response = requests.get(cover_url)
            artwork_response.raise_for_status()
            artwork_data = artwork_response.content
            # Determine MIME type from URL extension
            extension = cover_url.split(".")[-1].lower()
            if extension in ["jpg", "jpeg"]:
                mime_type = "image/jpeg"
            elif extension == "png":
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg"  # Default
    except requests.exceptions.RequestException as e:
        print(
            f"Warning: Could not download album art. Continuing without it. Error: {e}"
        )

    # --- 4. Print Summary Table ---
    # Truncate long strings to keep table format clean
    display_title = (
        (sanitized_title[:48] + "..") if len(sanitized_title) > 50 else sanitized_title
    )
    display_path = (book_dir[:48] + "..") if len(book_dir) > 50 else book_dir
    cover_status = "Downloaded" if artwork_data else "Skipped"

    print("\n" + "+" + "-" * 60 + "+")
    print("|" + "Audiobook Summary".center(60) + "|")
    print("+" + "-" * 15 + "+" + "-" * 44 + "+")
    print(f"| {'Title':<13} | {display_title:<42} |")
    print(
        f"| {'Author':<13} | {(author_name if author_name else 'Not Provided'):<42} |"
    )
    print(
        f"| {'Narrator':<13} | {(narrator_name if narrator_name else 'Not Provided'):<42} |"
    )
    print(f"| {'Year':<13} | {(year_text if year_text else 'Not Provided'):<42} |")
    print(f"| {'Genre':<13} | {genre_text:<42} |")
    print(f"| {'Cover Art':<13} | {cover_status:<42} |")
    print("+" + "-" * 15 + "+" + "-" * 44 + "+")
    print(f"| {'Save Path':<13} | {display_path:<42} |")
    print("+" + "-" * 60 + "+")

    # --- 5. Find all chapter MP3 links ---
    chapter_links = []
    for script in soup.find_all("script"):
        if "chapter_link_dropbox" in script.text:
            for line in script.text.split("\n"):
                if "chapter_link_dropbox" in line and ".mp3" in line:
                    url = line.split('"')[3]
                    if "welcome-you-to-tokybook.mp3" not in url:
                        if not url.startswith("https://"):
                            url = "https://files02.tokybook.com/audio/" + url.replace(
                                " ", "%20"
                            ).replace("\\", "/")
                        chapter_links.append(url)

    if not chapter_links:
        print(
            "\nError: Could not find any chapter links. The website structure may have changed."
        )
        return

    total_chapters = len(chapter_links)
    print(f"\nFound {total_chapters} chapters. Starting download...")
    print("-" * 30)

    # --- 6. Download each chapter and embed tags ---
    for i, link in enumerate(chapter_links, start=1):
        file_name = os.path.join(book_dir, f"Chapter {i:02}.mp3")

        try:
            chap_response = requests.get(link, stream=True)
            chap_response.raise_for_status()
            chap_size = int(chap_response.headers.get("content-length", 0))

            with open(file_name, "wb") as f, tqdm(
                total=chap_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=f"Chapter {i:02}/{total_chapters}",
            ) as progress:
                for chunk in chap_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(len(chunk))

            # --- 7. Embed Metadata ---
            try:
                audio = ID3(file_name)
            except ID3NoHeaderError:
                audio = ID3()

            # Add metadata tags
            audio.add(TALB(encoding=3, text=sanitized_title))
            audio.add(TCON(encoding=3, text=genre_text))
            audio.add(TRCK(encoding=3, text=f"{i}/{total_chapters}"))
            audio.add(TIT2(encoding=3, text=f"Chapter {i:02}"))

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

            audio.save(file_name)

        except requests.exceptions.RequestException as e:
            print(f"\nError downloading {link}: {e}")
        except Exception as e:
            print(f"\nAn error occurred while processing {file_name}: {e}")

    print("-" * 30)
    print("All chapters downloaded and tagged successfully!")


if __name__ == "__main__":
    print("--- Audiobook Downloader and Tagger ---")

    while True:
        input_book_url = input("Enter the Tokybook URL: ").strip()
        if "tokybook.com" in input_book_url:
            break
        print("Error: Please enter a valid URL from tokybook.com")

    input_cover_url = input(
        "Enter the direct URL for the cover image (or press Enter to skip): "
    ).strip()
    input_author_name = input(
        "Enter the author's name (or press Enter to skip): "
    ).strip()
    while True:
        input_year_text = input(
            "Enter the publication year (or press Enter to skip): "
        ).strip()
        if not input_year_text or (
            input_year_text.isdigit() and 1000 <= int(input_year_text) <= 2169
        ):
            break
        print("Error: Please enter a valid year (e.g., 2069) or leave blank to skip.")
    input_narrator_name = input(
        "Enter the narrator's name (or press Enter to skip): "
    ).strip()

    download_and_tag_audiobook(
        book_url=input_book_url,
        cover_url=input_cover_url,
        author_name=input_author_name,
        year_text=input_year_text,
        narrator_name=input_narrator_name,
    )
