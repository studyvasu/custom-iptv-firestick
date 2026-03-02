import requests
import re
import xml.etree.ElementTree as ET

# -------------------------------
# M3U URLs
# -------------------------------
COUNTRY_PLAYLISTS = {
    "US": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "UK": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u",
    "IN": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/in.m3u",
    "AU": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/au.m3u",
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
EPG_OUTPUT = "epg.xml"

# -------------------------------
# Category mapping
# -------------------------------
CATEGORY_MAP = {
    "news": "News",
    "movie": "Movies",
    "films": "Movies",
    "kids": "Kids",
    "cartoon": "Kids",
    "music": "Music",
    "travel": "Travel",
    "cook": "Cooking",
    "food": "Cooking",
    "doc": "Documentary",
    "education": "Education",
}

def assign_category(name):
    lname = name.lower()
    for kw, cat in CATEGORY_MAP.items():
        if kw in lname:
            return cat
    return "Other"

# -------------------------------
# Parse M3U safely
# -------------------------------
def parse_m3u(url):
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
                info["category"] = assign_category(info["name"])
                # generate id/name if missing
                if not info["tvg_id"]:
                    info["tvg_id"] = re.sub(r'\W+', '', info["name"]).lower()
                if not info["tvg_name"]:
                    info["tvg_name"] = info["name"]
                entries.append(info.copy())
                del info

    print(f"Parsed {len(entries)} entries")
    return entries

# -------------------------------
# Combine all playlists
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
# Write firestick.m3u with group-title
# -------------------------------
with open(PLAYLIST_OUTPUT, "w", encoding="utf-8") as f:
    f.write('#EXTM3U url-tvg="epg.xml"\n')
    for e in all_entries:
        f.write(
            f'#EXTINF:-1 tvg-id="{e["tvg_id"]}" '
            f'tvg-name="{e["tvg_name"]}" '
            f'tvg-logo="{e["tvg_logo"]}" '
            f'group-title="{e["category"]}",{e["name"]}\n'
            f'{e["url"]}\n'
        )
print(f"firestick.m3u written with {len(all_entries)} channels.")

# -------------------------------
# Filtered EPG with bi-directional partial match
# -------------------------------
print("Downloading and filtering EPG files ...")
epg_root = ET.Element("tv")
playlist_ids = [e["tvg_id"].lower() for e in all_entries]
playlist_names = [e["tvg_name"].lower() for e in all_entries]

for epg_url in EPG_URLS:
    try:
        r = requests.get(epg_url, timeout=30)
        r.raise_for_status()
        doc = ET.fromstring(r.content)

        # Channels
        for chan in doc.findall("channel"):
            dn = chan.find("display-name")
            epg_name = dn.text.lower() if dn is not None else ""
            epg_id = chan.get("id","").lower()
            # bi-directional partial match
            if any(pname in epg_name or epg_name in pname or pid in epg_id or epg_id in pid
                   for pname, pid in zip(playlist_names, playlist_ids)):
                epg_root.append(chan)

        # Programmes
        for prog in doc.findall("programme"):
            prog_chan = prog.get("channel","").lower()
            if any(pname in prog_chan or prog_chan in pname or pid in prog_chan or prog_chan in pid
                   for pname, pid in zip(playlist_names, playlist_ids)):
                epg_root.append(prog)

        print(f"EPG added from {epg_url}")

    except Exception as e:
        print(f"EPG fetch failed for {epg_url}: {e}")

ET.ElementTree(epg_root).write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered epg.xml written. Done.")
