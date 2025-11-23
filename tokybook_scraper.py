import requests
import json
import time
import os
import re
from urllib.parse import urlparse, quote

# --- CONFIGURATION ---
BASE_URL = "https://tokybook.com"
# Based on your logs, the base path for the audio files:
AUDIO_API_PATH = "/api/v1/public/audio" 
FULL_AUDIO_BASE = f"{BASE_URL}{AUDIO_API_PATH}"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
USER_IP = "1.1.1.1"

class TokyBookDownloader:
    def __init__(self):
        self.session = requests.Session()
        # Standard headers for all requests
        self.session.headers.update({
            "user-agent": USER_AGENT,
            "origin": BASE_URL,
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua-mobile": "?0"
        })

    def get_slug(self, url):
        return urlparse(url).path.strip("/").split("/")[-1]

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def get_dynamic_headers(self, full_url, audio_id, stream_token):
        """
        Generates the mandatory headers for API 3.
        x-track-src must match the path component of the URL.
        """
        parsed = urlparse(full_url)
        path = parsed.path
        
        # Ensure path is properly encoded if needed (browsers usually send %20 for spaces)
        # However, requests usually handles the URL, but the header needs the string.
        return {
            "x-audiobook-id": audio_id,
            "x-stream-token": stream_token,
            "x-track-src": path 
        }

    def get_book_metadata(self, slug):
        """API 1: Get Book ID and Detail Token"""
        print(f"[*] Fetching metadata for: {slug}...")
        url = f"{BASE_URL}/api/v1/search/post-details"
        payload = {
            "dynamicSlugId": slug,
            "userIdentity": {
                "ipAddress": USER_IP,
                "userAgent": USER_AGENT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            }
        }
        
        r = self.session.post(url, json=payload)
        if r.status_code != 200:
            raise Exception(f"Failed to get metadata: {r.text}")
        return r.json()

    def get_playlist(self, audio_book_id, post_detail_token):
        """API 2: Get List of Chapters and Stream Token"""
        print("[*] Fetching playlist info...")
        url = f"{BASE_URL}/api/v1/playlist"
        payload = {
            "audioBookId": audio_book_id,
            "postDetailToken": post_detail_token,
            "userIdentity": {
                "ipAddress": USER_IP,
                "userAgent": USER_AGENT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            }
        }

        r = self.session.post(url, json=payload)
        if r.status_code != 200:
            raise Exception(f"Failed to get playlist: {r.text}")
        return r.json()

    def download_chapter(self, track, audio_id, stream_token, output_dir):
        """API 3: Downloads m3u8 and segments with specific headers."""
        title = self.sanitize_filename(track['trackTitle'])
        filename = f"{output_dir}/{title}.mp3"
        
        # Check if file already exists to skip
        if os.path.exists(filename):
            print(f"    [Skipping] {title} (already exists)")
            return

        # 1. Build the M3U8 URL
        # track['src'] is relative like "B08G.../Chapter 1.m3u8"
        # We must encode the spaces to %20 to match your logs
        safe_src = quote(track['src']) 
        m3u8_url = f"{FULL_AUDIO_BASE}/{safe_src}"
        
        # 2. Get Headers for M3U8
        headers_m3u8 = self.get_dynamic_headers(m3u8_url, audio_id, stream_token)
        
        print(f"--> Processing: {title}")
        r = self.session.get(m3u8_url, headers=headers_m3u8)
        if r.status_code != 200:
            print(f"    [!] Failed to get m3u8. Status: {r.status_code}")
            print(f"    [!] Debug URL: {m3u8_url}")
            return

        # 3. Parse Segments
        lines = r.text.splitlines()
        ts_files = [line for line in lines if not line.startswith("#") and line.strip()]
        
        base_segment_url = m3u8_url.rsplit('/', 1)[0]
        
        # 4. Download Segments
        with open(filename, 'wb') as outfile:
            for i, ts_file in enumerate(ts_files):
                # Construct absolute URL for the segment
                if ts_file.startswith("http"):
                    ts_url = ts_file
                else:
                    ts_url = f"{base_segment_url}/{ts_file}"

                # !!! CRITICAL: Generate headers for THIS specific TS file !!!
                # The x-track-src must update to point to the .ts file
                ts_headers = self.get_dynamic_headers(ts_url, audio_id, stream_token)
                
                ts_r = self.session.get(ts_url, headers=ts_headers)
                
                if ts_r.status_code == 200:
                    outfile.write(ts_r.content)
                    print(f"\r    Segment {i+1}/{len(ts_files)}", end="", flush=True)
                else:
                    print(f"\n    [!] Failed segment {i}: {ts_r.status_code}")

        print(f"\n    [OK] Saved: {filename}")

    def run(self, url):
        # Step 1
        slug = self.get_slug(url)
        meta = self.get_book_metadata(slug)
        
        book_title = self.sanitize_filename(meta.get('title', 'Unknown_Book'))
        audio_id = meta.get('audioBookId')
        detail_token = meta.get('postDetailToken')

        # Step 2
        playlist_data = self.get_playlist(audio_id, detail_token)
        stream_token = playlist_data.get('streamToken') # The special token for headers
        tracks = playlist_data.get('tracks', [])

        print(f"[*] Found {len(tracks)} chapters for '{book_title}'")
        print(f"[*] Audio ID: {audio_id}")
        
        if not os.path.exists(book_title):
            os.makedirs(book_title)

        # Step 3
        for track in tracks:
            self.download_chapter(track, audio_id, stream_token, book_title)
            time.sleep(1) # Be polite

        print("\n[*] All downloads complete.")

# --- MAIN ---
if __name__ == "__main__":
    target_url = "https://tokybook.com/post/project-hail-mary-94ed6d"
    
    dl = TokyBookDownloader()
    dl.run(target_url)