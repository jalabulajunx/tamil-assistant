#!/bin/bash
# Tamil Assistant Launcher Script

# Kill any existing Tamil Assistant processes
pkill -f tamil_sidepanel.py

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
