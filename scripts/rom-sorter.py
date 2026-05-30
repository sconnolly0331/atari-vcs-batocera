#!/usr/bin/env python3
"""
ROM Auto-Sorter for Batocera
Moves files dropped in /userdata/roms/_incoming/ to the correct system folder.
Usage: rom-sorter.py <filepath>
"""

import os
import sys
import shutil
import logging
import zipfile
import subprocess
import struct
from pathlib import Path

ROMS_BASE  = Path('/userdata/roms')
INCOMING   = ROMS_BASE / '_incoming'
UNKNOWN    = INCOMING / '_unknown'
LOG_FILE   = '/userdata/system/logs/rom-sorter.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)
log = logging.getLogger('rom-sorter')

# ---------------------------------------------------------------------------
# Extension → Batocera system (unambiguous mappings only)
# ---------------------------------------------------------------------------
EXT_MAP = {
    # Atari
    'a26': 'atari2600',
    'a52': 'atari5200',
    'a78': 'atari7800',
    'atr': 'atari800', 'xfd': 'atari800', 'dcm': 'atari800', 'cas': 'atari800',
    'jag': 'jaguar',   'j64': 'jaguar',
    'lnx': 'lynx',
    # Nintendo
    'nes': 'nes', 'fds': 'fds', 'unf': 'nes',
    'smc': 'snes', 'sfc': 'snes', 'swc': 'snes', 'fig': 'snes',
    'z64': 'n64',  'n64': 'n64', 'v64': 'n64',
    'gb':  'gb',
    'gbc': 'gbc',
    'gba': 'gba',
    'nds': 'nds',
    '3ds': '3ds', 'cia': '3ds',
    'wbfs': 'wii',
    'rvz':  'gamecube',
    'gcm':  'gamecube', 'nkit': 'gamecube',
    # Sega
    'md': 'megadrive', 'gen': 'megadrive', 'smd': 'megadrive',
    '32x': 'sega32x',
    'gg':  'gamegear',
    'sms': 'mastersystem',
    'sg':  'sg1000',
    'gdi': 'dreamcast',
    'cdi': 'dreamcast',
    # Sony
    'pbp': 'psp',
    # NEC
    'pce': 'pcengine',
    'sgx': 'supergrafx',
    # SNK
    'ngp': 'ngp',
    'ngc': 'ngpc',
    # Bandai
    'ws':  'wswan',
    'wsc': 'wswanc',
    # Other handhelds / consoles
    'vb':  'virtualboy',
    'vec': 'vectrex',
    'col': 'colecovision',
    'int': 'intellivision',
    'min': 'pokemini',
    'sv':  'supervision',
    'uze': 'uzebox',
    'tic': 'tic80',
    'arduboy': 'arduboy',
    # Commodore
    'd64': 'c64', 't64': 'c64', 'prg': 'c64',
    'p00': 'c64', 'g64': 'c64', 'x64': 'c64',
    'd81': 'c128', 'd71': 'c128',
    'adf': 'amiga500', 'hdf': 'amiga500',
    'lha': 'amiga500', 'ipf': 'amiga500',
    # Spectrum
    'sna': 'zxspectrum', 'tap': 'zxspectrum',
    'z80': 'zxspectrum', 'tzx': 'zxspectrum', 'rzx': 'zxspectrum',
    # Amstrad CPC
    'cpc': 'amstradcpc',
    # Atari ST
    'st':  'atarist', 'stx': 'atarist', 'msa': 'atarist',
    # MSX
    'mx1': 'msx1', 'mx2': 'msx2',
    # PC Engine CD
    'pce': 'pcengine',
    # ScummVM
    'scummvm': 'scummvm',
}

# ---------------------------------------------------------------------------
# Disc image: keyword hints in filename → system
# ---------------------------------------------------------------------------
DISC_HINTS = [
    ('(ps2)',          'ps2'),
    ('ps2',            'ps2'),
    ('playstation 2',  'ps2'),
    ('playstation2',   'ps2'),
    ('scus_', 'ps2'), ('slus_', 'ps2'), ('sles_', 'ps2'), ('sces_', 'ps2'),
    ('slpm_', 'ps2'), ('slps_', 'ps2'),
    ('(psx)',          'psx'),
    ('playstation',    'psx'),
    ('saturn',         'saturn'),
    ('(sat)',          'saturn'),
    ('dreamcast',      'dreamcast'),
    ('(dc)',           'dreamcast'),
    ('3do',            '3do'),
    ('sega cd',        'megacd'),
    ('mega cd',        'megacd'),
    ('megacd',         'megacd'),
    ('pc engine cd',   'pcenginecd'),
    ('pcenginecd',     'pcenginecd'),
    ('gamecube',       'gamecube'),
    ('(gc)',           'gamecube'),
    ('nintendo wii',   'wii'),
    ('(wii)',          'wii'),
    ('ps3',            'ps3'),
    ('ps4',            'ps4'),
    ('psp',            'psp'),
]

# ---------------------------------------------------------------------------
# ISO / disc header detection (reads first 32KB)
# ---------------------------------------------------------------------------
def detect_disc_system(path: Path) -> str | None:
    """Read disc image header to identify the platform."""
    try:
        with open(path, 'rb') as f:
            header = f.read(0x8200)  # 32KB + a bit
    except OSError:
        return None

    # Sega Saturn: sector 0 contains "SEGASATURN"
    if b'SEGASATURN' in header[:0x200]:
        return 'saturn'
    # Sega Mega-CD
    if b'SEGADISCSYSTEM' in header[:0x200] or b'SEGA_CD_ROM' in header[:0x200]:
        return 'megacd'
    # Dreamcast: sector 0 contains "SEGA SEGAKATANA" or "SEGADATADISC"
    if b'SEGA SEGAKATANA' in header[:0x100] or b'SEGADATADISC' in header[:0x100]:
        return 'dreamcast'
    # 3DO: "3DO" in system area
    if b'3DO' in header[:0x100] or b'\x01\x5A\x5A\x5A\x5A\x5A\x01' in header[:0x200]:
        return '3do'
    # PC Engine CD: look for "PC Engine CD-ROM"
    if b'PC Engine' in header[:0x200]:
        return 'pcenginecd'
    # PlayStation (PSX): system.cnf or PSX executable marker
    # ISO9660 volume descriptor starts at sector 16 (offset 0x8000)
    vol_desc = header[0x8000:0x8000+0x200]
    if b'CD-XA001' in vol_desc:
        # Could be PSX or PS2
        if b'SYSTEM.CNF' in header or b'BOOT2' in header or b'PS2' in header[0x8000:]:
            return 'ps2'
        return 'psx'
    if b'PLAYSTATION' in header[:0x200]:
        return 'psx'
    # Generic ISO9660 — try volume label
    label = header[0x8028:0x8048].decode('ascii', errors='replace').strip()
    label_lower = label.lower()
    if 'ps2' in label_lower or 'playstation 2' in label_lower:
        return 'ps2'
    if 'playstation' in label_lower:
        return 'psx'

    return None

# ---------------------------------------------------------------------------
# Parse .cue file — return system and list of referenced bin files
# ---------------------------------------------------------------------------
def parse_cue(cue_path: Path):
    """Return (system_or_None, [referenced_file_paths])."""
    bins = []
    try:
        with open(cue_path) as f:
            for line in f:
                line = line.strip()
                if line.upper().startswith('FILE '):
                    # FILE "name.bin" BINARY
                    parts = line.split('"')
                    if len(parts) >= 2:
                        bins.append(cue_path.parent / parts[1])
    except OSError:
        pass

    system = None
    for b in bins:
        if b.exists():
            system = detect_disc_system(b)
            if system:
                break
    if not system:
        system = guess_from_name(cue_path.stem)
    return system, bins

# ---------------------------------------------------------------------------
# Inspect archive contents for extension clues
# ---------------------------------------------------------------------------
def inspect_zip(path: Path) -> str | None:
    """Return a system name based on file extensions found inside the zip."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except Exception:
        return None
    return classify_internal_extensions(names, path.stem)

def inspect_7z(path: Path) -> str | None:
    """Return a system name based on file extensions found inside the 7z."""
    try:
        # Use 7zr (standalone, no shared-lib issues) with plain listing
        result = subprocess.run(
            ['7zr', 'l', str(path)],
            capture_output=True, text=True, timeout=30
        )
        names = []
        in_table = False
        for line in result.stdout.splitlines():
            if line.startswith('---'):
                in_table = not in_table
                continue
            if in_table and line.strip():
                # Columns: Date Time Attr Size Compressed Name
                parts = line.split()
                if len(parts) >= 6:
                    names.append(parts[-1])
    except Exception:
        return None
    return classify_internal_extensions(names, path.stem)

def classify_internal_extensions(names: list[str], archive_stem: str) -> str | None:
    """Given a list of filenames inside an archive, guess the system."""
    ext_counts: dict[str, int] = {}
    for name in names:
        ext = Path(name).suffix.lstrip('.').lower()
        if ext:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    # If a known unique extension is the majority, use it
    for ext, system in EXT_MAP.items():
        if ext_counts.get(ext, 0) > 0:
            return system

    # Internal .bin/.iso with no other clues → could be arcade (MAME) if tiny
    total_files = sum(ext_counts.values())
    rom_like = ext_counts.get('rom', 0) + ext_counts.get('bin', 0)
    if rom_like > 0 and total_files <= 5:
        return 'mame'  # likely arcade zip

    # Fall back to name heuristics
    return guess_from_name(archive_stem)

# ---------------------------------------------------------------------------
# Name-based heuristics (last resort)
# ---------------------------------------------------------------------------
def guess_from_name(name: str) -> str | None:
    lower = name.lower()
    for keyword, system in DISC_HINTS:
        if keyword in lower:
            return system
    return None

# ---------------------------------------------------------------------------
# Main sort logic for a single path (file or directory)
# ---------------------------------------------------------------------------
def sort_item(item: Path):
    if not item.exists():
        log.warning(f'Item no longer exists: {item}')
        return

    # Skip internal directories
    if item == UNKNOWN or item.parent == UNKNOWN:
        return

    log.info(f'Sorting: {item.name}')

    system = None

    if item.is_dir():
        # Treat whole directory as a disc set; classify by contents
        children = list(item.rglob('*'))
        names = [str(c.relative_to(item)) for c in children if c.is_file()]
        system = classify_internal_extensions(names, item.name)
        if not system:
            system = guess_from_name(item.name)

    else:
        ext = item.suffix.lstrip('.').lower()

        # 1. Unique extension mapping
        if ext in EXT_MAP:
            system = EXT_MAP[ext]

        # 2. .zip — inspect contents
        elif ext == 'zip':
            system = inspect_zip(item)

        # 3. .7z — inspect contents
        elif ext == '7z':
            system = inspect_7z(item)

        # 4. .cue — parse for bin files, detect via header
        elif ext == 'cue':
            system, bins = parse_cue(item)
            if system:
                dest_dir = ROMS_BASE / system
                dest_dir.mkdir(parents=True, exist_ok=True)
                move_file(item, dest_dir / item.name)
                for b in bins:
                    if b.exists():
                        move_file(b, dest_dir / b.name)
                log.info(f'  → {system}/ (cue+bin set)')
                return

        # 5. .iso / .img — header detection + name hints
        elif ext in ('iso', 'img'):
            system = detect_disc_system(item)
            if not system:
                system = guess_from_name(item.stem)

        # 6. .chd — name hints only (no header)
        elif ext == 'chd':
            system = guess_from_name(item.stem)

        # 7. .bin — try header then name
        elif ext == 'bin':
            system = detect_disc_system(item)
            if not system:
                system = guess_from_name(item.stem)

        # 8. .m3u — read it to find referenced files, derive system from them
        elif ext == 'm3u':
            try:
                lines = item.read_text().splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ref_ext = Path(line).suffix.lstrip('.').lower()
                        if ref_ext in EXT_MAP:
                            system = EXT_MAP[ref_ext]
                            break
                        if ref_ext in ('chd', 'iso', 'bin'):
                            system = guess_from_name(item.stem)
                            break
            except OSError:
                pass

        # 9. .dsk — common to amstradcpc, amiga, apple2; try name hints
        elif ext == 'dsk':
            system = guess_from_name(item.stem)
            if not system:
                system = 'amstradcpc'  # most common .dsk user

        else:
            system = guess_from_name(item.stem)

    # Move to destination
    if system:
        dest_dir = ROMS_BASE / system
        if not dest_dir.exists():
            log.warning(f'  System folder does not exist: {dest_dir} — sending to _unknown')
            system = None
        else:
            dest = dest_dir / item.name
            move_file(item, dest)
            log.info(f'  → {system}/')
            return

    # Could not classify
    dest = UNKNOWN / item.name
    move_file(item, dest)
    log.info(f'  → _unknown/ (could not classify "{item.name}")')

def move_file(src: Path, dst: Path):
    """Move src to dst, avoiding overwrites by suffixing if needed."""
    if dst.exists():
        stem, suffix = dst.stem, dst.suffix
        i = 1
        while dst.exists():
            dst = dst.parent / f'{stem}_{i}{suffix}'
            i += 1
    try:
        shutil.move(str(src), str(dst))
    except Exception as e:
        log.error(f'  Move failed {src} → {dst}: {e}')

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) < 2:
        log.error('Usage: rom-sorter.py <path>')
        sys.exit(1)
    for arg in sys.argv[1:]:
        sort_item(Path(arg))
