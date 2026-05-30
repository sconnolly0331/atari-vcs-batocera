#!/bin/bash
# Drop this on the second machine and run it as root.
# Detects Batocera vs RetroPie and applies correct client netplay config.

HOST_IP="192.168.68.57"
HOST_PORT="55435"
PLAYER_NAME="Player 2"

echo "=== Netplay Client Setup ==="
echo "Host: $HOST_IP:$HOST_PORT"
echo ""

# ── Detect platform ──────────────────────────────────────────────────────────
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

# ── Batocera ─────────────────────────────────────────────────────────────────
if [ "$PLATFORM" = "batocera" ]; then
    CONF="/userdata/system/batocera.conf"
    
    # Remove any existing netplay lines
    sed -i '/^global\.netplay\./d' "$CONF"
    
    # Append client config
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
    echo "  Restart EmulationStation to apply, then:"
    echo "  Long-press a game → Start Netplay as Client"

# ── RetroPie ─────────────────────────────────────────────────────────────────
elif [ "$PLATFORM" = "retropie" ]; then
    CONF="/opt/retropie/configs/all/retroarch.cfg"
    
    # Remove old netplay lines
    sed -i '/^netplay_/d' "$CONF"
    
    # Append netplay client defaults
    cat >> "$CONF" << EOF

# Netplay — LAN client
netplay_nickname = "$PLAYER_NAME"
netplay_ip_port = "$HOST_PORT"
netplay_delay_frames = "0"
netplay_public_announce = "false"
EOF

    echo "✓ Written to $CONF"
    echo ""
    echo "To join a game from RetroPie:"
    echo "  In RetroArch: Settings → Netplay → Start Netplay as Client"
    echo "  Enter host IP: $HOST_IP   Port: $HOST_PORT"
    echo ""
    echo "  OR from the command line:"
    echo "  retroarch --connect $HOST_IP --port $HOST_PORT -L /path/to/core.so /path/to/rom"

# ── Generic RetroArch ─────────────────────────────────────────────────────────
elif [ "$PLATFORM" = "retroarch" ]; then
    CONF="$HOME/.config/retroarch/retroarch.cfg"
    mkdir -p "$(dirname $CONF)"
    sed -i '/^netplay_/d' "$CONF" 2>/dev/null || true
    cat >> "$CONF" << EOF

# Netplay — LAN client
netplay_nickname = "$PLAYER_NAME"
netplay_ip_port = "$HOST_PORT"
netplay_delay_frames = "0"
netplay_public_announce = "false"
EOF
    echo "✓ Written to $CONF"

else
    echo "Could not detect platform. Apply manually:"
    echo ""
    echo "For Batocera — add to /userdata/system/batocera.conf:"
    echo "  global.netplay.nickname=$PLAYER_NAME"
    echo "  global.netplay.port=$HOST_PORT"
    echo "  global.netplay.frames=0"
    echo "  global.netplay.server.ip=$HOST_IP"
    echo "  global.netplay.server.port=$HOST_PORT"
    echo ""
    echo "For RetroPie — add to /opt/retropie/configs/all/retroarch.cfg:"
    echo "  netplay_nickname = \"$PLAYER_NAME\""
    echo "  netplay_ip_port = \"$HOST_PORT\""
    echo "  netplay_delay_frames = \"0\""
fi

echo ""
echo "=== ROM sharing ==="
echo "Mount the game library from this machine:"
echo "  sudo mkdir -p /mnt/batocera"
echo "  sudo mount -t cifs //192.168.68.57/share /mnt/batocera -o guest,uid=1000"
echo "  (or browse \\\\\\\\192.168.68.57\\\\share in your file manager)"
echo ""
echo "Done."
