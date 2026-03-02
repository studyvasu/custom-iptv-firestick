import requests
import xml.etree.ElementTree as ET

CHANNELS_API = "https://iptv-org.github.io/api/channels.json"
GUIDES_API = "https://iptv-org.github.io/api/guides.json"

PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"

MAX_CHANNELS = 400

US_CATEGORIES = [
    "movies",
    "kids",
    "business",
    "travel",
    "music",
    "documentary",
    "education",
    "cooking",
]

INDIA_LANGUAGES = ["hin", "tel"]
INDIA_CATEGORIES = ["travel", "cooking", "kids", "education"]

KIDS_COUNTRIES = ["UK", "AU"]


def valid(channel):
    return (
        channel.get("url")
        and not channel.get("is_nsfw")
        and channel.get("status") != "offline"
    )


# Fetch channel list
print("Fetching channels...")
channels_resp = requests.get(CHANNELS_API, timeout=30)
data = channels_resp.json()

selected = []

for c in data:
    if not valid(c):
        continue

    country = c.get("country")
    cats = c.get("categories", [])
    langs = c.get("languages", [])

    if country == "US" and cats:
        selected.append(c)
    elif country == "IN" and (cats or langs):
        selected.append(c)
    elif country in KIDS_COUNTRIES and any("kid" in cat.lower() for cat in cats):
        selected.append(c)

# Deduplicate
unique = {}
for c in selected:
    unique[c["url"]] = c

channels = list(unique.values())[:MAX_CHANNELS]

print(f"Selected {len(channels)} channels.")

# Write playlist
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for c in channels:
        country = c.get("country")
        cats = ", ".join(c.get("categories", []))
        f.write(
            f'#EXTINF:-1 tvg-id="{c.get("id","")}" '
            f'tvg-name="{c.get("name","")}" '
            f'tvg-logo="{c.get("logo","")}" '
            f'group-title="{country} - {cats}",{c.get("name","")}\n'
            f'{c.get("url")}\n'
        )

print("Playlist created.")

# Fetch guides.json
print("Fetching guides list...")
guides_resp = requests.get(GUIDES_API, timeout=30)
guides_data = guides_resp.json()

# Build EPG root
epg_root = ET.Element("tv")

# Track added channels
added = set()

print("Building filtered EPG...")
for c in channels:
    chan_id = c.get("id")
    # Find all guides matching this channel ID
    matches = [
        g for g in guides_data
        if g.get("channel") == chan_id
    ]
    for guide in matches:
        feed_url = guide.get("feed")
        if not feed_url or feed_url in added:
            continue

        try:
            xml_resp = requests.get(feed_url, timeout=30)
            xml_resp.raise_for_status()
            # Parse feed and merge
            tree = ET.fromstring(xml_resp.content)
            for elem in tree.findall("programme"):
                epg_root.append(elem)
            added.add(feed_url)
            print(f"Added EPG for {chan_id}")
        except Exception:
            print(f"Failed to load EPG feed: {feed_url}")

# Write merged EPG
tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered EPG created.")
