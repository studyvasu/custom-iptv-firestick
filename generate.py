import requests
import xml.etree.ElementTree as ET

# Official channel list
CHANNELS_API = "https://iptv-org.github.io/api/channels.json"

# Real EPG XMLTV URLs (must exist on GitHub)
EPG_URLS = {
    "US": [
        "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedStates/usa3.xml",
        "https://raw.githubusercontent.com/globetvapp/epg/main/UnitedStates/usa4.xml"
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

# filter function
def valid(channel):
    return channel.get("url") and not channel.get("is_nsfw") and channel.get("status") != "offline"

print("Fetching channel list...")
r = requests.get(CHANNELS_API, timeout=30)
channels_data = r.json()

# filter channels by country code
filtered = []
for c in channels_data:
    if not valid(c):
        continue
    country = (c.get("country") or "").upper()
    if country in ["US", "IN", "UK", "AU"]:
        filtered.append(c)

unique = {c["url"]: c for c in filtered}
channels = list(unique.values())[:MAX_CHANNELS]
print(f"Selected {len(channels)} channels.")

# write playlist
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

# build EPG
print("Downloading EPG files...")
epg_root = ET.Element("tv")

play_ids = set(c.get("id","") for c in channels)
play_names = set(c.get("name","").lower() for c in channels)

for urls in EPG_URLS.values():
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            tree = ET.fromstring(resp.content)

            # include only channels in playlist
            for chan in tree.findall("channel"):
                chan_id = chan.get("id","")
                dn = chan.find("display-name")
                name = dn.text.lower() if dn is not None else ""
                if chan_id in play_ids or name in play_names:
                    epg_root.append(chan)

            for prog in tree.findall("programme"):
                if prog.get("channel","") in play_ids or prog.get("channel","").lower() in play_names:
                    epg_root.append(prog)

            print(f"Added from EPG source: {url}")

        except Exception as e:
            print(f"Failed: {url} -> {e}")

tree = ET.ElementTree(epg_root)
tree.write(EPG_OUTPUT, encoding="utf-8", xml_declaration=True)
print("Filtered EPG written.")
