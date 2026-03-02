import requests
import xml.etree.ElementTree as ET

# IPTV.org API
CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# External XMLTV sources (must exist in the repo)
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

PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"
MAX_CHANNELS = 400

def valid(channel):
    return channel.get("url") and not channel.get("is_nsfw") and channel.get("status") != "offline"

# --- Step 1: Fetch channels ---
print("Fetching channels...")
channels_resp = requests.get(CHANNELS_API, timeout=30)
channels_data = channels_resp.json()

selected = []
for c in channels_data:
    if not valid(c):
        continue

    country = (c.get("country") or "").lower()
    categories = c.get("categories") or []

    # US channels
    if country in ["us", "united states"]:
        selected.append(c)

    # India channels
    elif country in ["in", "india"]:
        selected.append(c)

    # UK/AU kids channels
    elif country in ["uk", "united kingdom", "au", "australia"]:
        if any("kid" in cat.lower() for cat in categories):
            selected.append(c)

# Deduplicate by URL
unique = {c["url"]: c for c in selected}
channels = list(unique.values())[:MAX_CHANNELS]

print(f"Selected {len(channels)} channels for playlist")

# --- Step 2: Write firestick.m3u ---
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

# --- Step 3: Fetch and filter EPG ---
print("Fetching and filtering EPG files...")
playlist_ids = set(c.get("id","") for c in channels if c.get("id"))
playlist_names = set(c.get("name","").lower() for c in channels)

epg_root = ET.Element("tv")

for country, urls in EPG_URLS.items():
    for url in urls:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            tree = ET.fromstring(r.content)

            # Filter only channels in playlist
            for chan in tree.findall("channel"):
                chan_id = chan.get("id","")
                chan_name = (chan.find("display-name").text if chan.find("display-name") is not None else "").lower()
                if chan_id in playlist_ids or chan_name in playlist_names:
                    epg_root.append(chan)

            for prog in tree.findall("programme"):
                prog_chan = prog.get("channel","")
                # Match by tvg-id or tvg-name
                if prog_chan in playlist_ids or prog_chan.lower() in playlist_names:
                    epg_root.append(prog)

            print(f"Processed EPG from {url}")

        except Exception as e:
            print(f"Failed to fetch EPG {url}: {e}")

# Write filtered EPG
tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered EPG written.")
print("Done.")
