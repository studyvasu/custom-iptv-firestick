import requests
import re
import xml.etree.ElementTree as ET

# -------------------------------
# Country playlists (US, UK, AU)
# -------------------------------
COUNTRY_PLAYLISTS = {
    "US": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "UK": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u",
    "AU": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/au.m3u",
}

# -------------------------------
# Language playlists for India and English
# -------------------------------
LANG_PLAYLISTS = {
    "Hindi": "https://iptv-org.github.io/iptv/languages/hin.m3u",
    "Telugu": "https://iptv-org.github.io/iptv/languages/tel.m3u",
    "English": "https://iptv-org.github.io/iptv/languages/eng.m3u",
}

# -------------------------------
# EPG URLs
# -------------------------------
EPG_URLS = [
    "https://raw.githubusercontent.com/globetvapp/epg/main/Usa/usa3.xml",
    "https://raw.githubusercontent.com/globetvapp/epg/main/Usa/usa4.xml",
    "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom1.xml",
    "https://raw.githubusercontent.com/globetvapp/epg/main/India/india1.xml",
    "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia1.xml",
]

PLAYLIST_OUTPUT = "firestick.m3u"
PLAYLIST_LANG_OUTPUT = "firestick-lang.m3u"
EPG_OUTPUT = "epg.xml"

# -------------------------------
# General category mapping (enhanced)
# -------------------------------
CATEGORY_MAP = {
    "news": "News",
    "movie": "Movies",
    "films": "Movies",
    "kids": "Kids",
    "cartoon": "Kids",
    "music": "Music",
    "travel": "Travel",
    "tour": "Travel",
    "cook": "Cooking",
    "cooking": "Cooking",
    "food": "Cooking",
    "recipe": "Cooking",
    "kitchen": "Cooking",
    "chef": "Cooking",
    "baking": "Cooking",
    "grill": "Cooking",
    "bbq": "Cooking",
    "doc": "Documentary",
    "documentary": "Documentary",
    "education": "Education",
    "learning": "Education",
    "sports": "Sports",
    "soccer": "Sports",
    "football": "Sports",
    "nba": "Sports",
    "cricket": "Sports",
    "hockey": "Sports",
    "tennis": "Sports",
    "golf": "Sports",
    "formula 1": "Sports",
    "wwe": "Sports",
}

# -------------------------------
# Kids channels override
# -------------------------------
KIDS_CHANNELS = ["cartoon network", "pogo", "nick", "disney channel", "baby tv"]

# -------------------------------
# Allowed countries
# -------------------------------
ALLOWED_COUNTRIES = {"US", "GB", "AU"}  # India handled separately

# -------------------------------
# Helper: normalize text for matching
# -------------------------------
def normalize(text):
    return re.sub(r'\W+', '', text).lower() if text else ""

# -------------------------------
# Assign category (enhanced)
# -------------------------------
def assign_category(name, country, tvg_name=""):
    lname = (name + " " + tvg_name).lower()
    category = "Other"

    # Check for sports
    if any(kw in lname for kw in CATEGORY_MAP if CATEGORY_MAP[kw] == "Sports"):
        category = "Sports"
    else:
        # General category matching
        for kw, cat in CATEGORY_MAP.items():
            if kw in lname:
                category = cat
                break

    # US filter: skip foreign-language channels
    if country == "US":
        if any(x in lname for x in ["afghan", "pashto", "persian"]):
            return None
        if not any(k in lname for k in CATEGORY_MAP.keys()):
            return None

    # Force Kids channels
    if "disney" in lname or "nick" in lname or any(k in lname for k in KIDS_CHANNELS):
        category = "Kids"

    return category

# -------------------------------
# Parse M3U safely
# -------------------------------
def parse_m3u(url, country=None):
    print(f"Downloading playlist {url} ...")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    lines = r.text.splitlines()
    entries = []

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            tvg_id = tvg_name = tvg_logo = ""
            name = ""
            m = re.search(r'tvg-id="([^"]*)"', line)
            if m: tvg_id = m.group(1)
            m = re.search(r'tvg-name="([^"]*)"', line)
            if m: tvg_name = m.group(1)
            m = re.search(r'tvg-logo="([^"]*)"', line)
            if m: tvg_logo = m.group(1)
            if "," in line:
                name = line.split(",")[-1].strip()
            info = {"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "name": name}
        elif line and not line.startswith("#"):
            if 'info' in locals():
                info["url"] = line
                if country:
                    category = assign_category(info["name"], country, info["tvg_name"])
                    if category is None:
                        continue
                else:
                    category = assign_category(info["name"], None, info["tvg_name"])
                info["category"] = category
                if not info["tvg_id"]:
                    info["tvg_id"] = normalize(info["name"])
                if not info["tvg_name"]:
                    info["tvg_name"] = info["name"]
                entries.append(info.copy())
                del info
    print(f"Parsed {len(entries)} entries")
    return entries

# -------------------------------
# Combine playlists
# -------------------------------
all_entries = []
lang_entries = []

# Country-specific playlists
for country, url in COUNTRY_PLAYLISTS.items():
    try:
        entries = parse_m3u(url, country)
        all_entries.extend(entries)
        print(f"{len(entries)} entries added from {country}")
    except Exception as e:
        print(f"Failed {country}: {e}")

# Language-specific playlists
for lang, url in LANG_PLAYLISTS.items():
    try:
        entries = parse_m3u(url)
        for e in entries:
            e["category"] = f"{lang}/{e['category']}"
        all_entries.extend(entries)
        lang_entries.extend(entries)
        print(f"{len(entries)} entries added from {lang}")
    except Exception as e:
        print(f"Failed {lang}: {e}")

# -------------------------------
# Write firestick.m3u
# -------------------------------
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for e in all_entries:
        f.write(f'#EXTINF:-1 tvg-id="{e["tvg_id"]}" tvg-name="{e["tvg_name"]}" tvg-logo="{e["tvg_logo"]}" group-title="{e["category"]}",{e["name"]}\n{e["url"]}\n')
print(f"{PLAYLIST_OUTPUT} written with {len(all_entries)} channels.")

# -------------------------------
# Write firestick-lang.m3u
# -------------------------------
with open(PLAYLIST_LANG_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for e in lang_entries:
        f.write(f'#EXTINF:-1 tvg-id="{e["tvg_id"]}" tvg-name="{e["tvg_name"]}" tvg-logo="{e["tvg_logo"]}" group-title="{e["category"]}",{e["name"]}\n{e["url"]}\n')
print(f"{PLAYLIST_LANG_OUTPUT} written with {len(lang_entries)} language-based channels.")

# -------------------------------
# Filtered EPG (robust matching)
# -------------------------------
print("Downloading and filtering EPG ...")
epg_root = ET.Element("tv")
playlist_ids = [normalize(e["tvg_id"]) for e in all_entries]
playlist_names = [normalize(e["tvg_name"]) for e in all_entries]

for epg_url in EPG_URLS:
    try:
        r = requests.get(epg_url, timeout=30)
        r.raise_for_status()
        doc = ET.fromstring(r.content)
        for chan in doc.findall("channel"):
            dn = chan.find("display-name")
            epg_name_norm = normalize(dn.text if dn is not None else "")
            epg_id_norm = normalize(chan.get("id", ""))

            # Include channel if normalized ID or name matches playlist
            if epg_id_norm in playlist_ids or epg_name_norm in playlist_names:
                epg_root.append(chan)
    except Exception as e:
        print(f"Failed to process EPG {epg_url}: {e}")

# Write filtered EPG to file
tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print(f"{EPG_OUTPUT} written with filtered channels.")
