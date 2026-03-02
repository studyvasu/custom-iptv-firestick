import requests
import re
import xml.etree.ElementTree as ET

# -------------------------------
# Raw M3U URLs from iptv-org repo (actual streams)
# -------------------------------
COUNTRY_PLAYLISTS = {
    "US": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "UK": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u",
    "IN": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/in.m3u",
    "AU": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/au.m3u",
}

# -------------------------------
# EPG URLs (Globetvapp GitHub)
# -------------------------------
EPG_URLS = [
    # United States
    "https://raw.githubusercontent.com/globetvapp/epg/main/Usa/usa3.xml",
    "https://raw.githubusercontent.com/globetvapp/epg/main/Usa/usa4.xml",
    # United Kingdom
    "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom1.xml",
    # India
    "https://raw.githubusercontent.com/globetvapp/epg/main/India/india1.xml",
    # Australia
    "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia1.xml",
]

PLAYLIST_OUTPUT = "firestick.m3u"
EPG_OUTPUT = "epg.xml"

# -------------------------------
# Helper: Parse IPTV M3U playlist
# -------------------------------
def parse_m3u(url):
    print(f"Downloading playlist {url} ...")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
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

# -------------------------------
# Combine all country playlists
# -------------------------------
all_entries = []
for country, url in COUNTRY_PLAYLISTS.items():
    try:
        entries = parse_m3u(url)
        print(f"Found {len(entries)} entries for {country}")
        all_entries.extend(entries)
    except Exception as e:
        print(f"Failed to fetch {country} playlist: {e}")

# -------------------------------
# Write combined firestick.m3u
# -------------------------------
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for e in all_entries:
        f.write(
            f'#EXTINF:-1 tvg-id="{e.get("tvg_id","")}" '
            f'tvg-name="{e.get("tvg_name","")}" '
            f'tvg-logo="{e.get("tvg_logo","")}",{e.get("name","")}\n'
            f'{e.get("url")}\n'
        )
print(f"firestick.m3u written with {len(all_entries)} channels.")

# -------------------------------
# Build filtered EPG
# -------------------------------
print("Downloading and filtering EPG files ...")
epg_root = ET.Element("tv")
playlist_ids = set(e.get("tvg_id","") for e in all_entries)
playlist_names = set(e.get("tvg_name","").lower() for e in all_entries)

for epg_url in EPG_URLS:
    try:
        r = requests.get(epg_url, timeout=30)
        r.raise_for_status()
        doc = ET.fromstring(r.content)

        # Filter channels
        for chan in doc.findall("channel"):
            chan_id = chan.get("id","")
            dn = chan.find("display-name")
            name = dn.text.lower() if dn is not None else ""
            if chan_id in playlist_ids or name in playlist_names:
                epg_root.append(chan)

        # Filter programmes
        for prog in doc.findall("programme"):
            if prog.get("channel","") in playlist_ids or prog.get("channel","").lower() in playlist_names:
                epg_root.append(prog)

        print(f"EPG added from {epg_url}")

    except Exception as e:
        print(f"EPG fetch failed for {epg_url}: {e}")

ET.ElementTree(epg_root).write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered epg.xml written.")
print("Done.")
