import requests

# IPTV.org API for channels
CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# External EPG XMLTV URLs (must exist in globetvapp/epg)
EPG_URLS = {
    "US": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedStates/usa1.xml",
        "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedStates/usa2.xml"
    ],
    "IN": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/India/india1.xml"
    ],
    "UK": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedKingdom/uk1.xml"
    ],
    "AU": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia1.xml"
    ]
}

# Output files
PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"
MAX_CHANNELS = 400

# Helper: check if channel is valid
def valid(channel):
    return channel.get("url") and not channel.get("is_nsfw") and channel.get("status") != "offline"

# Fetch channels from IPTV.org API
print("Fetching channels...")
resp = requests.get(CHANNELS_API, timeout=30)
channels_data = resp.json()

# Select channels based on country and category/language
selected = []
for c in channels_data:
    if not valid(c):
        continue
    country = (c.get("country") or "").upper()
    categories = c.get("categories") or []
    languages = c.get("languages") or []

    # US channels (any category)
    if country == "US":
        selected.append(c)

    # India channels (any category or language)
    elif country == "IN":
        selected.append(c)

    # UK/AU kids channels
    elif country in ["UK", "AU"]:
        if any("kid" in cat.lower() for cat in categories):
            selected.append(c)

# Deduplicate by URL
unique = {c["url"]: c for c in selected}
channels = list(unique.values())[:MAX_CHANNELS]

print(f"Selected {len(channels)} channels for playlist")

# Write firestick.m3u
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for c in channels:
        country = (c.get("country") or "").upper()
        cats = ", ".join(c.get("categories") or [])
        group = f"{country} - {cats}" if cats else country
        f.write(
            f'#EXTINF:-1 tvg-id="{c.get("id","")}" '
            f'tvg-name="{c.get("name","")}" '
            f'tvg-logo="{c.get("logo","")}" '
            f'group-title="{group}",{c.get("name","")}\n'
            f'{c.get("url")}\n'
        )

print("Playlist written.")

# Fetch and combine EPG XMLs
print("Fetching external EPG files...")
combined_epg = ""
for country, urls in EPG_URLS.items():
    for url in urls:
        try:
            r = requests.get(url, timeout=30)
            combined_epg += r.text
            print(f"Added EPG for {country} from {url}")
        except Exception as e:
            print(f"Failed to fetch EPG {url}: {e}")

# Write combined EPG
with open(EPG_OUTPUT, "w", encoding="utf-8") as f:
    f.write(combined_epg)

print("EPG file created.")
print("Done.")
