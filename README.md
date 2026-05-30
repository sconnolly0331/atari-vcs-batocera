# Atari VCS Batocera — Retro Gaming Hub

Automation scripts and configuration for an **Atari VCS running Batocera 42**, set up as a local-network multiplayer retro gaming hub with a Raspberry Pi as the second-player client.

---

## Hardware

| Device | Role |
|--------|------|
| Atari VCS (AMD Ryzen / Radeon Vega 3) | Host — Player 1, game library, scraper |
| Raspberry Pi | Client — Player 2 via LAN netplay |
| Sinden Lightguns (×2) | Connected to VCS via USB |
| Atari Game Controller | P1 controller |

- **Batocera.linux 42**
- AMD Radeon Vega 3 — OpenGL 4.6, Vulkan (RADV)
- Host LAN IP: `192.168.68.57`

---

## Systems & Emulators

| System | Emulator | Notes |
|--------|----------|-------|
| PS2 | PCSX2 (Vulkan) | Light gun games confirmed |
| Dreamcast | Flycast | Crazy Taxi, Soul Calibur |
| Saturn | Mednafen/Beetle | Multi-disc via .m3u |
| PS1 | DuckStation | Multi-disc via .m3u |
| PC Engine | Beetle PCE | |
| NES | Mesen / FBNeo | |
| SNES | Snes9x | Best for netplay |
| N64 | Mupen64Plus | |
| GBA | mGBA | |
| Mega Drive | Genesis Plus GX | |
| Jaguar | Virtual Jaguar | |
| Model 2 | m2emulator (Wine) | Not netplay-compatible |
| Model 3 | Supermodel | Not netplay-compatible |
| Daphne / Singe | Hypseus | LaserDisc games |
| MAME | MAME | 61+ arcade games |
| FBNeo | FBNeo | 26+ arcade games |
| Atomiswave / Naomi | FBNeo | |
| Namco 246 | MAME | Time Crisis 4, Vampire Night |
| Atari 2600 / 7800 | Stella / ProSystem | |
| 3DO | 4DO | |

> **Note:** Model 2 and Model 3 run via Wine/native binary — they are **not compatible with RetroArch netplay**. Use SNES, NES, MAME, FBNeo, or PS1 for multiplayer sessions.

---

## LAN Multiplayer (Netplay)

### How it works

RetroArch netplay syncs emulator state across the network in real time. Both machines must:
- Run the **same game ROM** (identical file)
- Use the **same RetroArch core** (emulator)
- Be on the **same LAN** (or use a relay for internet play)

The VCS is always **Player 1 / Host**. The Pi (or any second machine) joins as **Player 2 / Client**.

---

### Step 1 — Set up the client machine (Pi)

Run this on the Pi (one time only):

```bash
curl -sL https://raw.githubusercontent.com/sconnolly0331/atari-vcs-batocera/main/scripts/netplay-client-setup.sh | sudo bash
```

The script auto-detects whether the Pi is running **Batocera**, **RetroPie**, or bare **RetroArch** and writes the correct config. It sets:
- Host IP: `192.168.68.57`
- Port: `55435`
- Player name: `Player 2`

---

### Step 2 — Start a game as Host (VCS)

1. Open **EmulationStation** on the VCS
2. Browse to a game
3. **Long-press** the confirm button on the game title
4. Choose **Start Netplay as Host**
5. Wait — the game will launch and pause at the netplay lobby

---

### Step 3 — Join as Client (Pi)

**If Pi is running Batocera or RetroPie (EmulationStation):**
1. Navigate to the same game
2. Long-press → **Start Netplay as Client**

**If Pi is running bare RetroArch:**
1. Main Menu → Netplay → Connect to Netplay Host
2. Enter IP: `192.168.68.57`, Port: `55435`

**Command-line join (any platform):**
```bash
retroarch --connect 192.168.68.57 --port 55435 -L /path/to/core.so /path/to/rom
```

---

### Recommended games for netplay

These cores are lightweight and netplay reliably:

| System | Core | Good multiplayer games |
|--------|------|----------------------|
| SNES | Snes9x | Street Fighter II, Super Bomberman, Mario Kart |
| NES | Mesen | Contra, Double Dragon, Tecmo Bowl |
| MAME | MAME | Street Fighter, Metal Slug, NBA Jam |
| FBNeo | FBNeo | Any arcade fighter |
| Mega Drive | Genesis Plus GX | Streets of Rage, Mortal Kombat |
| GBA | mGBA | Mario Kart, Street Fighter Alpha 3 |

---

### Troubleshooting netplay

| Problem | Fix |
|---------|-----|
| Client can't connect | Check both machines are on same LAN; confirm host launched first |
| Game desyncs immediately | ROMs must be identical — copy from VCS share `\192.168.68.57\share` |
| Wrong core on client | Client must use same core as host — check RetroArch → Information → Core Information |
| VCS froze launching | Model 2 / Model 3 are not RetroArch cores — they can't netplay, use a different system |
| Player tags appear but no input | Controller not mapped on client — RetroArch → Settings → Input → Port 2 |

---

## ROM Auto-Sorter

Drop any ROM file into `/userdata/roms/_incoming/` and it automatically moves to the correct system folder within 1 second.

### How it works

1. `rom-watcher.sh` runs as a daemon (started at boot via `custom.sh`)
2. `inotifywait` fires the moment a file finishes writing
3. `rom-sorter.py` identifies the system by:
   - File extension (60+ mappings)
   - Archive inspection — peeks inside ZIP/7Z for the real extension
   - Disc image header detection (Saturn, Dreamcast, PS1/2, 3DO)
   - Filename heuristics as a last resort
4. File moves to `/userdata/roms/<system>/`
5. Unclassifiable files go to `_incoming/_unknown/` for manual review

### Drop zone paths

| Path | Purpose |
|------|---------|
| `/userdata/roms/_incoming/` | Drop ROMs here |
| `/userdata/roms/_incoming/_unknown/` | Unrecognised files land here |

### Logs

```bash
tail -f /userdata/system/logs/rom-sorter.log
```

### Manual sort (one file)

```bash
python3 /userdata/system/rom-sorter.py /path/to/rom.zip
```

---

## ROM Scraper

Fetches artwork from **ScreenScraper** for any games missing images.

```bash
python3 /userdata/system/rom-scraper.py
```

- Scans all system `gamelist.xml` files
- Skips games that already have artwork
- Downloads: screenshot, box art, marquee
- Logs to `/userdata/system/logs/rom-scraper.log`

> The copy in this repo has credentials stripped. The live version on the VCS has real credentials from the ScreenScraper account in ES settings.

---

## Sync Scripts to GitHub

After making changes to any script on the VCS, push them back to this repo:

```bash
python3 /userdata/system/sync-to-github.sh
```

- Compares local files against repo by git blob SHA — only pushes changed files
- Strips credentials (ScreenScraper keys, WiFi password) before pushing

---

## Fresh Install / Setup on a New VCS

```bash
# 1. Clone the repo
cd /userdata/system
git clone https://github.com/sconnolly0331/atari-vcs-batocera.git setup
cd setup

# 2. Copy scripts
cp scripts/*.py scripts/*.sh /userdata/system/
chmod +x /userdata/system/*.sh /userdata/system/*.py

# 3. Create drop zones
mkdir -p /userdata/roms/_incoming/_unknown
mkdir -p /userdata/system/logs

# 4. Apply boot script
cp scripts/custom.sh /userdata/system/custom.sh

# 5. Add ScreenScraper credentials to rom-scraper.py

# 6. Reboot — watcher starts automatically
```

---

## Notes

- `7zr` is used instead of `7z` — the `7z` binary has a broken shared library on this Batocera build
- Bezel Project installed for 23 systems (bezels auto-apply per game with system fallback)
- Sinden lightguns work on PS2, Saturn, Dreamcast, MAME, Model 2/3, Namco 246, Lindbergh
- Lindbergh and Singe games are not indexed on ScreenScraper — no artwork available
- Model 2 emulator runs via Wine bottle at `/userdata/system/wine-bottles/model2/`
