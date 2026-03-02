import requests

CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# Lightweight regional EPG files (much faster than global)
EPG_US = "https://iptv-org.github.io/epg/guides/us.xml"
EPG_IN = "https://iptv-org.github.io/epg/guides/in.xml"

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
        channel.get("url")
        and not channel.get("is_nsfw")
        and channel.get("status") != "offline"
    )


print("Fetching channel list...")
try:
    data = requests.get(CHANNELS_API, timeout=30).json()
except Exception as e:
    print("Failed to fetch channels:", e)
    exit(1)

selected = []

for c in data:
    if not valid(c):
        continue

    country = c.get("country")
    categories = c.get("categories", [])
    languages = c.get("languages", [])

    # US filter
    if country == "US" and any(cat in US_CATEGORIES for cat in categories):
        selected.append(c)

    # India filter
    elif country == "IN":
        if any(lang in INDIA_LANGUAGES for lang in languages) or \
           any(cat in INDIA_CATEGORIES for cat in categories):
            selected.append(c)

# Deduplicate by URL
unique = {}
for c in selected:
    unique[c["url"]] = c

channels = list(unique.values())[:MAX_CHANNELS]

print(f"Generating playlist with {len(channels)} channels...")

with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for c in channels:
        f.write(
            f'#EXTINF:-1 tvg-id="{c.get("id","")}" '
            f'tvg-name="{c.get("name","")}" '
            f'tvg-logo="{c.get("logo","")}" '
            f'group-title="{",".join(c.get("categories",[]))}",'
            f'{c.get("name","")}\n'
            f'{c.get("url")}\n'
        )

print("Downloading US EPG...")
epg_content = ""

try:
    epg_content += requests.get(EPG_US, timeout=60).text
    print("US EPG added.")
except:
    print("US EPG failed (continuing).")

print("Downloading India EPG...")
try:
    epg_content += requests.get(EPG_IN, timeout=60).text
    print("India EPG added.")
except:
    print("India EPG failed (continuing).")

if epg_content:
    with open(EPG_OUTPUT, "w", encoding="utf-8") as f:
        f.write(epg_content)
    print("EPG file created.")
else:
    print("No EPG downloaded (playlist will still work).")

print("Done.")
