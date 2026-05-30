#!/usr/bin/env python3
"""
Batocera ScreenScraper — downloads missing artwork for all games.
Uses the same API credentials as EmulationStation itself.
"""

import os, sys, ssl, json, time, hashlib, zipfile, subprocess, shutil, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

# --- Credentials (from ES binary) -----------------------------------------
DEV_ID   = 'YOUR_DEV_ID'
DEV_PASS = 'YOUR_DEV_PASS'
SS_USER  = 'YOUR_SCREENSCRAPER_USERNAME'
SS_PASS  = 'YOUR_SCREENSCRAPER_PASSWORD'
SOFT     = 'Batocera-Emulationstation'
API_BASE = 'https://api.screenscraper.fr/api2'
CTX      = ssl.create_default_context()

# --- Batocera system folder → ScreenScraper system ID --------------------
SYSTEM_IDS = {
    'atari2600':26,'atari5200':40,'atari7800':41,'atari800':43,
    'atarist':42,'jaguar':27,'jaguarcd':171,'lynx':28,
    'nes':3,'fds':106,'snes':4,'snes-msu1':4,'n64':14,'n64dd':122,
    'gb':9,'gbc':10,'gba':12,'nds':15,'3ds':17,
    'gamecube':13,'wii':16,'wiiu':18,'virtualboy':11,
    'megadrive':1,'sega32x':19,'mastersystem':2,'gamegear':21,
    'sg1000':2,'megacd':20,'saturn':22,'dreamcast':23,
    'psx':57,'ps2':58,'ps3':59,'ps4':60,'psp':61,'psvita':62,
    'pcengine':31,'pcenginecd':114,'supergrafx':105,'pcfx':72,
    'neogeo':68,'neogeocd':70,'ngp':25,'ngpc':82,
    'wswan':45,'wswanc':46,
    'mame':75,'fbneo':75,'atomiswave':53,'naomi':56,'naomi2':230,
    'model2':54,'model3':55,'daphne':49,'singe':49,
    'namco22':75,'namco2x6':75,'lindbergh':75,
    'colecovision':48,'intellivision':115,'vectrex':102,'3do':29,
    'amiga500':64,'amiga1200':64,'amigacd32':130,'amigacdtv':129,
    'c64':66,'c128':66,'zxspectrum':76,'amstradcpc':65,
    'msx1':113,'msx2':116,'msx2+':117,'msxturbor':118,
    'sgb':9,'sgb-msu1':4,'satellaview':4,
    'channelf':80,'astrocde':44,'vectrex':102,'supervision':None,
    'pokemini':211,'gamate':None,'lcdgames':None,
    'scummvm':135,'dos':135,
}

# Entries that are data files, collections, or non-games — skip scraping
SKIP_NAMES = {
    'fonts.mpq','hfmonk.mpq','hfmusic.mpq','hfvoice.mpq','pl.mpq','ru.mpq',
    'fbneo','namco2x6',
    'Atari Jaguar Rom Collection','AtariJaguarRomCollectionReuploadByDataghost',
    'SS - Boot Disc','segacd','nes','snes','altbeast','pygun',
}

ROMS_BASE = Path('/userdata/roms')
LOG = Path('/userdata/system/logs/rom-scraper.log')

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler(LOG), logging.StreamHandler()],
)
log = logging.getLogger('rom-scraper')

# --------------------------------------------------------------------------
def api_get(endpoint, params):
    base = {
        'devid': DEV_ID, 'devpassword': DEV_PASS,
        'softname': SOFT, 'output': 'json',
        'ssid': SS_USER, 'sspassword': SS_PASS,
    }
    base.update(params)
    url = f'{API_BASE}/{endpoint}?' + urllib.parse.urlencode(base)
    with urllib.request.urlopen(url, context=CTX, timeout=20) as r:
        return json.loads(r.read())

def download_file(url, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': SOFT})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r, open(dest, 'wb') as f:
        shutil.copyfileobj(r, f)

def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest().upper()

def name_from_filename(filename: str) -> str:
    """Convert a ROM filename to a clean search term."""
    import re
    name = Path(filename).stem
    name = name.replace('_', ' ').replace('-', ' ')
    name = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', name)
    return name.strip()

def search_by_name(sys_id: int, game_name: str):
    """Fallback: search ScreenScraper by game name and return jeu dict or None."""
    clean = name_from_filename(game_name)
    if not clean or len(clean) < 2:
        return None
    try:
        data = api_get('jeuRecherche.php', {'systemeid': sys_id, 'recherche': clean})
        jeux = data.get('response', {}).get('jeux', [])
        if jeux:
            # Take the first result and fetch full info
            jeu_id = jeux[0].get('id')
            if jeu_id:
                full = api_get('jeuInfos.php', {'systemeid': sys_id, 'jeuid': jeu_id})
                return full.get('response', {}).get('jeu')
    except Exception:
        pass
    return None

def pick_media(medias, media_type):
    """Pick best media item by type, preferring en/ss region."""
    candidates = [m for m in medias if m.get('type') == media_type]
    if not candidates:
        return None
    # Prefer English / US / world / no-region
    for pref in ('en','us','wor',''):
        for m in candidates:
            if m.get('region','').lower() in (pref, ''):
                return m
    return candidates[0]

def scrape_game(system: str, rom_path: Path, game_name: str, gamelist_dir: Path):
    sys_id = SYSTEM_IDS.get(system)
    if not sys_id:
        log.info(f'  No system ID for {system}, skipping')
        return None

    jeu = None

    # For directories (e.g. singe .daphne folders), go straight to name search
    if not rom_path.is_file():
        jeu = search_by_name(sys_id, game_name)
    else:
        # Try by filename + MD5
        params = {'systemeid': sys_id, 'romnom': rom_path.name}
        if rom_path.stat().st_size < 200 * 1024 * 1024:
            params['md5'] = md5_of(rom_path)
        try:
            data = api_get('jeuInfos.php', params)
            jeu = data.get('response', {}).get('jeu')
        except urllib.error.HTTPError as e:
            if e.code == 403:
                log.warning('  API quota reached or auth error')
                return None
        except Exception:
            pass

        # Fallback: search by name
        if not jeu:
            jeu = search_by_name(sys_id, game_name)

    if not jeu:
        log.info(f'  Not found on ScreenScraper: {game_name}')
        return None

    medias = jeu.get('medias', [])
    img_dir = gamelist_dir / 'images'
    stem = rom_path.stem

    result = {}

    # Image = screenshot (ss) or title screen (sstitle)
    for img_type in ('ss', 'sstitle'):
        m = pick_media(medias, img_type)
        if m and m.get('url'):
            dest = img_dir / f'{stem}-image.png'
            try:
                download_file(m['url'], dest)
                result['image'] = f'./images/{stem}-image.png'
                break
            except Exception as ex:
                log.debug(f'  Image download failed: {ex}')

    # Thumbnail = 2D box front
    for thumb_type in ('box-2D', 'box-3D', 'box-2D-back'):
        m = pick_media(medias, thumb_type)
        if m and m.get('url'):
            dest = img_dir / f'{stem}-thumb.png'
            try:
                download_file(m['url'], dest)
                result['thumbnail'] = f'./images/{stem}-thumb.png'
                break
            except Exception as ex:
                log.debug(f'  Thumbnail download failed: {ex}')

    # Marquee = wheel or screenmarquee
    for marq_type in ('wheel', 'screenmarquee', 'screenmarqueesmall'):
        m = pick_media(medias, marq_type)
        if m and m.get('url'):
            dest = img_dir / f'{stem}-marquee.png'
            try:
                download_file(m['url'], dest)
                result['marquee'] = f'./images/{stem}-marquee.png'
                break
            except Exception as ex:
                log.debug(f'  Marquee download failed: {ex}')

    return result if result else None

def update_gamelist(gl_path: Path, system: str):
    tree = ET.parse(gl_path)
    root = tree.getroot()
    gl_dir = gl_path.parent
    changed = 0

    for game in root.findall('game'):
        path_el  = game.find('path')
        name_el  = game.find('name')
        image_el = game.find('image')

        if path_el is None:
            continue
        if image_el is not None and image_el.text:
            continue  # already has image

        game_path = gl_dir / path_el.text.lstrip('./')
        game_name = name_el.text if name_el is not None else path_el.text

        # Skip non-games
        if game_name in SKIP_NAMES or Path(path_el.text).name in SKIP_NAMES:
            log.info(f'  [{system}] Skip: {game_name}')
            continue
        if game_name.startswith('ZZZ(notgame)'):
            log.info(f'  [{system}] Skip notgame: {game_name}')
            continue

        log.info(f'  [{system}] Scraping: {game_name}')
        result = scrape_game(system, game_path, game_name, gl_dir)

        if result:
            if 'image' in result:
                el = game.find('image')
                if el is None:
                    el = ET.SubElement(game, 'image')
                el.text = result['image']
            if 'thumbnail' in result:
                el = game.find('thumbnail')
                if el is None:
                    el = ET.SubElement(game, 'thumbnail')
                el.text = result['thumbnail']
            if 'marquee' in result:
                el = game.find('marquee')
                if el is None:
                    el = ET.SubElement(game, 'marquee')
                el.text = result['marquee']
            el = game.find('scrap')
            if el is None:
                el = ET.SubElement(game, 'scrap')
            el.set('name', 'ScreenScraper')
            from datetime import datetime
            el.set('date', datetime.now().strftime('%Y%m%dT%H%M%S'))
            changed += 1
            log.info(f'    → got {list(result.keys())}')
        else:
            log.info(f'    → no artwork found')

        time.sleep(0.5)  # be polite to the API

    if changed:
        ET.indent(tree, space='\t')
        tree.write(gl_path, encoding='unicode', xml_declaration=True)
        log.info(f'  [{system}] Saved {changed} updates to gamelist')
    return changed

# --------------------------------------------------------------------------
if __name__ == '__main__':
    log.info('=== ROM Scraper starting ===')
    total = 0
    for gl in sorted(ROMS_BASE.rglob('gamelist.xml')):
        system = gl.parent.name
        if system.startswith('_'):
            continue
        log.info(f'Checking [{system}]...')
        try:
            n = update_gamelist(gl, system)
            total += n
        except Exception as e:
            log.error(f'Error in [{system}]: {e}')
    log.info(f'=== Done: {total} games updated ===')
