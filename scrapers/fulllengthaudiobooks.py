import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import re

class FulllengthAudiobooksScraper:
    """
    Scrape audiobook metadata and chapter MP3 links from a fulllengthaudiobooks.net page.
    """
    
    def _clean_title_string(self, raw_title: str) -> Dict[str, Optional[str]]:
        """
        Cleans the raw title string (e.g., 'Author - Title Audiobook Free')
        and attempts to separate the author and main title.
        """
        cleaned = raw_title.strip()
        
        # Remove common suffixes and redundant text
        cleaned = re.sub(r'\s*(Audiobook\s*Free|Audio Book Online|Audiobook|Free)$', '', cleaned, flags=re.I).strip()
        
        # Try to split by common separators like '--' or '-'
        parts = re.split(r'\s*[-\u2013]\s*', cleaned, maxsplit=1) # \u2013 is the en dash (&#8211;)

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
        # Fetch the HTML content
        print(f"Fetching data from: {book_url}")
        try:
            response = requests.get(book_url, timeout=10)
            response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
            html = response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL: {e}")
            return {}

        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract Title and Author
        raw_h1 = soup.find("h1", class_="entry-title post-title")
        raw_title_text = raw_h1.text if raw_h1 else "Unknown Title"
        
        title_info = self._clean_title_string(raw_title_text)
        
        # 2. Extract Cover URL
        # Target the main image inside the content area.
        cover_tag = soup.select_one('.wp-caption img')
        cover_url = cover_tag.get('src') if cover_tag else None

        # 3. Extract Chapter Audio Links
        chapters = []
        # Find all <source> tags with type="audio/mpeg" inside the main content area
        audio_sources = soup.select('.entry source[type="audio/mpeg"]')
        
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
            "site": "fulllengthaudiobooks.net",
            "book_url": book_url,
            "title": title_info["title"],
            "author": title_info["author"],
            "narrator": None, # Narrator is not easily scrapable from this HTML
            "year": None,    # Year is not easily scrapable from this HTML
            "cover_url": cover_url,
            "chapters": chapters,
        }

if __name__ == '__main__':
    # This URL corresponds to the HTML provided by the user (Adam Silvera - They Both Die at the End)
    TEST_URL = "https://fulllengthaudiobooks.net/adam-silvera-they-both-die-at-the-end-audiobook/"

    scraper = FulllengthAudiobooksScraper()
    book_data = scraper.fetch_book_data(TEST_URL)

    if book_data:
        import json
        print("\n--- Extracted Book Data ---")
        print(json.dumps(book_data, indent=4))
        print(f"\nTotal Chapters Found: {len(book_data.get('chapters', []))}")
        if book_data.get('chapters'):
            print(f"Example Chapter 1 URL: {book_data['chapters'][0]['url']}")