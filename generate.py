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


print("Fetching channels...")
channels_resp = requests.get(CHANNELS_API, timeout=30)
channels_data = channels_resp.json()

selected = []

for c in channels_data:
    if not valid(c):
        continue

    country = c.get("country")
    categories = c.get("categories", [])
    languages = c.get("languages", [])

    # US filter
    if country == "US" and categories:
        selected.append(c)

    # India filter
    elif country == "IN" and (categories or languages):
        selected.append(c)

    # UK & AU kids
    elif country in KIDS_COUNTRIES and any("kid" in cat.lower() for cat in categories):
        selected.append(c)

# Deduplicate
unique = {}
for c in selected:
    unique[c["url"]] = c

channels = list(unique.values())[:MAX_CHANNELS]

print(f"Selected {len(channels)} channels for playlist.")

# Write playlist
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for c in channels:
        country = c.get("country")
        cats = ", ".join(c.get("categories", []))
        group = f"{country} - {cats}" if cats else country
        f.write(
            f'#EXTINF:-1 tvg-id="{c.get("id","")}" '
            f'tvg-name="{c.get("name","")}" '
            f'tvg-logo="{c.get("logo","")}" '
            f'group-title="{group}",{c.get("name","")}\n'
            f'{c.get("url")}\n'
        )

print("Playlist written.")

# Load guides
print("Fetching guides list...")
guides_resp = requests.get(GUIDES_API, timeout=30)
guides_data = guides_resp.json()

# Helper: normalize names
def normalize(s):
    return "".join(ch.lower() for ch in s if ch.isalnum())

# Build EPG
epg_root = ET.Element("tv")
added_guides = set()

print("Building filtered EPG...")

for c in channels:
    chan_name = c.get("name", "").lower()
    norm_chan = normalize(chan_name)

    # Try best match in guides
    for g in guides_data:
        site_name = g.get("site_name", "") or ""
        norm_site = normalize(site_name)

        if norm_chan in norm_site or norm_site in norm_chan:
            feed_url = g.get("feed")
            if feed_url and feed_url not in added_guides:
                try:
                    xml_resp = requests.get(feed_url, timeout=30)
                    xml_resp.raise_for_status()
                    guide_tree = ET.fromstring(xml_resp.content)
                    for prog in guide_tree.findall("programme"):
                        epg_root.append(prog)
                    added_guides.add(feed_url)
                    print(f"EPG added for {chan_name} via {site_name}")
                except Exception as e:
                    print(f"Failed to download EPG feed {feed_url}: {e}")

# Always write epg.xml even if partial
tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered EPG written.")

print("Done.")
