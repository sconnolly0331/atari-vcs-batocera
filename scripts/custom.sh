export mesa_glthread=true
export AMD_VULKAN_ICD=RADV

# ROM auto-sorter watcher
if [ ! -f /var/run/rom-watcher.pid ] || ! kill -0 "$(cat /var/run/rom-watcher.pid)" 2>/dev/null; then
    /userdata/system/rom-watcher.sh &
fi
