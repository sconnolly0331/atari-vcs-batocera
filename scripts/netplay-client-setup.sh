#!/bin/bash
# Run this on the second machine (Pi, VCS, etc.) to configure it as a netplay client.
# Detects Batocera, RetroPie, or bare RetroArch automatically.

HOST_IP="192.168.68.57"
HOST_PORT="55435"
PLAYER_NAME="Player 2"

echo "=== Netplay Client Setup ==="
echo "Host: $HOST_IP:$HOST_PORT"
echo ""

# ── Detect platform ───────────────────────────────────────────────────────────
if grep -qi "batocera" /etc/os-release 2>/dev/null; then
    PLATFORM="batocera"
elif [ -f /opt/retropie/configs/all/retroarch.cfg ]; then
    PLATFORM="retropie"
elif command -v retroarch &>/dev/null; then
    PLATFORM="retroarch"
else
    PLATFORM="unknown"
fi

echo "Detected platform: $PLATFORM"
echo ""

# ── Batocera ──────────────────────────────────────────────────────────────────
if [ "$PLATFORM" = "batocera" ]; then
    CONF="/userdata/system/batocera.conf"
    sed -i '/^global\.netplay\./d' "$CONF"
    cat >> "$CONF" << EOF

## Netplay — LAN client (connects to $HOST_IP)
global.netplay.nickname=$PLAYER_NAME
global.netplay.port=$HOST_PORT
global.netplay.frames=0
global.netplay.public_announce=0
global.netplay.server.ip=$HOST_IP
global.netplay.server.port=$HOST_PORT
EOF
    echo "✓ Written to $CONF"
    echo "  Restart EmulationStation, then long-press a game → Start Netplay as Client"

# ── RetroPie ──────────────────────────────────────────────────────────────────
elif [ "$PLATFORM" = "retropie" ]; then
    CONF="/opt/retropie/configs/all/retroarch.cfg"

    # Remove any existing netplay lines
    sed -i '/^netplay_/d' "$CONF"

    # Append client config
    cat >> "$CONF" << EOF

# Netplay — LAN client
netplay_nickname = "$PLAYER_NAME"
netplay_ip_address = "$HOST_IP"
netplay_ip_port = "$HOST_PORT"
netplay_delay_frames = "0"
netplay_public_announce = "false"
EOF

    echo "✓ Written to $CONF"
    echo ""
    echo "To join a netplay session:"
    echo "  In EmulationStation: long-press a game → Start Netplay as Client"
    echo ""
    echo "  Or from terminal:"
    echo "  retroarch --connect $HOST_IP --port $HOST_PORT -L /path/to/core.so /path/to/rom"

# ── Generic RetroArch ─────────────────────────────────────────────────────────
elif [ "$PLATFORM" = "retroarch" ]; then
    CONF="$HOME/.config/retroarch/retroarch.cfg"
    mkdir -p "$(dirname $CONF)"
    sed -i '/^netplay_/d' "$CONF" 2>/dev/null || true
    cat >> "$CONF" << EOF

# Netplay — LAN client
netplay_nickname = "$PLAYER_NAME"
netplay_ip_address = "$HOST_IP"
netplay_ip_port = "$HOST_PORT"
netplay_delay_frames = "0"
netplay_public_announce = "false"
EOF
    echo "✓ Written to $CONF"

# ── Unknown ───────────────────────────────────────────────────────────────────
else
    echo "Could not detect platform. Apply manually:"
    echo ""
    echo "For RetroPie — add to /opt/retropie/configs/all/retroarch.cfg:"
    echo "  netplay_nickname = \"$PLAYER_NAME\""
    echo "  netplay_ip_address = \"$HOST_IP\""
    echo "  netplay_ip_port = \"$HOST_PORT\""
    echo "  netplay_delay_frames = \"0\""
    echo "  netplay_public_announce = \"false\""
fi

echo ""
echo "=== ROM sharing ==="
echo "Mount the game library from the VCS:"
echo "  sudo mkdir -p /mnt/batocera"
echo "  sudo mount -t cifs //192.168.68.57/share /mnt/batocera -o guest,uid=1000"
echo ""
echo "Done."
