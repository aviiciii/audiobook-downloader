import os
import re
import requests
import subprocess
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from mutagen.id3 import (
    ID3, APIC, TALB, TPE1, TPE2, TCON, TDRC, TRCK, TIT2, ID3NoHeaderError
)

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
        value_element = item.find("span", class_="detail-value-link") or item.find("span", class_="detail-value")
        
        if value_element:
            # Clean up and store the text value
            value = ' '.join(value_element.text.split())
            if "authors:" in label:
                details['author'] = value
            elif "narrators:" in label:
                details['narrator'] = value
            elif "release date:" in label:
                # Extract year from date like "11-14-17"
                match = re.search(r'\d{2,4}$', value)
                if match:
                    year = match.group()
                    details['year'] = f"20{year}" if len(year) == 2 else year

    return details


# --- MAIN DOWNLOAD FUNCTION ---
def download_and_tag_audiobook(book_url):
    """
    Downloads all chapters of a Tokybook audiobook using the new API structure.
    """
    BASE_URL = "https://tokybook.com"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })

    # --- 1. Fetch the main audiobook page ---
    try:
        print(f"\nFetching book information from: {book_url}")
        response = session.get(book_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title, cover, and other metadata automatically
        book_title = soup.find("h1", class_=re.compile(r"text-4xl")).text.strip()
        sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)

        # Scrape details like author, narrator, year
        scraped_details = get_book_details(soup)
        author_name = scraped_details.get('author')
        narrator_name = scraped_details.get('narrator')
        year_text = scraped_details.get('year')

        cover_img_tag = soup.select_one("div.md\\:col-span-1 img")
        cover_url = urljoin(BASE_URL, cover_img_tag['src']) if cover_img_tag else None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching audiobook page: {e}")
        return
    except AttributeError as e:
        print(f"Error: Could not find required elements. The website structure may have changed. {e}")
        return

    # --- 2. Find the Play Button and extract ID and Token ---
    try:
        play_button = soup.find("button", {"data-action": "play-now"})
        book_id = play_button["data-book-id"]
        token = play_button["data-token"]
    except (TypeError, KeyError):
        print("Error: Could not find the play button, book ID, or token on the page.")
        return

    # --- 3. Call the /player API to get the playlist ---
    try:
        player_url = f"{BASE_URL}/player"
        headers = {"Referer": book_url, "X-Audiobook-Id": book_id, "X-Playback-Token": token}

        
        print("Fetching playlist from API...")
        player_response = session.get(player_url, headers=headers)
        player_response.raise_for_status()
        player_soup = BeautifulSoup(player_response.text, "html.parser")

        chapter_links = []
        for item in player_soup.find_all("li", class_="playlist-item-hls"):
            src = item.get("data-track-src")
            if src:
                chapter_links.append(urljoin(BASE_URL, src))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player data: {e}")
        return

    if not chapter_links:
        print("\nError: Could not find any chapter links in the player API response.")
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
            mime_type = "image/jpeg" if cover_url.lower().endswith(('.jpg', '.jpeg')) else "image/png"
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not download cover art. Error: {e}")
    
    # --- 6. Print Summary ---
    print("\n" + "+" + "-" * 60 + "+")
    print("|" + "Audiobook Summary".center(60) + "|")
    print("+" + "-" * 15 + "+" + "-" * 44 + "+")
    print(f"| {'Title':<13} | {sanitized_title:<42} |")
    print(f"| {'Author':<13} | {(author_name if author_name else 'N/A'):<42} |")
    print(f"| {'Narrator':<13} | {(narrator_name if narrator_name else 'N/A'):<42} |")
    print(f"| {'Year':<13} | {(year_text if year_text else 'N/A'):<42} |")
    print(f"| {'Cover Art':<13} | {'Downloaded' if artwork_data else 'Not Found':<42} |")
    print(f"| {'Save Path':<13} | {book_dir:<42} |")
    print("+" + "-" * 60 + "+")

    # --- 7. Download each chapter using yt-dlp ---
    total_chapters = len(chapter_links)
    print(f"\nFound {total_chapters} chapters. Starting download with yt-dlp...")

    for i, link in enumerate(chapter_links, start=1):
        chapter_title = f"Chapter {i:02}"
        file_name = os.path.join(book_dir, f"{chapter_title}.mp3")
        
        print(f"\n--- Downloading Chapter {i}/{total_chapters} ---")
        
        # Command for yt-dlp
        command = [
            'yt-dlp',
            '--quiet', '--no-warnings', '--progress',
            '--add-header', f"Referer: {book_url}",
            '--add-header', f"x-playback-token: {token}",
            '-o', file_name,
            link
        ]
        
        try:
            # Execute the command
            subprocess.run(command, check=True, capture_output=True, text=True)

            # --- 8. Embed Metadata ---
            print(f"Tagging metadata for {chapter_title}...")
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

        except FileNotFoundError:
            print("\nFATAL ERROR: 'yt-dlp' command not found.")
            print("Please ensure yt-dlp and ffmpeg are installed and in your system's PATH.")
            return
        except subprocess.CalledProcessError as e:
            print(f"\nError downloading {chapter_title}. yt-dlp failed.")
            print(f"Stderr: {e.stderr}")
        except Exception as e:
            print(f"\nAn error occurred while processing {file_name}: {e}")

    print("-" * 30)
    print("All chapters downloaded and tagged successfully!")


if __name__ == "__main__":
    print("--- Tokybook Downloader (Updated for HLS Streams) ---")
    print("Requires 'yt-dlp' and 'ffmpeg' to be installed.")
    
    while True:
        input_book_url = input("\nEnter the Tokybook URL: ").strip()
        if "tokybook.com/post/" in input_book_url:
            download_and_tag_audiobook(book_url=input_book_url)
            break
        print("Error: Please enter a valid book URL (e.g., https://tokybook.com/post/...)")