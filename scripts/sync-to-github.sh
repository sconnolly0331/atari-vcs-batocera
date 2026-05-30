#!/usr/bin/env python3
"""
Syncs Batocera VCS scripts and config to GitHub.
Run any time you want to push changes: python3 /userdata/system/sync-to-github.sh
Skips files that haven't changed. Strips credentials before pushing.
"""

import subprocess, base64, json, hashlib, re
from pathlib import Path

REPO  = "sconnolly0331/atari-vcs-batocera"
LABEL = "Auto-sync from Atari VCS"

# ── File map: local path → repo path ─────────────────────────────────────────
FILE_MAP = {
    "/userdata/system/rom-sorter.py":         "scripts/rom-sorter.py",
    "/userdata/system/rom-watcher.sh":        "scripts/rom-watcher.sh",
    "/userdata/system/rom-scraper.py":        "scripts/rom-scraper.py",
    "/userdata/system/custom.sh":             "scripts/custom.sh",
    "/userdata/system/netplay-client-setup.sh": "scripts/netplay-client-setup.sh",
    "/userdata/system/batocera.conf":         "config/batocera.conf",
}

# ── Sanitisers: strip credentials before pushing ─────────────────────────────
def sanitise(local_path: str, content: str) -> str:
    if local_path.endswith("rom-scraper.py"):
        content = re.sub(r"(DEV_ID\s*=\s*)'[^']+'",   r"\1'YOUR_DEV_ID'",   content)
        content = re.sub(r"(DEV_PASS\s*=\s*)'[^']+'", r"\1'YOUR_DEV_PASS'", content)
        content = re.sub(r"(SS_USER\s*=\s*)'[^']+'",  r"\1'YOUR_SCREENSCRAPER_USERNAME'", content)
        content = re.sub(r"(SS_PASS\s*=\s*)'[^']+'",  r"\1'YOUR_SCREENSCRAPER_PASSWORD'", content)
    if local_path.endswith("batocera.conf"):
        content = re.sub(r"(wifi\.ssid=).*",   r"\1YOUR_WIFI_SSID",     content)
        content = re.sub(r"(wifi\.key=).*",    r"\1YOUR_WIFI_PASSWORD", content)
        content = re.sub(r"(wifi\d\.ssid=).*", r"\1YOUR_WIFI_SSID",     content)
        content = re.sub(r"(wifi\d\.key=).*",  r"\1YOUR_WIFI_PASSWORD", content)
    return content

# ── GitHub API helpers ────────────────────────────────────────────────────────
def gh(method, endpoint, data=None):
    cmd = ["gh", "api", "--method", method, endpoint]
    inp = json.dumps(data).encode() if data else None
    if data:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=inp, capture_output=True)
    return json.loads(r.stdout) if r.stdout.strip() else {}

def get_repo_files():
    """Return {repo_path: sha} for every file currently in the repo."""
    result = gh("GET", f"/repos/{REPO}/git/trees/HEAD?recursive=1")
    return {item["path"]: item["sha"]
            for item in result.get("tree", [])
            if item["type"] == "blob"}

def blob_sha(content_bytes: bytes) -> str:
    """Compute the git blob SHA for content (same algorithm GitHub uses)."""
    header = f"blob {len(content_bytes)}\0".encode()
    return hashlib.sha1(header + content_bytes).hexdigest()

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"Syncing to {REPO}")
print("Fetching current repo state...", flush=True)
remote = get_repo_files()

pushed = skipped = errors = 0

for local_path, repo_path in FILE_MAP.items():
    local = Path(local_path)
    if not local.exists():
        print(f"  SKIP  {repo_path}  (local file not found)")
        continue

    raw     = local.read_text(errors="replace")
    clean   = sanitise(local_path, raw)
    encoded = clean.encode()
    local_sha = blob_sha(encoded)

    remote_sha = remote.get(repo_path)

    if remote_sha == local_sha:
        print(f"  ──    {repo_path}  (unchanged)")
        skipped += 1
        continue

    print(f"  ↑     {repo_path}  {'(new)' if not remote_sha else '(changed)'}", end=" ", flush=True)

    payload = {
        "message": f"{LABEL}: update {repo_path}",
        "content": base64.b64encode(encoded).decode(),
    }
    if remote_sha:
        payload["sha"] = remote_sha   # required for updates

    result = gh("PUT", f"/repos/{REPO}/contents/{repo_path}", payload)

    if result.get("content"):
        print("✓")
        pushed += 1
    else:
        print("✗")
        errors += 1

print(f"\nDone: {pushed} pushed, {skipped} unchanged, {errors} errors")
if pushed:
    print(f"https://github.com/{REPO}")
