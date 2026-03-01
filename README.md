# Audiobook Downloader and Tagger

This Python script downloads all chapters of an audiobook from supported websites, embeds metadata (title, author, narrator, etc.), and attaches cover art.

> **Note:**
> This project is intended for educational purposes only. Please respect copyright laws and the terms of service of the respective websites.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/aviiciii)

![Last Updated](https://img.shields.io/github/last-commit/aviiciii/tokybook?label=Last%20Updated)
![Repo Stars](https://img.shields.io/github/stars/aviiciii/tokybook?style=social)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Cross--Platform-009688?logo=windows&logoColor=white)
![License](https://img.shields.io/github/license/aviiciii/tokybook?color=orange)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Issues](https://img.shields.io/github/issues/aviiciii/tokybook?color=informational)

## Supported Sites

* [tokybook.com](https://tokybook.com)
* [zaudiobooks.com](https://zaudiobooks.com)
* [fulllengthaudiobooks.net](https://fulllengthaudiobooks.net/)
* [hdaudiobooks.net](https://hdaudiobooks.net/)
* [bigaudiobooks.net](https://bigaudiobooks.net/)
* [goldenaudiobook.com](https://goldenaudiobook.com) (only on Mac)

## Features

* **CLI and interactive modes**: Pass URL and options via command line, or use interactive prompts.
* Downloads all chapters (or a selected range) for a given audiobook URL.
* Prompts the user for audiobook details (URL, cover art, author, etc.).
* Automatically scrapes the book title.
* Embeds essential ID3 tags into each MP3 file for proper organization in media players.
* Saves the organized, tagged files into an `Audiobooks` folder (configurable via `-o`).
* Displays a summary table of all metadata before starting the download.

---

## Setup and Installation

To run this script, you need [Python 3.11](https://www.python.org/downloads/) installed on your system.

### Step 1: Clone the Repository

Start by cloning this repository to your local machine:

```bash
git clone https://github.com/aviiciii/tokybook.git
cd tokybook
```

### Step 2: Install Required Dependencies

This project requires both Python packages and FFmpeg for audio processing.

#### Install FFmpeg:

Make sure FFmpeg is available in your system's PATH.

- **macOS:**
  ```bash
  brew install ffmpeg
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt update
  sudo apt install ffmpeg
  ```
- **Windows:**
  1. The easiest way is to use [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/):
     ```bash
     winget install ffmpeg
     ```
  2. Alternatively, download FFmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html), extract the files, and add the `bin` folder to your system's PATH.

#### Install Python Packages and Run the Script:

This project uses **[uv](https://github.com/astral-sh/uv)** as its primary package manager. You can also use pip as a fallback.

**Using uv (recommended)**

If you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, just run:

```bash
uv run audiobook-downloader
```

Or run the script directly:

```bash
uv run main.py
```

> uv automatically creates a virtual environment, installs dependencies, and runs the command — no manual setup required.

**Using pip (fallback)**

```bash
pip install .
```

```bash
audiobook-downloader  # or: python main.py
```

### Usage

The tool supports both **interactive mode** (no arguments) and **CLI mode** (with arguments):

#### Interactive Mode

Simply run without arguments and follow the prompts:

```bash
uv run audiobook-downloader
```

#### CLI Mode

Pass the URL and options directly:

```bash
uv run audiobook-downloader <URL> [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `-o`, `--output DIR` | Output directory (default: `./Audiobooks`) |
| `-c`, `--chapters RANGE` | Chapter selection, e.g. `"1-5,8,10"` (default: all) |
| `--title TITLE` | Override book title |
| `--author AUTHOR` | Override author name |
| `--narrator NARRATOR` | Override narrator name |
| `--year YEAR` | Override publication year |
| `--cover-url URL` | Override cover art URL |

**Examples:**

```bash
# Download all chapters
uv run audiobook-downloader https://tokybook.com/post/project-hail-mary-94ed6d

# Download specific chapters
uv run audiobook-downloader https://tokybook.com/post/circe-c21c22 -c "1-5,8"

# Specify output directory
uv run audiobook-downloader https://zaudiobooks.com/red-rising/ -o ~/my-audiobooks

# Override metadata
uv run audiobook-downloader https://tokybook.com/post/some-book --title "My Book" --author "Author Name"

# Show help
uv run audiobook-downloader --help
```

When using CLI mode with a URL argument, interactive prompts for metadata editing and chapter selection are skipped (use `--title`, `--author`, etc. and `-c` to set them directly).

Enjoy :)

---

## Acknowledgements

This tool was made possible by the developers of the following open-source libraries:

* **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
* **[FFmpeg](https://ffmpeg.org/)**
* **[Requests](https://requests.readthedocs.io/en/latest/)**
* **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)**
* **[Tqdm](https://github.com/tqdm/tqdm)**
* **[Mutagen](https://mutagen.readthedocs.io/en/latest/)**
* **[Rich](https://github.com/Textualize/rich)**
* **[uv](https://github.com/astral-sh/uv)**

A special thanks to the team behind `tokybook.com`, `goldenaudiobook.com` and `zaudiobooks.com` for providing access to the audiobooks.
