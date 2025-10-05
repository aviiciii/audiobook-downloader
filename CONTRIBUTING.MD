# 📚 Contributing to the Audiobook Scrapers Repository

Thank you for your interest in contributing! This project maintains reliable Python scrapers for various free audiobook websites. Your efforts help keep the data clean and up-to-date.

## 1. Environment Setup

- **Python:** Install Python 3.11+.
- **Clone the repository:**
    ```sh
    git clone https://github.com/aviiciii/audiobook-downloader.git
    cd audiobook-downloader
    ```
- **Install dependencies:**  
    This project requires Python packages and FFmpeg for audio processing.

    - **FFmpeg:**
        - **macOS:**  
            `brew install ffmpeg`
        - **Linux (Debian/Ubuntu):**  
            ```sh
            sudo apt update
            sudo apt install ffmpeg
            ```
        - **Windows:**  
            `winget install ffmpeg`  
            Or download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add the `bin` folder to your PATH.

    - **Python packages:**  
        Use [uv](https://github.com/astral-sh/uv) for fast dependency sync:
        ```sh
        uv sync
        ```

- **Run your scraper:**  
    ```sh
    uv run python your_scraper.py
    ```

## 2. Adding a New Website Scraper

- **Create a Python module** for each new website.

### 2.1. File Naming Convention

- Use the domain name in snake_case, ending with `_scraper.py`.
    - Example:  
        Site: `audiobookheaven.net`  
        File: `audiobookheaven.py`

### 2.2. Scraper Class Structure

- The file must contain a single class named in CamelCase, matching the file name.
    - Example:  
        Class: `AudiobookHeavenScraper`
- Implement:
    ```python
    def fetch_book_data(self, book_url: str) -> Dict[str, Any]:
            ...
    ```

### 2.3. Required Data Fields

Your scraper should extract:

| Field      | Type           | Description                                      |
|------------|----------------|--------------------------------------------------|
| site       | str            | Canonical domain (e.g., "bigaudiobooks.net")     |
| book_url   | str            | The original URL used to fetch the data          |
| title      | str            | Clean book title (e.g., "Dark Places")           |
| author     | str or None    | Author's name (e.g., "Gillian Flynn")            |
| cover_url  | str or None    | Direct URL to the book cover image               |
| chapters   | List[Dict]     | List of dicts with "title" and "url"             |

### 2.4. Metadata Cleaning

- Implement a private helper:  
    `_clean_title_string(self, raw_title: str)`
- Responsibilities:
    - Remove boilerplate (e.g., "Audiobook Free", "(AUDIOBOOK)")
    - Split into title and author

### 2.5. Extracting Chapter Links

- **Priority 1:** Use `<audio>` tags (e.g., `.post-single source[type="audio/mpeg"]`)
- **Priority 2:** If audio is in JavaScript, parse raw HTML to extract links

## 3. Testing and Conventions

### 3.1. Self-Testing Block

- Every scraper must include:
    ```python
    if __name__ == '__main__':
            TEST_URL = "https://bigaudiobooks.net/example-book-url/"
            scraper = NewSiteScraper()
            book_data = scraper.fetch_book_data(TEST_URL)
            if book_data:
                    print(book_data)
    ```

### 3.2. Code Style

- **Formatting:** Use [Black](https://black.readthedocs.io/) (`black your_file.py`)
- **Type hints:** Use `from typing import Dict, Any, Optional`
- **Naming:** PEP 8 (snake_case for variables/functions, PascalCase for classes)
- **Docstrings:** For classes and main methods
- **Defensive coding:** Use `try/except` for HTTP requests and check for `None` with BeautifulSoup

## 4. Submitting Your Contribution

1. Fork the repository
2. Create a new branch (e.g., `feat/new_site_name`)
3. Commit your `[new_site_name].py` and any dependency updates
4. Submit a Pull Request (PR) to `main`
5. In the PR description, mention:
     - Target website
     - Number of chapters found
     - Confirmation that the self-test passed

We look forward to your contributions!
