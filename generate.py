import requests
import xml.etree.ElementTree as ET

CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# Only include EPG files that exist on GitHub
EPG_URLS = {
    "US": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/Usa/usa3.xml",
        "https://raw.githubusercontent.com/globetvapp/epg/main/Usa/usa4.xml"
    ],
    "IN": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/India/india1.xml"
    ],
    "UK": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom1.xml"
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

print("Fetching channels from IPTV.org...")
resp = requests.get(CHANNELS_API, timeout=30)
channels_data = resp.json()

# --- Filter channels ---
selected = []
for c in channels_data:
    if not valid(c):
        continue
    country = (c.get("country") or "").lower()
    categories = [cat.lower() for cat in (c.get("categories") or [])]

    # US/India all channels
    if country in ["us", "usa", "in", "india"]:
        selected.append(c)
    # UK/AU kids channels
    elif country in ["uk", "united kingdom", "au", "australia"]:
        if any("kid" in cat for cat in categories):
            selected.append(c)

# Deduplicate by URL
unique = {c["url"]: c for c in selected}
channels = list(unique.values())[:MAX_CHANNELS]
print(f"Selected {len(channels)} channels for playlist.")

# --- Write firestick.m3u ---
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

# --- Fetch and filter EPG ---
print("Downloading EPG files...")
epg_root = ET.Element("tv")
playlist_ids = set(c.get("id","") for c in channels)
playlist_names = set(c.get("name","").lower() for c in channels)

for country, urls in EPG_URLS.items():
    for url in urls:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            tree = ET.fromstring(r.content)

            for chan in tree.findall("channel"):
                chan_id = chan.get("id","")
                dn = chan.find("display-name")
                name = dn.text.lower() if dn is not None else ""
                if chan_id in playlist_ids or name in playlist_names:
                    epg_root.append(chan)

            for prog in tree.findall("programme"):
                if prog.get("channel","") in playlist_ids or prog.get("channel","").lower() in playlist_names:
                    epg_root.append(prog)

            print(f"Added EPG from {url}")
        except Exception as e:
            print(f"Failed to fetch EPG {url}: {e}")

tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered EPG written.")
print("Done.")
