import requests
import sys
from urllib.parse import urlparse

# Some fake headers to look a little more browserly
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "x-audiobook-id": "B08G9PRS1K",
"x-stream-token": "",
"x-track-src": "/api/v1/public/audio/B08G9PRS1K-Project-Hail-Mary-Audiobook/Project%20Hail%20Mary%20-%20ch%20-%20001.m3u8"}

# if len(sys.argv) != 3:
#     print(
#         "Requires parameters: m3u8_url output-file-name"
#     )
#     sys.exit(1)

initial_url = "https://tokybook.com/api/v1/public/audio/B08G9PRS1K-Project-Hail-Mary-Audiobook/Project%20Hail%20Mary%20-%20ch%20-%20001.m3u8"
output_file = "PHM.mpg"
segments = []

req = requests.get(initial_url, headers=HEADERS)

print(req.text)

# Get segments file; segments end in .ts, everything else is junk
for line in req.iter_lines():
    line = line.decode('utf8').strip()

    if line.endswith('.ts'):
        segments.append(line)

# Parse base url
parsed = urlparse(initial_url)

# open file, dump segments into it
with open(output_file, 'wb') as output:
    for line in segments:
        url = f"{parsed.scheme}://{parsed.netloc}{line}"
        HEADERS["x-track-src"] = urlparse(url).path
        print(f"Downloading {url}...")
        seg = requests.get(url, headers=HEADERS)
        output.write(seg.content)