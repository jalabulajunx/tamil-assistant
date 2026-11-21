#!/bin/bash
# Tamil Assistant Launcher Script

# Close any running Tamil Assistant. The app runs as "python3 /usr/bin/tamil-assistant";
# match that whole command line exactly (-x) so this launcher script, whose name also
# contains "tamil-assistant", is never matched.
APP_PATTERN='(/usr/bin/)?python3(\.[0-9]+)? /usr/bin/tamil-assistant'
if pkill -f -x "$APP_PATTERN"; then
    # Wait up to 3 s for the old window to go, so the i3 rules below target the new one
    for _ in $(seq 30); do
        pgrep -f -x "$APP_PATTERN" >/dev/null || break
        sleep 0.1
    done
fi

# Start Tamil Assistant using the installed executable
tamil-assistant &

# Wait for it to start
sleep 2

# Force it to be visible using the correct window class
i3-msg '[class="TamilAssistant"] floating enable'
i3-msg '[class="TamilAssistant"] move position 1520 0'
i3-msg '[class="TamilAssistant"] focus'
i3-msg '[class="TamilAssistant"] move to workspace current'

# Show a notification
notify-send "Tamil Assistant" "Launched successfully!"
