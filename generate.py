import requests
import re
import xml.etree.ElementTree as ET

# COUNTRY PLAYLIST URLS FROM IPTV-ORG
COUNTRY_PLAYLISTS = {
    "US": "https://iptv-org.github.io/iptv/countries/us.m3u",
    "UK": "https://iptv-org.github.io/iptv/countries/uk.m3u",
    "IN": "https://iptv-org.github.io/iptv/countries/in.m3u",
    "AU": "https://iptv-org.github.io/iptv/countries/au.m3u",
}

# EPG URLs (must exist — only some available)
EPG_URLS = [
    "https://raw.githubusercontent.com/globetvapp/epg/main/India/india1.xml",
    "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia1.xml",
]

PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"

def parse_m3u(url):
    """Parse an IPTV.org M3U playlist into stream entries."""
    print(f"Downloading playlist {url} ...")
    r = requests.get(url, timeout=30)
    lines = r.text.splitlines()
    entries = []
    info = {}
    for line in lines:
        if line.startswith("#EXTINF"):
            info = {}
            m = re.search(r'tvg-id="([^"]*)" tvg-name="([^"]*)" tvg-logo="([^"]*)",(.+)', line)
            if m:
                info["tvg_id"], info["tvg_name"], info["tvg_logo"], info["name"] = m.groups()
        elif line and not line.startswith("#"):
            if info:
                info["url"] = line
                entries.append(info.copy())
                info = {}
    return entries

# --- COMBINE ALL COUNTRY STREAMS ---
all_entries = []
for country, url in COUNTRY_PLAYLISTS.items():
    try:
        entries = parse_m3u(url)
        print(f"Got {len(entries)} entries from {country}")
        all_entries.extend(entries)
    except Exception as e:
        print(f"Failed to fetch {country} playlist: {e}")

# Write combined playlist
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for e in all_entries:
        f.write(
            f'#EXTINF:-1 tvg-id="{e.get("tvg_id","")}" '
            f'tvg-name="{e.get("tvg_name","")}" '
            f'tvg-logo="{e.get("tvg_logo","")}",{e.get("name","")}\n'
            f'{e.get("url")}\n'
        )
print("Combined firestick.m3u written.")

# --- BUILD FILTERED EPG ---
print("Downloading EPG files ...")
epg_root = ET.Element("tv")

playlist_ids = set(e.get("tvg_id","") for e in all_entries)
playlist_names = set(e.get("tvg_name","").lower() for e in all_entries)

for epg_url in EPG_URLS:
    try:
        r = requests.get(epg_url, timeout=30)
        r.raise_for_status()
        doc = ET.fromstring(r.content)

        for chan in doc.findall("channel"):
            chan_id = chan.get("id","")
            name_elem = chan.find("display-name")
            name = name_elem.text.lower() if name_elem is not None else ""
            if chan_id in playlist_ids or name in playlist_names:
                epg_root.append(chan)

        for prog in doc.findall("programme"):
            if prog.get("channel","") in playlist_ids or prog.get("channel","").lower() in playlist_names:
                epg_root.append(prog)

        print(f"Added EPG from {epg_url}")

    except Exception as e:
        print(f"EPG fetch failed for {epg_url}: {e}")

tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered epg.xml written.")
