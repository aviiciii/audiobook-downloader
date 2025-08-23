
# Audiobook Downloader and Tagger

This Python script downloads all chapters of an audiobook from `tokybook.com`, embeds metadata (title, author, narrator, etc.), and attaches cover art.


> **Note:**  
> This project is intended for educational purposes only. Please respect copyright laws and the terms of service of [tokybook](https://tokybook.com).


![Last Updated](https://img.shields.io/github/last-commit/aviiciii/tokybook?label=Last%20Updated)
![Repo Stars](https://img.shields.io/github/stars/aviiciii/tokybook?style=social)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Cross--Platform-009688?logo=windows&logoColor=white)
![License](https://img.shields.io/github/license/aviiciii/tokybook?color=orange)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Issues](https://img.shields.io/github/issues/aviiciii/tokybook?color=informational)


## Features

* Downloads all chapters for a given audiobook URL.
* Prompts the user for audiobook details (URL, cover art, author, etc.).
* Automatically scrapes the book title.
* Embeds essential ID3 tags into each MP3 file for proper organization in media players.
* Saves the organized, tagged files into an `Audiobooks` folder in the script's directory.
* Displays a summary table of all metadata before starting the download.

---

## Setup and Installation

To run this script, you need [Python 3](https://www.python.org/downloads/) installed on your system.


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
    1. Download FFmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html).
    2. Extract the files and add the `bin` folder to your system's PATH.

#### Install Python Packages:

You can install the required Python packages using either **pip** or the faster **[uv](https://github.com/astral-sh/uv)** package manager:

**Option A: Using uv (recommended)**

If you have [uv](https://github.com/astral-sh/uv) installed, just run:

```bash
uv sync
```

**Option B: Using pip**

```bash
pip install -r requirements.txt
```



### Step 3: Run the Script

Once the setup is complete, you can run the script from your terminal:

**Option A: Using uv**
```bash
uv run main.py
```

**Option B: Using Python**
```bash
python main.py # or python3 main.py on some systems
```

The script will then prompt you to enter the following information:

* The Tokybook URL for the audiobook.
* Optional details like the author, cover image URL, year, and narrator.

After you provide the details, it will display a summary table, and the download will begin.

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

A special thanks to the team behind `tokybook.com` for providing access to the audiobooks.
