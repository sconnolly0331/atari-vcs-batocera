# Atari VCS Batocera Setup

Configuration and automation scripts for an Atari VCS running Batocera 42.

## Hardware
- Atari VCS (AMD Ryzen / Radeon Vega 3)
- Batocera.linux 42
- Sinden lightguns
- Atari Game Controller
- Raspberry Pi client for LAN netplay

## Scripts

### `scripts/rom-sorter.py`
Automatically sorts ROM files dropped into `/userdata/roms/_incoming/` into the correct system folders. Supports:
- 60+ system extension mappings (NES, SNES, N64, GBA, PS1/2, Saturn, Dreamcast, etc.)
- ZIP/7Z archive inspection (peeks inside to classify by internal extension)
- Disc image header detection (Saturn, Dreamcast, PS1/2, 3DO)
- Filename heuristics fallback
- Unclassifiable files go to `_incoming/_unknown/`

### `scripts/rom-watcher.sh`
`inotifywait` daemon that monitors `_incoming/` and triggers the sorter instantly when any file lands. Started at boot via `custom.sh`. Ignores partial downloads (`.part`, `.crdownload`, `.tmp`).

### `scripts/rom-scraper.py`
Calls the ScreenScraper API to fetch artwork (screenshot, box art, marquee) for any games missing images across all system gamelists. Safe to re-run — skips games that already have artwork.

Requires ScreenScraper credentials — fill in `YOUR_DEV_ID`, `YOUR_DEV_PASS`, `YOUR_SCREENSCRAPER_USERNAME`, `YOUR_SCREENSCRAPER_PASSWORD`.

### `scripts/custom.sh`
Runs at every Batocera boot. Sets AMD GPU env vars and starts the ROM watcher.

### `scripts/netplay-client-setup.sh`
Auto-detecting netplay client setup script for the second machine (Raspberry Pi). Detects Batocera, RetroPie, or bare RetroArch and writes the correct config.

## Setup

### ROM Auto-Sorter
```bash
# Copy scripts to system
cp scripts/rom-sorter.py /userdata/system/
cp scripts/rom-watcher.sh /userdata/system/
cp scripts/custom.sh /userdata/system/
chmod +x /userdata/system/rom-sorter.py /userdata/system/rom-watcher.sh

# Create drop zone
mkdir -p /userdata/roms/_incoming/_unknown

# Start watcher (also starts automatically at boot)
/userdata/system/rom-watcher.sh &
```

Drop any ROM into `/userdata/roms/_incoming/` — it moves itself to the right folder within a second.

### ROM Scraper
```bash
# Fill in credentials first
nano /userdata/system/rom-scraper.py

# Run
python3 /userdata/system/rom-scraper.py
```

Log: `/userdata/system/logs/rom-scraper.log`

### LAN Netplay
This machine (`192.168.68.57`) is configured as **Player 1 / Host**.

The Raspberry Pi at `192.168.68.55` is the client. To set it up:
```bash
# On the Pi
sudo bash netplay-client-setup.sh
```

**To play:**
1. On the VCS: long-press a game in ES → Start Netplay as Host
2. On the Pi: same game → Start Netplay as Client (or `retroarch --connect 192.168.68.57`)

## Notes
- 7z inspection uses `7zr` not `7z` — the `7z` binary has a broken shared lib on this Batocera build
- Bezel Project installed for 23 systems
- Sinden lightguns work on PS2, Saturn, Dreamcast, MAME, Model 2/3, Namco 246, Lindbergh
- Lindbergh and Singe games are not on ScreenScraper — no artwork available
