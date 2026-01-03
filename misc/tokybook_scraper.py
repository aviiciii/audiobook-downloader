import requests
import json
import time
import os
import re
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
BASE_URL = "https://tokybook.com"
AUDIO_API_PATH = "/api/v1/public/audio"
FULL_AUDIO_BASE = f"{BASE_URL}{AUDIO_API_PATH}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
USER_IP = "1.1.1.1"

# TUNING: Parallel threads
MAX_WORKERS = 10


class TokyBookDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "user-agent": USER_AGENT,
                "origin": BASE_URL,
                "sec-ch-ua-platform": '"macOS"',
                "sec-ch-ua-mobile": "?0",
            }
        )

    def get_slug(self, url):
        return urlparse(url).path.strip("/").split("/")[-1]

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def get_dynamic_headers(self, full_url, audio_id, stream_token):
        """Generates headers matching the specific track path."""
        parsed = urlparse(full_url)
        return {
            "x-audiobook-id": audio_id,
            "x-stream-token": stream_token,
            "x-track-src": parsed.path,
        }

    def get_book_metadata(self, slug):
        # print(f"[*] Fetching metadata for: {slug}...")
        url = f"{BASE_URL}/api/v1/search/post-details"
        payload = {
            "dynamicSlugId": slug,
            "userIdentity": {
                "ipAddress": USER_IP,
                "userAgent": USER_AGENT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            },
        }
        r = self.session.post(url, json=payload)
        r.raise_for_status()
        return r.json()

    def get_playlist(self, audio_book_id, post_detail_token):
        # print("[*] Fetching playlist info...")
        url = f"{BASE_URL}/api/v1/playlist"
        payload = {
            "audioBookId": audio_book_id,
            "postDetailToken": post_detail_token,
            "userIdentity": {
                "ipAddress": USER_IP,
                "userAgent": USER_AGENT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            },
        }
        r = self.session.post(url, json=payload)
        r.raise_for_status()
        return r.json()

    def _fetch_segment_data(self, args):
        """Worker function for ThreadPool."""
        ts_url, audio_id, stream_token, index = args
        headers = self.get_dynamic_headers(ts_url, audio_id, stream_token)
        try:
            r = self.session.get(ts_url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.content
            return None
        except Exception:
            return None

    def get_last_chapter_number(self, folder_path):
        """Finds the highest numbered chapter file in the folder."""
        max_num = 0
        if not os.path.exists(folder_path):
            return 0

        for f in os.listdir(folder_path):
            match = re.search(r"Chapter (\d+)\.mp3", f)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        return max_num

    def download_chapter(self, track, chapter_num, audio_id, stream_token, output_dir):
        filename_only = f"Chapter {chapter_num:03}.mp3"
        filepath = os.path.join(output_dir, filename_only)

        # 1. Get m3u8 Playlist
        safe_src = quote(track["src"])
        m3u8_url = f"{FULL_AUDIO_BASE}/{safe_src}"
        headers_m3u8 = self.get_dynamic_headers(m3u8_url, audio_id, stream_token)

        print(f"--> Processing: {filename_only}")
        r = self.session.get(m3u8_url, headers=headers_m3u8)
        if r.status_code != 200:
            print(f"    [!] Failed to get m3u8. Status: {r.status_code}")
            return

        # 2. Parse Segments
        lines = r.text.splitlines()
        ts_files = [line for line in lines if not line.startswith("#") and line.strip()]
        base_segment_url = m3u8_url.rsplit("/", 1)[0]

        print(f"    Found {len(ts_files)} segments. Downloading...")

        # 3. Prepare Tasks
        tasks = []
        for i, ts_file in enumerate(ts_files):
            if ts_file.startswith("http"):
                ts_url = ts_file
            else:
                ts_url = f"{base_segment_url}/{ts_file}"
            tasks.append((ts_url, audio_id, stream_token, i))

        # 4. Parallel Download
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = executor.map(self._fetch_segment_data, tasks)

            with open(filepath, "wb") as outfile:
                for i, content in enumerate(results):
                    if content:
                        outfile.write(content)
                        # Minimal progress indicator
                        if i % 10 == 0:
                            print(f"\r    {i}/{len(ts_files)}", end="", flush=True)

        print(f"\r    [OK] Complete: {filename_only}          ")

    def run(self, url):
        slug = self.get_slug(url)
        meta = self.get_book_metadata(slug)

        book_title = self.sanitize_filename(meta.get("title", "Unknown_Book"))
        audio_id = meta.get("audioBookId")
        detail_token = meta.get("postDetailToken")

        playlist_data = self.get_playlist(audio_id, detail_token)
        stream_token = playlist_data.get("streamToken")
        tracks = playlist_data.get("tracks", [])

        print(f"[*] Book: '{book_title}' | Chapters: {len(tracks)}")

        if not os.path.exists(book_title):
            os.makedirs(book_title)

        # Find the highest chapter number currently on disk
        max_existing = self.get_last_chapter_number(book_title)

        if max_existing > 0:
            print(
                f"[*] Resume detected. Last file found: Chapter {max_existing:03}.mp3"
            )
            print(
                f"[*] Skipping 1 to {max_existing - 1}. Redownloading {max_existing}..."
            )

        for i, track in enumerate(tracks, start=1):
            if i < max_existing:
                print(f"    [Skipping] Chapter {i:03}.mp3")
                continue

            self.download_chapter(track, i, audio_id, stream_token, book_title)

            # Be polite to the server
            if i % 5 == 0:
                time.sleep(1)

        print("\n[*] All downloads complete.")


if __name__ == "__main__":
    target_url = "https://tokybook.com/post/project-hail-mary-94ed6d"
    dl = TokyBookDownloader()
    dl.run(target_url)
