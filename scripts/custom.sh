export mesa_glthread=true

# Mount Pi Toshiba hub (ROMs + shared saves)
PI_MOUNT=/userdata/system/mnt/pi-retropie
mkdir -p "$PI_MOUNT"
if ! mountpoint -q "$PI_MOUNT"; then
    mount -t cifs //192.168.68.55/retropie "$PI_MOUNT" \
        -o guest,uid=0,gid=0,file_mode=0664,dir_mode=0775,nofail 2>/dev/null
fi
export AMD_VULKAN_ICD=RADV

# ROM auto-sorter watcher
if [ ! -f /var/run/rom-watcher.pid ] || ! kill -0 "$(cat /var/run/rom-watcher.pid)" 2>/dev/null; then
    /userdata/system/rom-watcher.sh &
fi
export PATH="$HOME/.grok/bin:$PATH"
