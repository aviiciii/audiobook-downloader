import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import re
from urllib.parse import urlparse

class BigAudiobooksScraper:
    """
    Scrape audiobook metadata and chapter MP3 links specifically from
    bigaudiobooks.net.
    """
    
    def _clean_title_string(self, raw_title: str) -> Dict[str, Optional[str]]:
        """
        Cleans the raw title string (e.g., 'Author - Title Audiobook')
        and attempts to separate the author and main title.
        """
        cleaned = raw_title.strip()
        
        # Remove common suffixes like ' Audiobook', ' Audio Book', and HTML entities
        cleaned = re.sub(r'\s*(Audiobook|Audio Book|Free)$', '', cleaned, flags=re.I).strip()
        
        # Try to split by common separators like '--', '-' or the en dash (\u2013 or &#8211;)
        parts = re.split(r'\s*[-\u2013]\s*', cleaned, maxsplit=1) 

        if len(parts) == 2:
            author = parts[0].strip()
            title = parts[1].strip()
        else:
            # Fallback if separation fails
            author = None
            title = cleaned

        return {"title": title, "author": author}
    def fetch_book_data(self, book_url: str) -> Dict[str, Any]:
        """
        Fetches the book page and extracts all relevant data including chapter URLs.
        
        Args:
            book_url: The URL of the audiobook page to scrape.
            
        Returns:
            A dictionary containing the extracted book metadata and chapters.
        """
        # --- Pre-fetch Setup ---
        expected_domain = "bigaudiobooks.net"
        if urlparse(book_url).netloc != expected_domain:
            print(f"Error: URL {book_url} does not match target domain {expected_domain}")
            return {}

        print(f"Fetching data from: {book_url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': book_url
            }
            response = requests.get(book_url, headers=headers, timeout=10)
            response.raise_for_status()
            html = response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL: {e}")
            return {}

        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract Title and Author
        # Targeting the main headline tag
        raw_h1 = soup.find("h1", class_="title-page") or soup.find("h1")
        raw_title_text = raw_h1.text if raw_h1 else "Unknown Title"
        
        title_info = self._clean_title_string(raw_title_text)
        
        # 2. Extract Cover URL
        # We check both the image tag with data-lazy-src (common on this site) 
        # and the og:image meta tag.
        img_tag = soup.select_one('.wp-caption img')
        cover_tag = img_tag or soup.find('meta', property='og:image')
        
        if cover_tag:
            # Prefer the lazy-loaded source if available, otherwise fall back to src or content
            cover_url = cover_tag.get('data-lazy-src') or cover_tag.get('src') or cover_tag.get('content')
        else:
            cover_url = None

        # 3. Extract Chapter Audio Links
        chapters = []
        # Target <source> tags with type="audio/mpeg" inside the main article body 
        audio_sources = soup.select('.post-single source[type="audio/mpeg"]')
        
        for index, source in enumerate(audio_sources):
            chapter_url = source.get('src')
            if chapter_url:
                # Clean up the URL to remove query parameters like '?_=1'
                clean_url = chapter_url.split('?')[0]
                
                chapter_title = f"Chapter {index + 1:03d}"
                
                chapters.append({
                    "title": chapter_title,
                    "url": clean_url
                })

        return {
            "site": expected_domain,
            "book_url": book_url,
            "title": title_info["title"],
            "author": title_info["author"],
            "narrator": None,
            "year": None,
            "cover_url": cover_url,
            "chapters": chapters,
        }

if __name__ == '__main__':
    # Test URL for bigaudiobooks.net (Gillian Flynn - Dark Places)
    TEST_URL = "https://bigaudiobooks.net/gillian-flynn-dark-places-audiobook/"

    scraper = BigAudiobooksScraper()
    
    book_data = scraper.fetch_book_data(TEST_URL)

    if book_data:
        import json
        print("\n" + "="*50)
        print(f"Testing URL: {TEST_URL}")
        print("="*50)
        print("--- Extracted Book Data ---")
        print(json.dumps(book_data, indent=4))
        print(f"\nTotal Chapters Found: {len(book_data.get('chapters', []))}")
        if book_data.get('chapters'):
            print(f"Example Chapter 1 URL: {book_data['chapters'][0]['url']}")