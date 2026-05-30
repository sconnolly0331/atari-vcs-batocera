#!/bin/bash
# ROM Watcher — monitors _incoming/ and calls rom-sorter.py on new arrivals.
# Started by custom.sh at boot; logs to /userdata/system/logs/rom-sorter.log.

INCOMING="/userdata/roms/_incoming"
SORTER="/userdata/system/rom-sorter.py"
LOG="/userdata/system/logs/rom-sorter.log"
PIDFILE="/var/run/rom-watcher.pid"

echo $$ > "$PIDFILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO  ROM Watcher started (PID $$), watching $INCOMING" >> "$LOG"

# inotifywait events:
#   close_write  — file was written and closed (download/copy complete)
#   moved_to     — file was moved/renamed into the watched directory
# -r recursive so subdirs of _incoming are also caught
# --exclude _unknown so we don't re-sort already-unknowns

inotifywait -m -r \
    --exclude "/_unknown/" \
    -e close_write \
    -e moved_to \
    --format '%w%f' \
    "$INCOMING" 2>>"$LOG" | \
while IFS= read -r filepath; do
    # Skip hidden/temp files (wget partial downloads, .part files, etc.)
    basename="${filepath##*/}"
    case "$basename" in
        .* | *.part | *.tmp | *.crdownload | *.download)
            continue
            ;;
    esac

    # Give the file a moment to fully settle if it just appeared
    sleep 0.5

    echo "$(date '+%Y-%m-%d %H:%M:%S') INFO  Detected: $filepath" >> "$LOG"
    python3 "$SORTER" "$filepath" 2>>"$LOG"
done
