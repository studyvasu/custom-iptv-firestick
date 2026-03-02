import requests

CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# Regional EPG files (US + India)
EPG_US = "https://iptv-org.github.io/epg/guides/us.xml"
EPG_IN = "https://iptv-org.github.io/epg/guides/in.xml"

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
    "cooking"
]

INDIA_LANGUAGES = ["hin", "tel"]
INDIA_CATEGORIES = ["travel", "cooking", "kids", "education"]

KIDS_COUNTRIES = ["UK", "AU"]  # UK & Australia kids channels


def valid(channel):
    return (
        channel.get("url")
        and not channel.get("is_nsfw")
        and channel.get("status") != "offline"
    )


print("Fetching channels...")
try:
    response = requests.get(CHANNELS_API, timeout=30)
    response.raise_for_status()
    data = response.json()
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
    if country == "US":
        if any(cat in US_CATEGORIES for cat in categories):
            selected.append(c)

    # India filter
    elif country == "IN":
        if any(lang in INDIA_LANGUAGES for lang in languages) or any(
            cat in INDIA_CATEGORIES for cat in categories
        ):
            selected.append(c)

    # UK & AU kids filter
    elif country in KIDS_COUNTRIES:
        if "kids" in categories:
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
        country = c.get("country")
        categories = c.get("categories", [])
        languages = c.get("languages", [])

        # Smart grouping
        if country == "US":
            if "movies" in categories:
                group = "US - Movies"
            elif "kids" in categories:
                group = "US - Kids"
            elif "business" in categories:
                group = "US - Business"
            elif "travel" in categories:
                group = "US - Travel"
            elif "music" in categories:
                group = "US - Music"
            elif "documentary" in categories:
                group = "US - Documentary"
            elif "education" in categories:
                group = "US - Education"
            elif "cooking" in categories:
                group = "US - Cooking"
            else:
                group = "US - Other"

        elif country == "IN":
            if "hin" in languages:
                group = "India - Hindi"
            elif "tel" in languages:
                group = "India - Telugu"
            elif "kids" in categories:
                group = "India - Kids"
            elif "education" in categories:
                group = "India - Education"
            elif "travel" in categories:
                group = "India - Travel"
            elif "cooking" in categories:
                group = "India - Cooking"
            else:
                group = "India - Other"

        elif country == "UK" and "kids" in categories:
            group = "UK - Kids"
        elif country == "AU" and "kids" in categories:
            group = "Australia - Kids"
        else:
            group = "Other"

        f.write(
            f'#EXTINF:-1 tvg-id="{c.get("id","")}" '
            f'tvg-name="{c.get("name","")}" '
            f'tvg-logo="{c.get("logo","")}" '
            f'group-title="{group}",{c.get("name","")}\n'
            f'{c.get("url")}\n'
        )

print("Downloading US + India EPG...")
epg_content = ""

for epg_url, region in [(EPG_US, "US"), (EPG_IN, "India")]:
    try:
        r = requests.get(epg_url, timeout=60)
        r.raise_for_status()
        epg_content += r.text
        print(f"{region} EPG added.")
    except:
        print(f"{region} EPG failed (continuing).")

# Always write epg.xml (even empty)
with open(EPG_OUTPUT, "w", encoding="utf-8") as f:
    f.write(epg_content)
print("EPG file created.")

print("Done.")
