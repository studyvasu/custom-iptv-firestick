import requests
import gzip
import shutil

CHANNELS_API = "https://iptv-org.github.io/api/channels.json"
EPG_SOURCE = "https://iptv-org.github.io/epg/guides.xml.gz"

PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"

MAX_CHANNELS = 400

US_CATEGORIES = [
    "movies", "kids", "business", "travel",
    "music", "documentary", "education", "cooking"
]

INDIA_LANGUAGES = ["hin", "tel"]
INDIA_CATEGORIES = ["travel", "cooking", "kids", "education"]

def valid(channel):
    return (
        channel.get("url") and
        not channel.get("is_nsfw") and
        channel.get("status") != "offline"
    )

print("Fetching channels...")
data = requests.get(CHANNELS_API).json()

selected = []

for c in data:
    if not valid(c):
        continue

    country = c.get("country")
    categories = c.get("categories", [])
    languages = c.get("languages", [])

    if country == "US" and any(cat in US_CATEGORIES for cat in categories):
        selected.append(c)

    elif country == "IN":
        if any(lang in INDIA_LANGUAGES for lang in languages) or \
           any(cat in INDIA_CATEGORIES for cat in categories):
            selected.append(c)

# Deduplicate
unique = {}
for c in selected:
    unique[c["url"]] = c

channels = list(unique.values())[:MAX_CHANNELS]

print(f"Generating playlist with {len(channels)} channels...")

with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write(f'#EXTM3U url-tvg="epg.xml"\n')
    for c in channels:
        f.write(
            f'#EXTINF:-1 tvg-id="{c.get("id","")}" '
            f'tvg-name="{c.get("name","")}" '
            f'tvg-logo="{c.get("logo","")}" '
            f'group-title="{",".join(c.get("categories",[]))}",'
            f'{c.get("name","")}\n'
            f'{c.get("url")}\n'
        )

print("Downloading EPG...")
epg_response = requests.get(EPG_SOURCE)

with open("guides.xml.gz", "wb") as f:
    f.write(epg_response.content)

with gzip.open("guides.xml.gz", "rb") as f_in:
    with open(EPG_OUTPUT, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print("Done.")
