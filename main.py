import os
import requests
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from mutagen.id3 import ID3, APIC, TALB, TPE1, TPE2, TCON, TDRC, TRCK, TIT2, ID3NoHeaderError

# --- Configuration ---
# Replace with the actual audiobook page URL


# Location
# where the downloaded audiobook will be saved
download_location = os.path.join(os.getcwd(), "Audiobooks")

def download_and_tag_audiobook(
    book_url,
    cover_url,
    author_name,
    year_text,
    narrator_name
):
    """
    Downloads all chapters of an audiobook, and embeds metadata and cover art.
    """
    # --- 1. Fetch the main audiobook page and get the title ---
    try:
        print(f"Fetching book information from: {book_url}")
        response = requests.get(book_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, "lxml")
        book_title = soup.find("div", {"class": "inside-page-hero grid-container grid-parent"}).find("h1").text.strip()
        # Sanitize the title to use as a folder name
        sanitized_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)
        print(f"Book Title: {sanitized_title}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching audiobook page: {e}")
        return
    except AttributeError:
        print("Error: Could not find the book title on the page. The website structure may have changed.")
        return

    # --- 2. Create a directory for the audiobook ---
    os.makedirs(download_location, exist_ok=True)
    book_dir = os.path.join(download_location, sanitized_title)
    os.makedirs(book_dir, exist_ok=True)

    # --- 3. Download the cover image data into memory ---
    artwork_data = None
    try:
        if cover_url:
            print(f"Downloading cover art from: {cover_url}")
            artwork_response = requests.get(cover_url)
            artwork_response.raise_for_status()
            artwork_data = artwork_response.content
            artwork_extension = cover_url.split('.')[-1]
            if artwork_extension.lower() not in ['jpg', 'jpeg', 'png']:
                print("Warning: Cover art URL does not point to a valid image format (jpg, jpeg, png).")
                artwork_data = None
            else:
                print("Cover art downloaded successfully.")
        else: 
            print("No cover URL provided. Continuing without cover art.")
    except requests.exceptions.RequestException as e:
        artwork_data = None
        print(f"Warning: Could not download album art. Continuing without it. Error: {e}")

    # validate author and narrator names
    author_name = author_name.strip() if author_name and author_name.strip() else None
    narrator_name = narrator_name.strip() if narrator_name and narrator_name.strip() else None
    year_text = year_text.strip() if year_text and year_text.strip() else None
    

    # --- 4. Find all chapter MP3 links ---
    chapter_links = []
    for script in soup.find_all("script"):
        if "chapter_link_dropbox" in script.text:
            for line in script.text.split("\n"):
                if "chapter_link_dropbox" in line and ".mp3" in line:
                    url = line.split('"')[3]
                    # Filter out the welcome message URL
                    if "welcome-you-to-tokybook.mp3" not in url:
                        # Ensure the URL is correctly formatted
                        if not url.startswith("https://"):
                            url = "https://files02.tokybook.com/audio/" + url.replace(" ", "%20").replace('\\', "/")
                        chapter_links.append(url)
    
    if not chapter_links:
        print("Error: Could not find any chapter links. The website structure may have changed.")
        return

    total_chapters = len(chapter_links)
    print(f"Found {total_chapters} chapters. Starting download...")
    print("-" * 30)

    # --- 5. Download each chapter and embed tags ---
    for i, link in enumerate(chapter_links, start=1):
        file_name = os.path.join(book_dir, f"Chapter {i:02}.mp3")
        
        try:
            chap_response = requests.get(link, stream=True)
            chap_response.raise_for_status()
            chap_size = int(chap_response.headers.get("content-length", 0))

            # Download the file with a progress bar
            with open(file_name, "wb") as f, tqdm(
                total=chap_size, unit="B", unit_scale=True, unit_divisor=1024,
                desc=f"Chapter {i:02}/{total_chapters}"
            ) as progress:
                for chunk in chap_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(len(chunk))

            # --- 6. Embed Metadata ---
            try:
                audio = ID3(file_name)
            except ID3NoHeaderError:
                audio = ID3()

            # Add metadata tags and cover art
            audio.add(TALB(encoding=3, text=sanitized_title))
            audio.add(TCON(encoding=3, text="Audiobook"))
            audio.add(TRCK(encoding=3, text=f"{i}/{total_chapters}"))
            audio.add(TIT2(encoding=3, text=f"Chapter {i:02}"))
            if author_name:
                audio.add(TPE1(encoding=3, text=author_name))
            if narrator_name:
                audio.add(TPE2(encoding=3, text=narrator_name))
            if year_text:
                audio.add(TDRC(encoding=3, text=year_text))
            if artwork_data:
                audio.add(APIC(
                    encoding=3,
                    mime=f"image/{artwork_extension}",  
                    type=3,
                    desc='Cover',
                    data=artwork_data
                ))
            
            audio.save(file_name)

        except requests.exceptions.RequestException as e:
            print(f"\nError downloading {link}: {e}")
        except Exception as e:
            print(f"\nAn error occurred while processing {file_name}: {e}")

    print("-" * 30)
    print("All chapters downloaded successfully!")


if __name__ == "__main__":
    print("Please provide the audiobook details:")
    
    input_book_url = input("Enter the Tokybook URL: ").strip()
    input_cover_url = input("Enter the direct URL for the cover image (preferably a .jpg or .png): ").strip()
    input_author_name = input("Enter the author's name (optional, press Enter to skip): ").strip()
    input_year_text = input("Enter the publication year (optional, press Enter to skip): ").strip()
    input_narrator_name = input("Enter the narrator's name (optional, press Enter to skip): ").strip()

    print("\nStarting the process with the provided information...\n")
    
    # --- Run the main function with user-provided details ---
    download_and_tag_audiobook(
        book_url=input_book_url,
        cover_url=input_cover_url,
        author_name=input_author_name,
        year_text=input_year_text,
        narrator_name=input_narrator_name
    )