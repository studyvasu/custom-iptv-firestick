import requests

CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# External country EPG sources
EPG_SOURCES = {
    "US": "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedStates/usa.xml",
    "IN": "https://raw.githubusercontent.com/globetvapp/epg/main/India/india.xml",
    "UK": "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedKingdom/uk.xml",
    "AU": "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia.xml"
}

PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"
MAX_CHANNELS = 400

US_CATEGORIES = [
    "movies", "kids", "business", "travel",
    "music", "documentary", "education", "cooking"
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

    country = (c.get("country") or "").upper()
    categories = c.get("categories", [])
    languages = c.get("languages", [])

    if country == "US":
        if categories:
            selected.append(c)
    elif country == "IN":
        if categories or languages:
            selected.append(c)
    elif country in KIDS_COUNTRIES and any("kid" in cat.lower() for cat in categories):
        selected.append(c)

unique = {}
for c in selected:
    unique[c["url"]] = c

channels = list(unique.values())[:MAX_CHANNELS]
print(f"Selected {len(channels)} channels for playlist.")

with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for c in channels:
        country = (c.get("country") or "").upper()
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

combined_epg = ""
for country_code, epg_url in EPG_SOURCES.items():
    try:
        print(f"Fetching EPG for {country_code}...")
        r = requests.get(epg_url, timeout=30)
        combined_epg += r.text
        print(f"Added EPG for {country_code}")
    except Exception as e:
        print(f"Failed to fetch EPG for {country_code}: {e}")

with open(EPG_OUTPUT, "w", encoding="utf-8") as f:
    f.write(combined_epg)

print("EPG file created.")
