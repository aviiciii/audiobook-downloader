import requests
import json
import subprocess
import os
import re
from typing import Dict, Any, List
from urllib.parse import urlparse  # Import urlparse for path extraction

# --- CONFIGURATION (UPDATE THESE VALUES) ---
# The base book ID from the original request
AUDIOBOOK_ID = "B08G9PRS1K"
# The dynamic token required in the POST payload (must be updated from a live session)
POST_DETAIL_TOKEN = ""
# The directory where the final audio files will be saved
OUTPUT_DIR = "Project_Hail_Mary_Audiobook"

# --- API ENDPOINTS AND HEADERS ---
PLAYLIST_URL = "https://tokybook.com/api/v1/playlist"
BASE_STREAM_URL = "https://tokybook.com/api/v1/public/audio/"

HEADERS = {
    "authority": "tokybook.com",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "content-type": "application/json",
    "dnt": "1",
    "origin": "https://tokybook.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
}


def get_stream_data() -> Dict[str, Any]:
    """
    Performs the initial POST request to retrieve the stream token and track list.
    """
    print("Step 1: Requesting stream token and playlist...")

    # The timestamp and IP address are provided in the payload but may be optional/ignored
    # or validated server-side. Using the values provided for demonstration.
    payload = {
        "audioBookId": AUDIOBOOK_ID,
        "postDetailToken": POST_DETAIL_TOKEN,
        "userIdentity": {
            "ipAddress": "122.164.84.165",  # Update if necessary
            "userAgent": HEADERS["user-agent"],
            "timestamp": "2025-11-23T16:52:25.929Z",  # Update if necessary
        },
    }

    try:
        response = requests.post(
            PLAYLIST_URL, headers=HEADERS, json=payload, timeout=15
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to playlist API: {e}")
        return {}


def download_track(stream_token: str, track_info: Dict[str, str], book_title: str):
    """
    Uses yt-dlp to download and convert a single HLS track.
    """
    # Clean track title for a valid filename
    safe_title = re.sub(r'[\\/:*?"<>|]', "", track_info["trackTitle"]).strip()

    # Construct the final M3U8 URL
    m3u8_path = track_info["src"]
    m3u8_url = BASE_STREAM_URL + m3u8_path

    # Extract the URL path for the X-Track-Src header
    track_src_path = urlparse(m3u8_url).path

    # Output file path and format (e.g., 'Project_Hail_Mary_Audiobook/Project Hail Mary - ch - 001.mp3')
    output_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp3")

    print(f"\nDownloading: {safe_title}")

    # yt-dlp command arguments.
    command = [
        "yt-dlp",
        # HLS URL is the input source
        m3u8_url,
        # Set custom headers using --add-header
        "--add-header",
        f"X-Stream-Token:{stream_token}",
        "--add-header",
        f"X-AudioBook-Id:{AUDIOBOOK_ID}",
        "--add-header",
        f"X-Track-Src:{track_src_path}",
        "--add-header",
        "Referer: https://tokybook.com/",
        # Extract audio only
        "-x",
        # Convert to mp3 format
        "--audio-format",
        "mp3",
        # Set output path and filename
        "-o",
        output_path,
        # Verbose output (optional, good for debugging)
        "-v",
    ]

    try:
        # Execute the yt-dlp command
        subprocess.run(command, check=True, text=True, capture_output=True)
        print(f"Success: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {safe_title}:")
        print(e.stderr)
    except FileNotFoundError:
        print("\nERROR: yt-dlp command not found.")
        print(
            "Please ensure yt-dlp and ffmpeg are installed and accessible in your system's PATH."
        )


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    data = get_stream_data()

    if not data or "streamToken" not in data or not data.get("tracks"):
        print(
            "Failed to retrieve stream data or token. Check your POST_DETAIL_TOKEN and AUDIOBOOK_ID."
        )
        return

    stream_token = data["streamToken"]
    tracks = data["tracks"]
    book_title = data.get("bookTitle", "Unknown Book")

    print(f"\nStep 2: Starting download for '{book_title}' ({len(tracks)} chapters)...")
    print("-" * 30)

    for track in tracks:
        download_track(stream_token, track, book_title)

    print("\n--- Download complete ---")


if __name__ == "__main__":
    main()
