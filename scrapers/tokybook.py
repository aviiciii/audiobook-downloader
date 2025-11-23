import requests
import json
import time
import re
import os
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor


class TokybookScraper:
    BASE_URL = "https://tokybook.com"
    AUDIO_API_PATH = "/api/v1/public/audio"
    FULL_AUDIO_BASE = f"{BASE_URL}{AUDIO_API_PATH}"
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

    def fetch_book_data(self, url):
        """
        Scrapes metadata and prepares the chapter list with tokens.
        """
        slug = self._get_slug(url)
        session = requests.Session()
        session.headers.update({"user-agent": self.USER_AGENT, "origin": self.BASE_URL})

        # 1. Get Post Details (Metadata + ID)
        print(f"[*] Fetching metadata for: {slug}...")
        details_url = f"{self.BASE_URL}/api/v1/search/post-details"
        payload = {
            "dynamicSlugId": slug,
            "userIdentity": {
                "ipAddress": "127.0.0.1",  # Server ignores exact IP usually
                "userAgent": self.USER_AGENT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            },
        }

        try:
            r = session.post(details_url, json=payload)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[!] Error fetching details: {e}")
            return None

        title = data.get("title")
        audio_book_id = data.get("audioBookId")
        post_detail_token = data.get("postDetailToken")

        # 2. Get Playlist (Tracks + Stream Token)
        print(f"[*] Fetching playlist for ID: {audio_book_id}...")
        playlist_url = f"{self.BASE_URL}/api/v1/playlist"
        playlist_payload = {
            "audioBookId": audio_book_id,
            "postDetailToken": post_detail_token,
            "userIdentity": payload["userIdentity"],
        }

        try:
            r = session.post(playlist_url, json=playlist_payload)
            r.raise_for_status()
            playlist_data = r.json()
        except Exception as e:
            print(f"[!] Error fetching playlist: {e}")
            return None

        stream_token = playlist_data.get("streamToken")
        tracks = playlist_data.get("tracks", [])

        # 3. Format for main.py
        chapters = []
        chapter_number = 1

        for track in tracks:
            chapters.append(
                {
                    "title": f"Chapter {chapter_number:03d}",
                    "url": track.get("src"),  # This is the relative path
                    "src": track.get("src"),  # Keeping original for reference
                    "duration": track.get("duration"),
                }
            )
            chapter_number += 1
        return {
            "site": "tokybook.com",
            "title": title,
            
            "author": data.get("authors", [{}])[0].get("name")
            if data.get("authors")
            else None,
            
            "narrator": data.get("narrators", [{}])[0].get("name")
            if data.get("narrators")
            else None,
            
            "year": str(data.get("year"))
            if data.get("year")
            else None,  # API doesn't always give year, defaulting
            
            "cover_url": data.get("coverImage") if data.get("coverImage") else None,
            "chapters": chapters,
            "audio_book_id": audio_book_id,  # Crucial for download
            "stream_token": stream_token,  # Crucial for download
            "site_headers": {"user-agent": self.USER_AGENT},
        }

    def _get_slug(self, url):
        return urlparse(url).path.strip("/").split("/")[-1]

    @staticmethod
    def _get_dynamic_headers(full_url, audio_id, stream_token):
        parsed = urlparse(full_url)
        return {
            "user-agent": TokybookScraper.USER_AGENT,
            "x-audiobook-id": audio_id,
            "x-stream-token": stream_token,
            "x-track-src": parsed.path,
        }

    @staticmethod
    def _fetch_segment(args):
        """Worker for ThreadPool"""
        ts_url, audio_id, stream_token = args
        headers = TokybookScraper._get_dynamic_headers(ts_url, audio_id, stream_token)
        try:
            # Short timeout for segments to fail fast and potentially retry (handled by main exception)
            r = requests.get(ts_url, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        return None

    @staticmethod
    def download_chapter(chapter_data, book_data, output_path, progress):
        """
        Specialized downloader for Tokybook that handles m3u8 and parallel segments.
        """
        audio_id = book_data.get("audio_book_id")
        stream_token = book_data.get("stream_token")

        # Construct M3U8 URL
        # The chapter['url'] from fetch_book_data is relative path like "ID/Chapter.m3u8"
        # We need to quote it and prepend base
        safe_src = quote(chapter_data["url"])
        m3u8_url = f"{TokybookScraper.FULL_AUDIO_BASE}/{safe_src}"

        headers = TokybookScraper._get_dynamic_headers(m3u8_url, audio_id, stream_token)

        # 1. Get Playlist
        r = requests.get(m3u8_url, headers=headers)
        if r.status_code != 200:
            raise Exception(f"Failed to fetch m3u8: {r.status_code}")

        lines = r.text.splitlines()
        ts_files = [line for line in lines if not line.startswith("#") and line.strip()]
        base_segment_url = m3u8_url.rsplit("/", 1)[0]

        # 2. Prepare Parallel Tasks
        tasks = []
        for ts_file in ts_files:
            if ts_file.startswith("http"):
                ts_url = ts_file
            else:
                ts_url = f"{base_segment_url}/{ts_file}"
            tasks.append((ts_url, audio_id, stream_token))

        # 3. Download
        progress.log(f"[dim]Downloading {len(ts_files)} segments in parallel...[/dim]")

        downloaded_buffer = []

        # Using 10 threads for speed
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(TokybookScraper._fetch_segment, tasks)

            for chunk in results:
                if chunk:
                    downloaded_buffer.append(chunk)
                else:
                    raise Exception("Segment download failed")

        # 4. Write to disk
        with open(output_path, "wb") as f:
            for chunk in downloaded_buffer:
                f.write(chunk)
