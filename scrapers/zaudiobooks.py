import requests
from bs4 import BeautifulSoup


class ZaudiobooksScraper:
    def fetch_book_data(self, book_url: str) -> dict:
        """
        Scrape audiobook metadata and chapters from a zaudiobooks.com page.
        """
        response = requests.get(book_url, timeout=30)
        response.raise_for_status()
        html = response.text

        # Save raw HTML if needed for debugging
        # with open("website.html", "w", encoding="utf-8") as f:
        #     f.write(html)

        # Extract track info block
        lines = html.splitlines()
        start_index = None
        for i, line in enumerate(lines):
            if "tracks = [" in line:
                start_index = i
                break

        if start_index is None:
            return None

        # Parse the following lines to extract chapters
        chapters = []
        name = None
        base_url = "https://files01.freeaudiobooks.top/audio/"

        skip_this_track = False

        for line in lines[start_index:]:
            if "name" in line:
                # Extract and clean name
                name = (
                    line.strip()
                    .replace('"', "")
                    .replace("\\", "")
                    .replace("name: ", "")
                    .rstrip(",")
                )
                if name.lower() == "welcome":
                    skip_this_track = True
                else:
                    skip_this_track = False

            if "chapter_link_dropbox" in line:
                if skip_this_track:
                    continue

                chapter_link = (
                    line.strip()
                    .replace('"', "")
                    .replace("\\", "")
                    .replace("chapter_link_dropbox: ", "")
                    .rstrip(",")
                )
                full_url = base_url + chapter_link
                chapter_number = len(chapters) + 1
                chapter_title = f"Chapter {chapter_number:03d}"
                chapters.append({"title": chapter_title, "url": full_url})

            if "]," in line:
                break

        # Extract title and cover (optional with BeautifulSoup)
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("meta", property="og:title")
        cover_tag = soup.find("meta", property="og:image")
        h1_tag = soup.find("h1", class_="page-title")
        img_tag = soup.select_one(".inner-article-content img")

        title = (
            h1_tag.text
            if h1_tag
            else (title_tag["content"] if title_tag else "Unknown Title")
        )
        cover_url = (
            img_tag["src"] if img_tag else (cover_tag["content"] if cover_tag else None)
        )

        return {
            "site": "zaudiobooks.com",
            "book_url": book_url,
            "title": title.strip(),
            "author": None,
            "narrator": None,
            "year": None,
            "cover_url": cover_url,
            "chapters": chapters,
        }
